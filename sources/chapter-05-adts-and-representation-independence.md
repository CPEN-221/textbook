# Chapter 5 | ADTs and Representation Independence

> If a data abstraction such as stack is specified as a single entity, much of the
> extraneous detail can be eliminated.
>
> <cite>Barbara Liskov and Stephen Zilles, “Specification Techniques for Data
> Abstractions”</cite>

Our first transit network is a map:

```java
Map<StopId, Set<StopId>> outgoing = new HashMap<>();
```

The keys are stops. Each value is the set of stops reachable by one direct trip. We
initially pass this map to the route finder, map viewer, feed loader, and tests.
Several of those clients begin to inspect or mutate it directly.

We then replace the map with a compact set of connections. Every client that depends
on the map representation breaks, even though the meaning of a transit network has
not changed.

An **abstract data type**, or **ADT**, separates those clients from the representation.
Clients use specified values and operations. The implementation decides how to store
the values. We can then change the representation without changing clients that
depend only on the specification.

By the end of this chapter, you should be able to:

- define an ADT by its abstract values and operations;
- design operations from client needs instead of exposing a convenient data
  structure;
- classify operations as creators, producers, observers, or mutators;
- specify an immutable ADT, including exceptional behaviour and returned
  collections;
- explain representation independence and the conditions it requires;
- test two implementations through one public contract.

## 1. Define the Abstract Value

Before choosing fields, say what a value of the type *means*. Our
`TransitNetwork` represents a finite directed graph:

- each vertex is a `StopId`;
- an edge `from -> to` means that a vehicle can travel directly from `from` to
  `to` in the model;
- direction matters;
- the network has no edge from a stop to itself.

This is the **abstract value**. A client can ask whether an edge exists without
knowing whether the implementation stores a map, a matrix, or a collection of edge
records.

The word *directly* matters. An edge from UBC to Wesbrook and one from Wesbrook to
Alma do not imply a direct edge from UBC to Alma. A later route-search operation may
derive reachability through several edges, but that is a different observation.

We will make the network immutable. `withConnection` produces a network value; it
does not change the receiver. Once a client receives a network, its stops and
connections remain unchanged.

## 2. Define Operations for Clients

An application programming interface (API) that exposes the representation might
include this method:

```java
Map<StopId, Set<StopId>> adjacencyMap()
```

The method requires every client to understand a map of sets, and it requires the ADT
to keep that representation or emulate it. A client that only needs to know whether
two stops are directly connected should not have to read a map of sets to find out.

Instead, we name the questions and transformations clients need:

```java
public interface TransitNetwork {
    static TransitNetwork empty(Set<StopId> stops) {
        return AdjacencyMapNetwork.empty(stops);
    }

    Set<StopId> stops();
    boolean contains(StopId stop);
    Set<StopId> directDestinationsFrom(StopId stop);
    boolean hasDirectConnection(StopId from, StopId to);
    TransitNetwork withConnection(StopId from, StopId to);
}
```

The complete interface in the [companion
project](../../examples/chapters-05-06/src/main/java/ca/ubc/ece/cpen221/transit/TransitNetwork.java)
includes the specifications. The public operations refer to stops, direct destinations,
and connections. No method returns the representation.

This interface is one Java expression of the ADT, but an ADT is not the same thing as
a Java interface. A final class with private fields and a well-specified public API
can implement an ADT. An interface is useful here because it gives the compiler one
client-facing type while we experiment with multiple implementations.

## 3. Classify the Operations

Four categories help us check whether the API can create, inspect, and transform its
values. Let `T` stand for the ADT.

| Category | Relationship to `T` | Network example |
|---|---|---|
| **Creator** | creates a `T` without receiving a `T` | `empty(stops)` |
| **Producer** | creates a `T` from an existing `T` | `network.withConnection(from, to)` |
| **Observer** | returns information of another type | `network.stops()` |
| **Mutator** | changes an existing `T` | none in this immutable design |

An operation may fit more than one category. `withConnection` may return `this` when
the connection already exists. It still acts as a producer because its contract
describes the returned abstract value rather than requiring a fresh object. A test
that insists on `result != network` would require behaviour absent from the contract.

The classification also exposes omissions. If an API has a creator and three
mutators but no observer, then clients cannot learn anything about the value except
by remembering its history. If it returns a mutable `Map` as its only observer, then
it has mixed observation with unrestricted mutation. The table helps us review the
design; an ADT does not need one operation in every category.

## 4. Define the Public Contract

The creator has a compact promise:

```java
/**
 * Creates a network containing exactly {@code stops} and no connections.
 *
 * @param stops the stops to include
 * @return a network containing exactly {@code stops} and no connections
 * @throws NullPointerException if {@code stops} or an element is null
 */
static TransitNetwork empty(Set<StopId> stops)
```

"Exactly" protects isolated stops. An implementation that records only stops which
occur in an edge would lose every stop in an empty network and violate the
postcondition.

The producer specifies the added edge and the unchanged receiver:

```java
/**
 * @return an immutable network with the same stops and connections as this
 *         network, plus {@code from -> to}
 * @throws NullPointerException if either argument is null
 * @throws IllegalArgumentException if either argument is not in this network,
 *         or if the two arguments are equal
 */
TransitNetwork withConnection(StopId from, StopId to)
```

The receiver remains unchanged because the type is immutable. Adding an existing
edge has no effect on the abstract value. The specification permits the
implementation to return the receiver in that case.

Our observers return unmodifiable sets. They do not promise an iteration order. That
omission is deliberate: a client can test set membership and equality, but it cannot
depend on the current hash-table order. If stable order becomes a requirement, then
we can add it to the specification and accept the associated implementation cost.

A specification does not need to restate every implementation failure; running out of
memory, for example, is not useful network behaviour to repeat on each method. A
specification does need to settle the predictable boundary cases: `null` arguments,
unknown stops, self-connections, permitted mutation, and iteration order.

## 5. Return the Interface from a Factory

The static creator returns the interface type:

```java
static TransitNetwork empty(Set<StopId> stops) {
    return AdjacencyMapNetwork.empty(stops);
}
```

`AdjacencyMapNetwork` has package access rather than `public` access. Code outside
the package cannot name the class or call its constructor. Clients write:

```java
TransitNetwork network = TransitNetwork.empty(Set.of(ubc, wesbrook, alma));
```

The declared type matters. If the factory returned `AdjacencyMapNetwork`, or clients
constructed that class directly, then the implementation name would appear in
method signatures and tests. Changing representations would then become a migration
rather than a private edit.

A factory chooses an implementation while returning the abstraction. We could later
make that choice depend on input size or a configuration setting, provided every
returned object satisfies the same contract.

## 6. Implement Without Exposing the Representation

Our first implementation stores an **adjacency map**:

```java
final class AdjacencyMapNetwork implements TransitNetwork {
    private final Map<StopId, Set<StopId>> outgoing;

    private AdjacencyMapNetwork(Map<StopId, Set<StopId>> outgoing) {
        Objects.requireNonNull(outgoing, "outgoing");
        Map<StopId, Set<StopId>> snapshot = new HashMap<>();
        outgoing.forEach((stop, destinations) ->
                snapshot.put(Objects.requireNonNull(stop, "stop"),
                        Set.copyOf(Objects.requireNonNull(
                                destinations, "destinations"))));
        this.outgoing = Map.copyOf(snapshot);
        checkRep();
    }
}
```

The constructor snapshots both levels of mutable container. Copying only the map
would leave aliases to its destination sets. Naming an abstraction boundary does not
enforce it; the implementation must prevent clients from reaching mutable
representation objects.

Because the stored map and its sets are unmodifiable, this observer can return one
of those sets safely:

```java
@Override
public Set<StopId> directDestinationsFrom(StopId stop) {
    requireMember(stop);
    return outgoing.get(stop);
}
```

That decision depends on the complete reachable representation. `StopId` is an
immutable record, the destination set is unmodifiable, and no mutable input alias
reaches the field. If any of those facts changed, then returning the field's value
could expose the representation.

The public contract tells clients what they may assume. The private constructor and
helpers may depend on representation details. Data abstraction requires us to keep
those dependencies out of the public API.

## 7. Compare Two Representations

Suppose feed import gives us a set of distinct directed connections. A second
implementation stores exactly that representation:

```java
final class ConnectionSetNetwork implements TransitNetwork {
    private final Set<StopId> stops;
    private final Set<Connection> connections;
}
```

Its direct-destination observer scans and filters `connections`, whereas the
adjacency-map implementation performs a single lookup. Building a network from a feed
of connections is the reverse: the connection set stores the records as they arrive,
while the adjacency map must group them by origin stop first. The better choice
depends on which of those two operations the application performs more often, and on
whether the measured cost of the scan matters at the network sizes involved.

Now run ordinary client code:

```java
TransitNetwork original = TransitNetwork.empty(Set.of(ubc, wesbrook));
TransitNetwork extended = original.withConnection(ubc, wesbrook);

System.out.println(original.hasDirectConnection(ubc, wesbrook));
System.out.println(extended.hasDirectConnection(ubc, wesbrook));
```

On Eclipse Temurin 25.0.4.1, the complete program printed:

```text
false
true
```

The observation does not reveal a map or a connection set. That is
**representation independence**: client behaviour depends on the ADT specification,
not on which valid representation implements it.

Representation independence has requirements. The implementations must realise the
same abstract values, satisfy the same operation specifications, and prevent clients
from observing representation-only differences. A public downcast, leaked mutable
collection, promised iteration order, or implementation-specific exception can make
client behaviour depend on the representation.

It also has limits. Performance can be observable and may matter to a specification
with explicit complexity bounds. Serialisation formats, reflection, and debugging
tools can reveal concrete classes. We do not pretend implementations are physically
indistinguishable. We design ordinary program dependencies so clients need not rely
on those differences.

Consider replacing the adjacency-map implementation after the system has been
deployed. A client that uses only `TransitNetwork` operations requires no source
change. A client that casts the result to `AdjacencyMapNetwork` must change with the
implementation. This is the practical value of representation independence: the
implementation can respond to measured workloads without requiring every caller to
migrate. The replacement must still preserve stop membership, edge direction,
exception behaviour, immutability, and returned-collection guarantees.

## 8. Run Contract Tests Against Both Implementations

To test representation independence, the companion project supplies both factories
to one parameterised test suite. One of its tests is:

```java
@ParameterizedTest(name = "{0}: producer leaves original unchanged")
@MethodSource("implementations")
void producerLeavesOriginalUnchanged(
        String ignoredName,
        Function<Set<StopId>, TransitNetwork> factory) {
    TransitNetwork original = factory.apply(Set.of(UBC, WESBROOK, ALMA));
    TransitNetwork extended = original.withConnection(UBC, WESBROOK);

    assertFalse(original.hasDirectConnection(UBC, WESBROOK));
    assertTrue(extended.hasDirectConnection(UBC, WESBROOK));
    assertEquals(Set.of(WESBROOK),
            extended.directDestinationsFrom(UBC));
}
```

The test observes promises: old value unchanged, new edge present, correct direct
destination. It does not inspect fields, assert a concrete class, or depend on set
iteration order. The same tests also cover isolated stops, direction, invalid
arguments, duplicate additions, input aliasing, and unmodifiable results.
These tests make representative contract obligations executable. Review remains
necessary for obligations and inputs that the test suite does not cover.

White-box tests still have a place. An implementation may need focused tests for a
complicated private algorithm. Every implementation must also pass the shared
contract tests before the factory can substitute it for another implementation.
The shared factory also keeps implementation-specific setup out of individual test
cases.

> **Design principle: expose only the operations clients need, and keep the
> representation data structures private.**

Client code then reads in transit terms rather than in map operations, and a
correctness argument about the network has to consider only the specified operations
instead of every mutation a client could perform on an exposed map.

## 9. Common Misconceptions

### “An ADT is a class with private fields”

Private fields are useful access control, but they do not define the abstract values
or specify the operations. A class can keep every field private while returning a
mutable alias, exposing representation-shaped methods, or leaving its behaviour
ambiguous.

The abstraction comes from the specified value space and operations. Java access
control helps enforce the boundary.

### “If two implementations pass today’s tests, they are interchangeable”

Tests sample behaviour; the specification defines it. Two implementations may agree
on every tested input and disagree on an untested boundary, mutation policy, or
exception. Shared tests provide evidence, not a new definition of the ADT.

Review the tests against the contract, then review each implementation's reasoning.
The next chapter examines the implementation's correctness obligations.

## 10. Review a Generated ADT

Generated code often exposes a familiar container through its public operations.
Before accepting it, complete these checks:

- State the abstract values without referring to Java fields.
- List the operations clients need.
- Identify every public type, method name, return value, or exception that exposes
  the chosen representation.
- Check creator, producer, and observer specifications at boundary cases.
- Trace whether a client can mutate the representation through an argument or
  result.
- Apply the same contract to a substantially different candidate representation.
- Separate tests that observe the contract from tests that inspect the current
  implementation.

Ask an assistant for alternatives if that helps compare designs, but verify the
result. Renaming `getMap` to `getNetworkData` still exposes the same representation.

## Try the Abstraction Boundary

### 1. Classify the operations

Classify each operation on Java's immutable `String` ADT as creator, producer, or
observer: `String.valueOf(42)`, `text.substring(1)`, `text.length()`, and
`text.charAt(0)`. Can one operation fit more than one reasonable classification?
Defend the perspective you choose.

### 2. Find the representation exposure

Suppose `TransitNetwork` adds this method:

```java
HashMap<StopId, HashSet<StopId>> getOutgoingMap()
```

Identify three dependencies a client could acquire. Propose transit operations that
serve plausible client needs without promising the map-of-sets representation.

### 3. Predict the two values

Trace this code without running it:

```java
TransitNetwork a = TransitNetwork.empty(Set.of(UBC, WESBROOK));
TransitNetwork b = a.withConnection(UBC, WESBROOK);
TransitNetwork c = b.withConnection(UBC, WESBROOK);
```

What must be true of the three abstract values? Which object-identity relationships
are permitted but not required?

### 4. Design a contract test

Write one black-box test that distinguishes a directed network from an undirected
one. Write another that catches a creator which drops isolated stops. Explain which
postcondition each test checks.

### 5. Compare representations

For a sparse network with frequent direct-destination queries, compare an adjacency
map with a connection set. Consider query work, construction work, memory overhead,
and ease of validating the data. Choose one for that workload and state what evidence
could change your choice.

## Summary

Abstract values and specified operations define an ADT. Creators introduce values,
producers derive values, observers reveal information, and mutators change existing
values. Our immutable network needs no mutators.

The `TransitNetwork` interface gives clients a small transit vocabulary. A factory
returns that abstraction while a package-private implementation snapshots and owns
its representation. We can store an adjacency map or separate stop and connection
sets without changing contract-respecting clients.

That freedom is representation independence. Access control, specifications,
immutable boundaries, and contract tests all help preserve it. The next question is
how an implementer determines whether a particular map or pair of sets represents a
valid network. Chapter 6 defines that relationship between concrete fields and
abstract values.

## References

- Barbara Liskov and Stephen Zilles, [“Specification Techniques for Data Abstractions”](https://csg.csail.mit.edu/CSGArchives/memos/Memo-117.pdf)
- Barbara Liskov and Stephen Zilles, “Programming with Abstract Data Types,”
  *Association for Computing Machinery Special Interest Group on Programming
  Languages (ACM SIGPLAN) Notices* 9(4), 1974, digital object identifier (DOI)
  `10.1145/942572.807045`
- [Java Language Specification, access control](https://docs.oracle.com/javase/specs/jls/se25/html/jls-6.html#jls-6.6)
- [Java Platform, Standard Edition (Java SE) 25 `Set` interface](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Set.html)
- [JUnit 6.1.3 User Guide, parameterized tests](https://docs.junit.org/6.1.3/writing-tests/parameterized-classes-and-tests.html)
