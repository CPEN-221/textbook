# Chapter 5 | ADTs and Representation Independence

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

## 1. Start with the Abstract Value

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
does not change the receiver. Immutability gives clients a simple temporal rule:
once they hold a network, its stops and connections do not change underneath them.

## 2. Choose Operations for Clients

A representation-first API is easy to spot:

```java
Map<StopId, Set<StopId>> adjacencyMap()
```

The method asks every client to understand a map of sets. It also forces the ADT to
keep that shape or emulate it forever. A client trying to answer “is this a direct
connection?” should not have to know which bucket owns the answer.

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

The complete interface in the
[companion project](../../examples/chapters-05-06/src/main/java/ca/ubc/ece/cpen221/transit/TransitNetwork.java)
includes the specifications. The short view above reveals the vocabulary: stops,
direct destinations, and connections. No method returns “the representation.”

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

The categories overlap at the edges. `withConnection` may return `this` when the
connection already exists. It still acts as a producer: its contract describes the
returned abstract value, not a fresh object identity. A test that insists on
`result != network` would claim a promise the ADT never made.

The classification also exposes omissions. If an API has a creator and three
mutators but no observer, clients cannot learn anything about the value except by
remembering its history. If it returns a mutable `Map` as its only observer, it has
mixed observation with unrestricted mutation. The table helps us review the design;
an ADT does not need one operation in every category.

## 4. Specify the Boundary

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

The producer says what changes and, just as importantly, what does not:

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
depend on the current hash-table order. If stable order becomes a requirement, we can
add it to the specification and accept the associated implementation cost.

Specifications do not need to expose every implementation failure. Running out of
memory, for example, is not useful network behaviour to restate on each method.
They do need to settle predictable boundary cases such as `null`, unknown stops,
self-connections, mutation, and ordering.

## 5. Put the Implementation Behind a Factory

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
constructed that class directly, the implementation name would leak into method
signatures and tests. Changing representations would then become a migration rather
than a private edit.

A factory chooses an implementation while returning the abstraction. We could later
make that choice depend on input size or a configuration setting, provided every
returned object satisfies the same contract.

## 6. Implement Without Reopening the Boundary

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
was retained. If any of those facts changed, returning the field's value could
expose the representation.

The public contract tells clients what they may assume. The private constructor and
helpers may depend on representation details. Data abstraction requires us to keep
those dependencies out of the public API.

## 7. Change the Representation

Suppose feed import gives us a set of distinct directed connections. A second
implementation stores exactly that shape:

```java
final class ConnectionSetNetwork implements TransitNetwork {
    private final Set<StopId> stops;
    private final Set<Connection> connections;
}
```

Its direct-destination observer scans and filters `connections`; the adjacency-map
implementation performs a lookup. The connection set makes bulk construction and
whole-edge operations natural. The map makes neighbourhood queries natural. The
better choice depends on the operations and performance requirements of the
application.

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

Representation independence has requirements. The implementations must realize the
same abstract values, satisfy the same operation specifications, and prevent clients
from observing representation-only differences. A public downcast, leaked mutable
collection, promised iteration order, or implementation-specific exception can poke
a hole through the boundary.

It also has limits. Performance can be observable and may matter to a specification
with explicit complexity bounds. Serialization formats, reflection, and debugging
tools can reveal concrete classes. We do not pretend implementations are physically
indistinguishable. We design ordinary program dependencies so clients need not rely
on those differences.

## 8. Test the Contract Against Both Implementations

To test representation independence, the companion project supplies both factories
to one parameterized test suite. One of its tests is:

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

White-box tests still have a place. An implementation may need focused tests for a
complicated private algorithm. Every implementation must also pass the shared
contract tests before the factory can substitute it for another implementation.

Our design principle is:

> **Design principle: make clients depend on the smallest useful behavioural
> vocabulary, not on the data structures that happen to implement it.**

This principle also makes clients easier to read because their operations use domain
terms. It simplifies correctness arguments by restricting clients to specified
operations instead of arbitrary map mutation.

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
The next chapter develops that inside view.

## 10. Reviewing a Generated ADT

Generated code often begins with a familiar container and lets that container shape
the API. Before accepting it, ask:

- What are the abstract values, stated without Java fields?
- Which operations do clients actually need?
- Does any public type, method name, return value, or exception expose the chosen
  representation?
- Are creators, producers, and observers specified at boundary cases?
- Can a client mutate the representation through an argument or result?
- Would the same contract make sense for a substantially different representation?
- Do the tests observe the contract or inspect the current implementation?

Ask an assistant for alternatives if that helps compare designs, but verify the
result. Renaming `getMap` to `getNetworkData` still exposes the same representation.

## Try the Abstraction Boundary

### 1. Classify the operations

Classify each operation on Java's immutable `String` ADT as creator, producer, or
observer: `String.valueOf(42)`, `text.substring(1)`, `text.length()`, and
`text.charAt(0)`. Can one operation fit more than one reasonable classification?
Defend the perspective you choose.

### 2. Find the representation leak

Suppose `TransitNetwork` adds this method:

```java
HashMap<StopId, HashSet<StopId>> getOutgoingMap()
```

Identify three dependencies a client could acquire. Propose domain operations that
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

An ADT is defined by abstract values and specified operations. Creators introduce
values, producers derive values, observers reveal information, and mutators change
existing values. Our immutable network needs no mutators.

The `TransitNetwork` interface gives clients a small domain vocabulary. A factory
returns that abstraction while a package-private implementation snapshots and owns
its representation. We can store an adjacency map or separate stop and connection
sets without changing contract-respecting clients.

That freedom is representation independence. Access control, specifications,
immutable boundaries, and contract tests all help preserve it. The next question is
how an implementer determines whether a particular map or pair of sets represents a
valid network. Chapter 6 defines that relationship between concrete fields and
abstract values.

## Sources and provenance

This chapter was written anew for the Fall 2026 CPEN 221 notes. It retains the old
manuscript's central ideas that an ADT is defined by its specification, that ADT
operations can be classified by their relationship to the abstract type, and that
clients should be independent of representation. The outline, prose, transit-network
API, two implementations, tests, and examples are new. No old `MyString`, `Map`,
hash-table, car-control, or inherited figure was reused. Equality and hashing are
deliberately deferred to Chapter 7.

Technical references:

- Barbara Liskov and Stephen Zilles, “Programming with Abstract Data Types,”
  *SIGPLAN Notices* 9(4), 1974, DOI `10.1145/942572.807045`
- [MIT 6.031: Abstract Data Types](https://web.mit.edu/6.031/www/sp21/classes/10-abstract-data-types/)
- [Java Language Specification, access control](https://docs.oracle.com/javase/specs/jls/se25/html/jls-6.html#jls-6.6)
- [Java SE 25 `Set` interface](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Set.html)
- [JUnit 6.1.3 User Guide, parameterized tests](https://docs.junit.org/6.1.3/writing-tests/parameterized-classes-and-tests.html)
