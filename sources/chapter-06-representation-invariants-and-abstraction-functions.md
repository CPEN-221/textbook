# Chapter 6 | Representation Invariants and Abstraction Functions

The `TransitNetwork` interface prevents clients from accessing the adjacency map.
The implementation still has to construct and query that map correctly.

Suppose one destination set contains `ALMA`, but `ALMA` is not a key in the map.
`directDestinationsFrom(UBC)` may include it, while
`directDestinationsFrom(ALMA)` rejects it as an unknown stop. These two results are
inconsistent.

Private fields prevent a client from creating that state directly. They do not
prevent a constructor or producer from creating it by mistake. We need to state
which concrete states are meaningful and how each meaningful state corresponds to
the graph promised by the abstract data type (ADT).

We use two definitions to describe this relationship. A **representation invariant
(RI)** selects the valid representations. An **abstraction function (AF)** explains
which abstract value each valid representation denotes. Together they state what
constructors must establish, what operations must preserve, and what an internal
checker should reject.

By the end of this chapter, you should be able to:

- distinguish the abstract value space from the representation space;
- write an abstraction function for a Java representation;
- write a representation invariant that is strong enough for the abstraction
  function and implementation algorithms;
- distinguish an abstract invariant from a representation invariant;
- implement and place a `checkRep` method appropriately;
- argue that creators establish, producers preserve, and observers do not expose a
  representation invariant;
- explain what invariant checking can and cannot establish.

## 1. Abstract and Representation Spaces

The `TransitNetwork` specification describes an **abstract space** `A`: all finite
directed graphs over `StopId` values with no self-connections. A client reasons about
vertices and edges in this space.

`AdjacencyMapNetwork` has a **representation space** `R` determined by this field:

```java
private final Map<StopId, Set<StopId>> outgoing;
```

Candidate representation values include maps with several keys, an empty map, and
maps whose destination sets mention other keys. Before the constructor checks them,
they also include maps with `null` parts or destinations that have no key. Java's
generic types say that keys and values have certain declared types. They do not
express all the relationships our graph requires.

The implementation uses selected values in `R` to realize values in `A`. Some
candidate maps are inconsistent and must not represent an abstract network value.

## 2. State the Abstraction Function

For a valid adjacency map `r`, the correspondence is:

```text
AF(r) is the directed graph (V, E) where
V = r.outgoing.keySet(), and
E = { (from, to) | to is in r.outgoing.get(from) }.
```

This is the **abstraction function**, written `AF: R_valid -> A`. It maps a concrete
representation to the abstract value that clients observe. The function is a
reasoning device and a documentation obligation; it need not be an executable Java
method.

Trace a small value. Suppose the map is:

```text
UBC      -> {WESBROOK}
WESBROOK -> {ALMA}
ALMA     -> {}
```

The abstraction function maps this representation to three vertices and two directed
edges: UBC to Wesbrook, and Wesbrook to Alma. The empty set beside Alma is
significant. Alma is a vertex even though it has no outgoing edge.

Several representations may map to the same abstract value. A map's iteration order
does not belong to our graph, so two maps that iterate differently can mean the same
network. An abstraction function therefore need not be one-to-one.

The abstraction function must be precise enough to settle every public observation.
If we wrote only “the map stores the network,” we would not know whether keys with
empty sets count as stops, whether direction matters, or whether duplicate-looking
data has meaning.

## 3. Define the Representation Invariant

The **representation invariant**, or **RI**, is a predicate over candidate
representations. It is true exactly for the representations our implementation
allows between public operations.

For `AdjacencyMapNetwork`:

```text
RI(r) is true exactly when:
1. r.outgoing is non-null;
2. every key, destination set, and destination is non-null;
3. every destination is also a key in r.outgoing; and
4. no key occurs in its own destination set.
```

Conditions 1 and 2 make the map safe for our implementation to traverse. Condition
3 coordinates the two roles a stop can play: a destination must also belong to the
network's vertex set. Condition 4 expresses the ADT's no-self-connection rule in
this representation.

That last rule starts in the abstract space. “A network has no self-connection” is
an **abstract invariant**: a property of every value the public ADT permits. The RI
is representation-specific. A boolean adjacency matrix would enforce the same
abstract invariant with a different concrete condition, such as a `false` diagonal.

Not every useful RI condition comes from an abstract invariant. A cached edge count
would need to equal the number of stored edges even if clients never see the cache.
A sorted-array representation would need to remain sorted so binary search works.
Those obligations come from an implementation choice.

## 4. Implement `checkRep`

An executable checker converts a violated assumption into evidence near its source:

```java
private void checkRep() {
    assert outgoing != null : "outgoing map is null";
    for (Map.Entry<StopId, Set<StopId>> entry : outgoing.entrySet()) {
        StopId from = entry.getKey();
        Set<StopId> destinations = entry.getValue();
        assert from != null : "null origin";
        assert destinations != null : "null destination set";
        for (StopId destination : destinations) {
            assert destination != null : "null destination";
        }
        assert outgoing.keySet().containsAll(destinations)
                : "destination outside the stop set";
        assert !destinations.contains(from) : "self connection";
    }
}
```

We use Java assertions because an RI violation is an internal implementation bug,
not a client input error. Assertions are disabled by default unless the Java Virtual
Machine (JVM) receives `-ea` (or `-enableassertions`). The companion build enables
them while running tests.
Public argument checks still use ordinary conditionals and documented exceptions;
Chapter 3 explained why assertions are unsuitable for enforcing preconditions.

There is a small defensive detail in the loop. We inspect each destination for
`null` instead of calling `destinations.contains(null)`. Some unmodifiable collection
implementations are permitted to reject an ineligible query with
`NullPointerException`. An invariant checker should report the broken invariant, not
trip over its own inspection.

`Map.copyOf` and `Set.copyOf` already reject `null` while this implementation builds
its snapshots. We retain the non-null clauses in the RI because they document the
assumptions used by every method. Some checks are redundant at runtime and still
support the correctness argument.

## 5. Establish and Preserve the RI

Writing an RI comment does not enforce it. We must inspect every operation that
creates or changes a representation.

For a mutable ADT, the standard obligations are:

1. every creator establishes the RI;
2. every mutator assumes the RI on entry and re-establishes it before returning;
3. no representation exposure lets a client mutate the rep between calls.

Our network is immutable, so producers build new representations rather than
changing the receiver. Creators must establish the RI, producers must return a new
value that satisfies it, and observers must not mutate or expose mutable state.

### The constructor creates an owned representation

The private constructor snapshots the nested containers before checking them:

```java
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
```

The copies prevent a caller from changing the field after `checkRep` returns. The
checker then verifies cross-entry relationships that `Map.copyOf` cannot know. When
the constructor completes normally, the object owns an unmodifiable valid rep.

Our creator supplies one empty destination set for every requested stop. It thereby
establishes the non-null and membership conditions and preserves isolated vertices.
The constructor checks the result.

### The producer preserves the RI

The producer creates a modified copy:

```java
@Override
public TransitNetwork withConnection(StopId from, StopId to) {
    requireDistinctMembers(from, to);
    if (outgoing.get(from).contains(to)) {
        return this;
    }

    Map<StopId, Set<StopId>> updated = new HashMap<>(outgoing);
    Set<StopId> destinations = new HashSet<>(outgoing.get(from));
    destinations.add(to);
    updated.put(from, Set.copyOf(destinations));
    return new AdjacencyMapNetwork(updated);
}
```

`requireDistinctMembers` establishes that both endpoints are existing keys and are
different. The method copies the outer map and the one destination set it changes.
It leaves the receiver unchanged. The private constructor takes a full immutable
snapshot and checks the result before returning the new object to the caller.

This is a local correctness argument. Assuming the receiver satisfies the RI and the
argument check succeeds, the only new destination is a non-null existing key
different from its origin. Every unchanged entry remains valid. Therefore the new
map satisfies the RI.

The duplicate case returns `this`. That preserves the RI because it creates no new
representation and the receiver was valid on entry.

### Observers do not expose the representation

`stops()` returns the key-set view of an unmodifiable map.
`directDestinationsFrom` returns an unmodifiable destination set. `StopId` values are
immutable. None of these paths gives a client a mutator for a reachable rep object.

If the field held mutable sets, checking after construction would not be enough. A
leaked alias could invalidate the rep while no ADT method was running. Representation
exposure breaks encapsulation and the invariant argument.

## 6. Limits of `checkRep`

An RI tells us whether a concrete state is well formed. It does not tell us whether
that state is the *right* result of an operation.

Imagine an `empty(stops)` implementation that returns a valid empty map regardless
of its argument. The map satisfies our RI: it contains no nulls, outside
destinations, or self-connections. Its abstraction is the empty graph. But the
creator's postcondition says that the result contains exactly the requested stops.
For a nonempty argument, the method is wrong.

This distinction separates two questions:

- **Representation correctness:** does the rep satisfy the RI, and what value does
  the AF assign it?
- **Operation correctness:** assuming the precondition, does the operation produce
  the abstract value required by its postcondition?

`checkRep` helps with the first. Contract tests and reasoning about each operation
address the second. One does not subsume the other.

The companion suite includes a test that creates an empty network with two isolated
stops and observes both. That test catches the valid-but-wrong empty-map
implementation. Another test checks that a producer leaves the original network
unchanged. Neither fact appears in the RI because both concern operation history and
specified results, not the well-formedness of one representation.

## 7. Define the RI and AF for a Second Representation

Chapter 5 introduced a second representation:

```java
private final Set<StopId> stops;
private final Set<Connection> connections;
```

Its abstraction function is different:

```text
AF(r) is the directed graph (V, E) where
V = r.stops, and
E = { (c.from(), c.to()) | c is in r.connections }.
```

Its RI is also different:

```text
RI(r) is true exactly when:
1. r.stops, r.connections, and their elements are non-null; and
2. both endpoints of every connection occur in r.stops.
```

The RI does not repeat the no-self-connection rule because `Connection` is a record
whose own specification and constructor require two distinct, non-null stops. The
network implementation may rely on the public guarantees of its rep types. If
`Connection` later permitted self-connections, the network RI would need an explicit
clause or a stronger component type.

Likewise, a `Set` already has set semantics. We need not write “connections contains
no duplicates” in the RI; the field's abstract type makes duplicates unobservable.
An array representation would need a concrete uniqueness condition if its algorithms
depended on one stored copy per edge.

The public `TransitNetwork` specification remains unchanged while RI and AF change
with the representation. These definitions belong inside the implementation, close
to its fields. If they became client requirements, clients would depend on private
representation choices.

Both implementations pass the same 15 contract-test invocations. This is evidence
that they produce the same public behaviour for those cases. It is not a
mathematical proof over every possible graph.

## 8. Develop an RI Systematically

To develop a representation invariant, inspect the representation from five
directions.

1. **Make the AF meaningful.** Exclude rep values for which you cannot assign an
   unambiguous abstract value.
2. **Support the algorithms.** Record ordering, balance, acyclicity, uniqueness, or
   other conditions that private algorithms assume.
3. **Coordinate fields.** Relate cached sizes, parallel collections, indices, and
   references that must agree.
4. **Prevent unintended failures.** Rule out `null`, invalid indices, missing keys,
   and similar states that would make ordinary operations fail outside their
   specifications.
5. **Carry abstract invariants into the rep.** Translate every constraint on valid
   abstract values into a concrete condition.

Do not include how the object arrived there. “Connections were added in feed order”
is a history property unless the current rep records enough information to check it.
Do not restate facts guaranteed by Java primitive types or by the specifications of
rep components. An RI should be strong enough for the implementation and no stronger
than necessary.

An unnecessarily strong invariant creates work and may eliminate useful
representations. Requiring every stop to have an outgoing edge would simplify one
loop, but it would make an isolated terminal stop impossible to represent. The RI
must permit every value allowed by the ADT, including isolated terminal stops.

Our design principle is:

> **Design principle: document the meaning and validity of the representation, then
> verify that every creator and producer establishes those conditions.**

The AF defines what each valid state means. The RI defines which states may occur.
The operation proof establishes that each transition produces the abstract value
required by its specification. Keeping these obligations separate makes each one
easier to inspect.

## 9. Common Misconceptions

### “The representation invariant is a private precondition”

A public method precondition assigns responsibility to the client. The RI is an
implementation obligation. A correct client cannot be blamed when a producer puts
an outside destination into a private map.

Public methods may *assume* the RI on entry because earlier implementation code was
responsible for establishing it. That assumption is part of an internal proof, not a
new demand on callers.

### “If `checkRep` passes, the implementation is correct”

A valid representation can encode the wrong abstract result. The empty-map example
passes `checkRep` while violating the creator's postcondition. A checker can also
contain a bug, omit an expensive condition, or be disabled with assertions.

Treat a successful check as evidence that the tested conditions hold. It does not
establish that every operation satisfies its specification.

### “The abstraction function should return a Java object”

The abstract graph is a mathematical model used in the specification. We do not need
to allocate a second graph object whenever we call an observer. Implementations
compute the observations promised by the ADT as if the abstract value existed.

## 10. Review Generated Representation Code

Generated implementations often contain plausible fields and thin getters without a
clear representation argument. Require that argument before trusting the design:

- What is the abstract value space?
- What is the AF for these exact fields?
- For which candidate field values is that AF meaningful?
- Which extra conditions do the algorithms assume?
- Which abstract invariants need concrete enforcement?
- Does every creator establish the RI?
- Does every producer or mutator preserve it on success and on exceptional exit?
- Can an alias bypass those operations?
- Which postconditions need tests because the RI cannot express them?

Then compare the prose with the code. If the RI says "all destinations are known"
while the checker tests only for `null`, the checker does not implement the stated
RI.

## Try the Representation

### 1. Evaluate candidate maps

For each map, decide whether it satisfies the adjacency-map RI. For valid maps,
state the graph produced by the AF.

```text
{ UBC -> {}, WESBROOK -> {} }
{ UBC -> {WESBROOK} }
{ UBC -> {UBC} }
{ UBC -> {WESBROOK}, WESBROOK -> {} }
```

For each invalid map, name the exact violated clause rather than saying only
“invalid.”

### 2. Separate RI from postcondition

A creator receives `{UBC, WESBROOK}` and returns the representation
`{UBC -> {}, WESBROOK -> {}}`. Does the rep satisfy the RI? Does the result satisfy
the creator's postcondition? Now answer both questions if it returns `{}`.

### 3. Trace preservation

Assume the map satisfies the RI and trace `withConnection(UBC, WESBROOK)`. For each
RI clause, identify the line or prior fact that preserves it. What changes in the
argument when the edge already exists?

### 4. Design an array representation

Represent the same network with a `List<StopId>` and a square `boolean[][]`. Write an
AF and RI. Include dimensions, uniqueness of stop identifiers, row/column meaning,
and the no-self-connection abstract invariant. Which condition prevents one stop
from having two matrix indices?

### 5. Place the checker

Suppose a mutable network adds `removeStop`. During the method, it first removes the
key and then removes incoming edges. The RI is temporarily false between those
steps. Where should `checkRep` run? What must happen if an exception can escape from
the middle?

## Summary

An implementation connects two spaces. The representation space contains concrete
field values; the abstract space contains the values promised to clients. The
abstraction function maps valid reps to abstract values. The representation invariant
selects which reps are valid.

For the adjacency map, the AF defines keys as vertices and destination memberships as
edges. The RI rules out null parts, outside destinations, and self-connections. The
constructor snapshots and checks its input, the producer preserves the conditions,
and observers expose only immutable values. A connection-set implementation needs a
different AF and RI while keeping the same public ADT.

Invariant checking reports malformed internal states when `checkRep` runs. It does
not prove postconditions or replace contract tests. Together, AF, RI, operation
reasoning, and tests form a correctness argument that can be inspected and updated.

The next chapter will ask when two separately represented ADT values count as equal,
how that decision interacts with hashing, and what subtypes may promise without
surprising their clients.

## References

- Barbara Liskov and John Guttag, *Program Development in Java: Abstraction,
  Specification, and Object-Oriented Design*, Addison-Wesley, 2001
- [Java Language Specification, assertions](https://docs.oracle.com/javase/specs/jls/se25/html/jls-14.html#jls-14.10)
- [Java SE 25 `Map.copyOf`](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Map.html#copyOf(java.util.Map))
- [Java SE 25 unmodifiable collection factories](https://docs.oracle.com/en/java/javase/25/core/creating-immutable-lists-sets-and-maps.html)
