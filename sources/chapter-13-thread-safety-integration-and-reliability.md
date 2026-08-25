# Chapter 13 | Thread Safety, Integration, and Reliability

> If you can keep your head when all about you
> Are losing theirs and blaming it on you,
>
> <cite>Rudyard Kipling, “If—”</cite>

The prediction service keeps the latest departure-board snapshot in memory. Network
tasks replace the snapshot as updates arrive, while request tasks read it to answer
clients. Every snapshot is valid on its own. The program can still fail if one thread
publishes a new value without the coordination needed by its readers.

Concurrency changes the set of states an implementation can expose. Operations that
look indivisible in source code may consist of several reads and writes. A thread may
observe stale data unless the Java memory model establishes the required ordering.
A concurrent collection alone cannot supply thread safety. We need a specification
and an argument for the whole abstraction.

This final chapter publishes immutable snapshots through an atomic reference. It then
connects that implementation to the design decisions made throughout the readings:
types, specifications, testing, ownership, abstraction, equality, composition,
recursion, transformations, protocols, and task lifetimes.

By the end of this chapter, you should be able to:

- state a thread-safety policy for a shared abstraction;
- distinguish atomicity, visibility, and ordering;
- identify a data race and explain the role of happens-before relationships;
- publish an immutable snapshot through `AtomicReference`;
- recognise a compound action that a thread-safe collection does not make atomic;
- compare confinement, immutability, locks, and atomic variables;
- write a representation and concurrency argument for an integrated component; and
- use failures and operational evidence to revise a software design.

## 1. Permitted Concurrent Observations

`SnapshotStore` has two operations:

```text
read()
effects: none
returns: one complete snapshot published by the store

update(operation)
requires: operation is non-null and safe to call more than once
effects: atomically replaces the current snapshot with a value computed from it
returns: the replacement snapshot
```

The word *atomically* states an observable property. Each successful update should
appear to take effect at one point between its invocation and return. A reader may see
the old snapshot or the new snapshot when the calls overlap, but it must not see a
mixture of their fields.

The contract does not promise that a reader obtains the latest external transit
observation. Network delay, refresh policy, and clock time determine freshness. It
promises a coherent snapshot among those published by this store.

`update` may invoke its operation repeatedly when competing updates occur. The
function must therefore have no non-repeatable external effect. Sending a message or
incrementing an unrelated counter inside it could happen more than once even though
only one replacement succeeds.

> **Design principle:** State the concurrent observations an abstraction permits,
> then use one coordination policy for all state that must change together.

## 2. Atomicity, Visibility, and Ordering

**Atomicity** means an operation appears indivisible with respect to the relevant
threads. Reading or writing one reference is atomic, but a sequence such as “read,
compute, write” is a compound action and can interleave with another thread.

**Visibility** concerns whether a write by one thread becomes observable to another.
A thread can retain or reuse values according to the Java memory model when no
synchronisation relationship requires it to observe another thread's write.

**Ordering** concerns which actions are guaranteed to precede others. Compilers,
processors, and the runtime may reorder operations when the allowed observations of
a correctly synchronised program remain unchanged. Source line order in one thread
does not by itself create an inter-thread guarantee.

The Java Language Specification defines a **happens-before** relation. If action A
happens-before action B, then B is guaranteed to observe the effects of A in the ways
specified by the memory model. Important examples include:

- releasing a monitor happens-before a later successful acquisition of that monitor;
- a write to a `volatile` field happens-before every subsequent read of that field;
- actions before starting a thread happen-before actions in the started thread; and
- all actions in a thread happen-before another thread successfully returns from
  joining it.

Two conflicting accesses to the same variable form a **data race** when at least one
is a write and they are not ordered by happens-before. Correctly synchronised programs
have sequentially consistent behaviour under the Java memory model: their actions
can be understood as an interleaving that respects each thread's program order.

## 3. Atomic Publication of an Immutable Snapshot

The snapshot value copies its map during construction:

```java
public record BoardSnapshot(
        long version,
        Instant observedAt,
        Map<String, Integer> predictions) {
    public BoardSnapshot {
        predictions = Map.copyOf(predictions);
    }
}
```

The record components do not change after construction. `Instant` is immutable, and
`Map.copyOf` creates an unmodifiable snapshot of the entries. The string keys and
integer values are immutable. Once safely published, a `BoardSnapshot` can be shared
without locks because readers do not race with mutations inside it.

The store coordinates replacement of the reference:

```java
public static final class SnapshotStore {
    private final AtomicReference<BoardSnapshot> current;

    public SnapshotStore(BoardSnapshot initial) {
        current = new AtomicReference<>(initial);
    }

    public BoardSnapshot read() {
        return current.get();
    }

    public BoardSnapshot update(UnaryOperator<BoardSnapshot> operation) {
        return current.updateAndGet(operation);
    }
}
```

`AtomicReference.get` and the successful update supply the memory effects documented
for atomic variables. Readers obtain either the complete old reference or the
complete new reference, and publication makes the constructed snapshot's state
visible.

The companion program started two virtual threads. Each performed 1,000 updates that
incremented the version. After joining both threads, the validated Java 25 run
printed:

```text
version=2000
```

The result relies on the atomic read-modify-write operation. A plain sequence that
reads `current`, computes a replacement, and assigns it can lose an increment when
two threads read the same version before either writes.

## 4. The Compare-and-Set Loop

`updateAndGet` is conceptually a compare-and-set loop. It reads the current
reference, applies the operation, and attempts to replace the reference only if no
other update changed it in the meantime. If the comparison fails, it retries with
the newer value.

The successful compare-and-set is the **linearisation point** for the update: the
instant at which the operation takes effect in a sequential account of concurrent
calls. The `get` operation similarly observes one reference at its atomic read.

This reasoning gives the store a linearizable contract. Each call can be placed in a
total order consistent with real-time order for non-overlapping calls. Linearizability
is useful for a “current value” abstraction because clients can reason as if updates
occurred one at a time.

The retry explains the requirement on the update function. Consider:

```java
store.update(old -> {
    billingService.chargeForRefresh();
    return refresh(old);
});
```

Contention can call `chargeForRefresh` more than once before one replacement
succeeds. The atomic reference protects only its stored reference. It does not roll
back effects performed by the function. Compute a side-effect-free candidate inside
the update, or use a different protocol that separates external effects and defines
idempotence.

Atomic replacement also has a retry cost. If snapshots are large and contention is
high, several threads may compute discarded candidates. A lock can be more suitable
when the update is expensive, requires exactly-once execution, or spans several
mutable resources.

## 5. Compound Actions on Concurrent Collections

Replacing `HashMap` with `ConcurrentHashMap` makes individual documented map
operations safe for concurrent use. It does not make an arbitrary sequence of calls
atomic.

This check-then-act sequence can fetch the same stop twice:

```java
if (!cache.containsKey(stop)) {
    cache.put(stop, provider.fetch(stop));
}
return cache.get(stop);
```

Two threads can both observe absence, both call the provider, and both put. The map
remains structurally valid, but the program may duplicate network load or an external
effect.

`ConcurrentHashMap.computeIfAbsent` performs the per-key computation according to its
documented atomicity rules:

```java
return cache.computeIfAbsent(stop, provider::fetch);
```

The mapping function must follow that API's constraints. It should be short and
should not recursively update the same map in a way that violates the contract. A
failed computation leaves absence rather than caching an exception. The application
must still decide whether failures or stale values should be cached.

A thread-safe container also does not make its elements immutable. A concurrent map
can safely publish a reference to a mutable `ArrayList` that callers then modify
without coordination. Thread safety must cover the reachable representation and the
compound observations promised by the abstraction.

## 6. Coordination Strategies

Four strategies cover many designs.

### Confinement

State is **confined** when only one thread accesses it. A request handler can build a
mutable route locally and return an immutable result. No synchronisation is needed
for the confined builder because concurrent tasks do not share it.

Confinement is usually the simplest policy. It must be preserved when references are
passed to callbacks, stored in fields, or returned. Virtual threads do not imply
confinement if they share the same object.

### Immutability

An immutable value does not change after construction. Safe publication lets any
number of threads read it. The snapshot design combines immutable state with atomic
replacement, so readers never coordinate with one another.

Immutability must include reachable mutable objects or make defensive copies. A final
field pointing to a mutable map does not make the map immutable.

### Locks

The `synchronized` statement and explicit locks provide mutual exclusion and
happens-before relationships. A lock can protect a multi-field invariant and an
operation that must execute exactly once within the critical section.

Every access participating in that invariant must follow the same locking policy.
Calling an unknown or slow network operation while holding a lock can block unrelated
clients and risk deadlock through callbacks. Often the program can copy the required
state under the lock, release it, perform slow work, and validate before committing a
result.

### Atomic variables and concurrent collections

Atomic variables support operations on one independently updated value or reference.
Concurrent collections provide specified atomic operations and scalable access
patterns. They work well when the abstraction aligns with those operations.

Several atomics do not automatically make a multi-variable invariant atomic. If
`latestData` and `latestVersion` must always correspond, publishing them in one
immutable snapshot is clearer than updating two atomic fields separately.

## 7. The Thread-Safety Argument and the RI

The representation invariant (RI) for `SnapshotStore` can state:

```text
current is non-null;
current.get() is non-null;
the snapshot's map contains no null key or value;
every prediction is non-negative.
```

The abstraction function maps the current referenced record to the board value
observed by clients. If non-negative predictions belong to the abstract invariant,
the `BoardSnapshot` constructor should check them rather than relying on the store.
Then every construction path establishes the property.

The thread-safety argument adds a coordination policy:

1. `current` is the only mutable representation state.
2. All accesses to it use `AtomicReference` operations.
3. Each referenced `BoardSnapshot` and everything reachable from it is immutable.
4. The update function has no externally visible effect that depends on being called
   exactly once.
5. Therefore readers observe complete safely published snapshots, and successful
   updates can be ordered by their atomic replacement points.

The detailed argument is more useful than the comment “thread safe.” It identifies
the state,
the access rule, the publication mechanism, and the client observation being
protected. A future edit that adds a mutable `lastError` field must extend the policy
or reveal that the argument no longer covers the whole representation.

## 8. The Integrated Journey-Planning System

The completed journey-planning example now crosses several boundaries:

```text
request data
  -> validated domain types
  -> router interface and composed policies
  -> recursive or graph-based journey values
  -> concurrent provider tasks
  -> protocol adapters
  -> immutable published snapshot
  -> response data
```

Each arrow carries a contract. Integration failures commonly occur where two locally
reasonable assumptions disagree. A protocol adapter may represent an absent
prediction as `-1`, while the domain type rejects negative minutes. A cache may use a
request type whose equality omits an accessibility requirement. A retry wrapper may
repeat a non-idempotent provider operation. A stream may discard encounter order that
the user interface treats as ranking.

Integration tests should concentrate on these boundaries. A deterministic local
server can return malformed and delayed responses. A fixed clock can control cache
expiry. A test executor or latch can arrange concurrent events without depending only
on repeated luck. Tests should state the observation that demonstrates the contract,
including allowed sets of outcomes for genuinely concurrent calls.

System reliability also needs operational evidence. Timeouts, failure categories,
queue depth, request latency, cache age, and rejected work can reveal whether runtime
assumptions hold. Metrics require definitions just as method results do. A “failure
count” that mixes invalid client requests with unavailable providers cannot support a
clear diagnosis.

## 9. Design Revisions from Failure Evidence

A failing integration test or production incident supplies evidence about a violated
assumption. The next step is to locate that assumption in a contract, representation,
boundary, or concurrency policy.

Suppose readers occasionally see a new version paired with old predictions. The
immediate defect may be separate field updates. The design correction is to publish
one immutable snapshot so the values that must agree change together. A test that
only increases delays might reproduce the old race, but the snapshot abstraction
prevents the mixed state by construction.

Suppose a provider receives duplicate purchases after a client timeout. Increasing
the timeout may reduce frequency without resolving ambiguity. The protocol needs an
idempotency mechanism or an operation whose retry semantics are explicit.

Suppose route lookup fails after a cached request object changes. Synchronising the
map does not repair a mutable hash key. Equality and ownership must be corrected.

Reliability depends on decisions made throughout the design. The types,
specifications, state ownership, APIs, and protocols determine which failures are
possible and how much evidence the system can retain.

## 10. Common Misconception: Thread-Safe Parts Make a Thread-Safe Whole

An application can use `AtomicInteger`, `ConcurrentHashMap`, and immutable records
and still violate its concurrent contract. Two atomic counters can disagree when the
abstraction requires them to advance together. A concurrent map can contain mutable
values. A check followed by an update can race even though both calls are individually
safe.

Thread safety is a property of an abstraction under a stated access pattern. The
analysis begins with what clients may observe, identifies all shared reachable state,
and checks every compound action. Selecting a class with “Concurrent” in its name is
an implementation step within that argument.

The opposite overstatement is also wrong. A class does not need internal locks when
its specification requires single-thread confinement and the system enforces that
ownership. Making every object independently thread-safe can add contention and
obscure which component owns mutation.

## 11. Practice by Constructing Interleavings

For each exercise, write one interleaving that violates the intended property, then
propose a coordination policy.

1. Two threads execute `counter = counter + 1` on a shared `int`. Break the expression
   into reads, arithmetic, and writes and produce a final value of one.
2. A board stores `version` and `predictions` in separate volatile fields. Show how a
   reader can observe values from different updates, then redesign the state.
3. A `ConcurrentHashMap` stores mutable lists of arrivals. Identify which accesses
   the map protects and which require another policy.
4. An `AtomicReference.updateAndGet` function writes a log entry. Explain why one
   successful update can produce multiple entries under contention.
5. A router holds a lock while making an HTTP request. Identify effects on latency,
   cancellation, and deadlock risk. Split the operation if its invariant permits.
6. Design a deterministic test for two concurrent snapshot updates. State why joining
   both threads creates the observation point for the final assertion.

Finally, review the journey-planning system as a whole. Select one boundary from each
of the following categories: data representation, component API, external protocol,
and concurrent state. For each boundary, write the contract, one failure, and the
evidence that would distinguish that failure from its nearest alternative cause.

## 12. Summary

- A thread-safety contract states which observations concurrent clients may make.
- Atomicity, visibility, and ordering are distinct concerns connected by the Java
  memory model's happens-before relation.
- Immutable snapshots plus atomic publication keep related state coherent for
  readers.
- Atomic update functions may run more than once and therefore should not contain
  non-repeatable effects.
- Concurrent collections protect their documented operations, not arbitrary compound
  actions or mutable elements.
- Confinement, immutability, locks, atomic variables, and concurrent collections each
  fit different ownership and update patterns.
- Reliability follows from decisions across the system and improves when failures
  lead to corrected contracts and representations.

## References

- Rudyard Kipling. [“If—,” *Rewards and Fairies*](https://www.gutenberg.org/files/556/556-h/556-h.htm).
- Oracle. [Java Language Specification, Java SE 25, Chapter 17: Threads and Locks](https://docs.oracle.com/javase/specs/jls/se25/html/jls-17.html).
- Oracle. [`AtomicReference` (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/atomic/AtomicReference.html).
- Oracle. [`ConcurrentHashMap` (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/ConcurrentHashMap.html).
- Oracle. [`ReentrantLock` (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/locks/ReentrantLock.html).
