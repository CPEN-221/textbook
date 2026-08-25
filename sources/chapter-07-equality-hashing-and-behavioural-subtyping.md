# Chapter 7 | Equality, Hashing, and Behavioural Subtyping

> And things which are equal to the same are equal to one another.
>
> <cite>Euclid, *The Elements*, Book I</cite>

A journey planner stores a reliability score for each journey option. Later, it
constructs a new `JourneyOption` with the same origin, destination, departure,
arrival, accessibility status, and service description. The second object should
retrieve the score stored under the first one.

This lookup depends on several design decisions. The program
must decide when two objects represent the same value. A hash-based collection must
place equal values where it can find them. A subtype must also keep the promises made
by its supertype, or code written for the supertype will behave differently when the
subtype arrives.

Java supplies mechanisms for all three concerns, but it cannot choose the meaning of
equality for an application. That meaning comes from the abstraction represented by
the type.

By the end of this chapter, you should be able to:

- distinguish reference identity from equality of abstract values;
- state and apply the contracts of `equals` and `hashCode`;
- explain how a hash-based collection uses both methods;
- choose the state that participates in a type's equality relation;
- identify the risks of mutable hash keys;
- distinguish equality from ordering; and
- determine whether a subtype preserves the behavioural contract of its supertype.

## 1. The Meaning of Journey Equality

Consider two requests for a journey from UBC to Waterfront. They may cause the
planner to allocate two Java objects even when every journey detail is the same.
Reference identity and value equality answer different questions:

- `first == second` asks whether both expressions refer to the same object;
- `first.equals(second)` asks whether the two objects should be treated as the same
  value according to the class's equality relation.

Unless a class overrides `equals`, it inherits `Object.equals`, whose equality
relation is object identity. That default is suitable for an object whose identity
matters independently of its current fields. A database session, open socket, or
running thread is not interchangeable with another merely because selected
properties match.

A journey option has a different abstraction. In our current model, its abstract
value consists of an origin, a destination, two instants, an accessibility property,
and a service description. Two allocations with the same six components represent
the same option. A Java record expresses that decision directly:

```java
public record JourneyOption(
        String origin,
        String destination,
        Instant departure,
        Instant arrival,
        boolean stepFree,
        String displayLabel) {

    public JourneyOption {
        Objects.requireNonNull(origin);
        Objects.requireNonNull(destination);
        Objects.requireNonNull(departure);
        Objects.requireNonNull(arrival);
        Objects.requireNonNull(displayLabel);
        if (arrival.isBefore(departure)) {
            throw new IllegalArgumentException("arrival precedes departure");
        }
    }
}
```

A record's generated `equals` compares corresponding component values, and its
generated `hashCode` uses those same components. The generated methods fit this
abstraction because every component belongs to the value.

Suppose a later interface shows a translated label supplied by the user interface.
That label may not belong to journey equality. Adding it as a record component would
then change the equality relation. We could instead store it in a separate view
object, or use an ordinary final class with deliberately implemented equality. The
choice depends on what the type represents, not on which fields happen to be
available.

> **Design principle:** Define equality from the abstract value represented by the
> type. Then derive `equals` and `hashCode` from the same immutable state.

## 2. The `equals` Contract

For non-null references, `Object.equals` requires an equivalence relation:

- **reflexive:** `x.equals(x)` is true;
- **symmetric:** `x.equals(y)` has the same result as `y.equals(x)`;
- **transitive:** if `x` equals `y` and `y` equals `z`, then `x` equals `z`;
- **consistent:** repeated comparisons have the same result while relevant state
  remains unchanged; and
- **non-null:** `x.equals(null)` is false.

These conditions are observable by clients. A set relies on them when it decides
whether a value is already present. If equality is asymmetric, the result can depend
on which object receives the method call. If equality is not transitive, no
collection can divide values into coherent equivalence classes.

Inheritance makes hand-written equality difficult. Imagine a `JourneyOption`
subclass that adds a fare. If the superclass compares only the original fields while
the subclass also compares the fare, a superclass value can consider a subclass
value equal while the subclass rejects the superclass value. Symmetry fails. If the
subclass ignores its fare, two objects with different advertised values compare
equal.

An implementation template cannot resolve this semantic conflict.
Possible designs include making value classes final, including all value state in a
record, or using composition for additional information. Each choice states which
values the program considers interchangeable.

An `equals` implementation must also accept `Object`. It should return false for an
object outside the equality domain instead of throwing because the argument has an
unexpected type. Records generate this check. For an ordinary final class, a typical
implementation tests identity, tests the class, casts, and compares the value fields.
The exact class test is often appropriate for a final value class. More elaborate
class hierarchies require a fresh analysis of symmetry and substitutability.

## 3. The `hashCode` Contract

The `hashCode` contract contains the implication that matters most in daily work:

```text
if x.equals(y), then x.hashCode() == y.hashCode()
```

The converse is not required. Unequal objects may have the same hash code. A hash
code has a limited number of possible `int` values, while a program may have far more
distinct values.

A `HashMap` uses a key's hash code to narrow its search and equality to identify a
matching key among candidates. The specification allows implementations to avoid
calling `equals` when the hash codes differ. If a class overrides `equals` but
inherits identity-based `Object.hashCode`, two equal allocations can receive
different hash codes. A lookup using the second allocation may search somewhere
other than the location used for the first insertion.

The companion example uses a record, so both methods agree:

```java
Map<JourneyOption, Integer> reliability = new HashMap<>();
reliability.put(stored, 94);
return "equal=" + stored.equals(query)
        + ", reliability=" + reliability.get(query);
```

The complete program constructed two separate but equal records. On the validated
Java 25 run, it printed:

```text
equal=true, reliability=94
```

The number returned by `Object.hashCode` is not specified to be a memory address.
Some implementations may derive identity hash codes using implementation details,
but portable Java code cannot infer an address or object layout from the value.

### Hash quality affects performance, not correctness

A legal implementation could return `0` for every object. Equal values would have
equal hash codes, so the contract would hold. A large hash table would then place all
keys in one collision group and lose the usual performance benefit of hashing.

A useful hash function incorporates the same value fields as `equals` and spreads
common inputs reasonably across `int` results. `Objects.hash` can provide a concise
implementation. Performance-sensitive code may use a direct computation to avoid
the array allocation associated with its variable arguments. Correctness comes
first: an omitted equality field can produce excessive collisions, while an extra
field can violate the contract.

## 4. Mutable Hash Keys

Suppose a mutable key uses its destination and departure time for equality and
hashing. The program inserts the key into a `HashMap`, then changes its departure
time. A subsequent lookup recomputes a different hash code and searches according to
the new value. The entry remains in the location selected by the old value.

The `Map` specification says that behaviour is unspecified when a key changes in a
way that affects equality while the key is stored. The map does not receive a
notification that it should relocate the entry.

Immutability prevents this failure. `JourneyOption` components are final, and the
component types used here are immutable. A record is only shallowly immutable,
however. If a component referred to a mutable list and equality examined that list,
client mutation could still change the record's hash code. Chapter 4's ownership
rules still apply.

When mutable domain objects are necessary, stable immutable identifiers can serve as
keys. A `TripId` may remain fixed while a separate `TripStatus` changes. This design
also clarifies whether the application means “this particular scheduled trip” or
“whatever trip currently has these displayed properties.”

## 5. Equality and Ordering Serve Different Contracts

A comparator can order journey options by arrival time:

```java
Comparator<JourneyOption> byArrival =
        Comparator.comparing(JourneyOption::arrival);
```

Two options that arrive at the same instant compare as zero even if their origins,
routes, or accessibility properties differ. The comparator therefore defines
equivalence classes that are coarser than `equals`.

A `TreeSet` exposes this difference because it uses its ordering to
decide whether an element is already present. With `byArrival`, adding a second
journey at the same arrival time may leave the set unchanged. A `HashSet` using the
record's equality would retain both values.

The `Comparable` specification strongly recommends, but does not require, a natural
ordering consistent with `equals`. A type whose natural ordering is inconsistent
must document the fact. `BigDecimal` is the standard library's prominent example:
values such as `4.0` and `4.00` compare as numerically equal but are not equal under
`equals` because scale participates in equality.

For journey options, an arrival-only order is useful for presentation but incomplete
as a natural ordering. A total display order can add tie-breakers:

```java
Comparator<JourneyOption> displayOrder =
        Comparator.comparing(JourneyOption::arrival)
                .thenComparing(JourneyOption::departure)
                .thenComparing(JourneyOption::origin)
                .thenComparing(JourneyOption::destination)
                .thenComparing(JourneyOption::displayLabel);
```

Even that comparator omits `stepFree`, so it is not consistent with the record's
equality. Whether to add the final tie-breaker depends on the collection's contract.
The collection contract must make the decision explicit.

### Collection equality crosses implementation boundaries

Java collection interfaces define equality at the interface level. Two sets are
equal when they contain equal elements, regardless of whether one is a `HashSet` and
the other is a tree-based or immutable implementation. Two maps are equal when they
contain the same key-value mappings. Their iteration order and internal tables do not
participate unless a more specific type deliberately states another contract.

Interface-level collection equality supports representation independence. A transit
API can change an internal
map implementation without changing the abstract map value returned to a client.
The element contracts still matter. If `JourneyOption` has defective equality, a map
containing those options cannot repair it.

Lists use position-sensitive equality. A list of stops from UBC through Oakridge to
Waterfront is not equal to a list containing the same stops in another order. The
collection abstraction determines whether order participates. Selecting `List`,
`Set`, or `Map` in an API therefore communicates a semantic decision, not only a
storage choice.

## 6. Behavioural Subtyping

Equality is one place where substitutability fails, but the broader issue applies to
every method contract. The **behavioural subtyping principle** says that code written
against a supertype should continue to satisfy its reasoning when it receives an
object of a subtype. Liskov and Wing describe this in terms of what clients can prove
about objects using the supertype's specification.

Suppose `RoutingPolicy` promises that `select(options)` accepts every nonempty list
of valid options and returns one member of that list. A subtype called
`StepFreePolicy` cannot reject every list that contains a non-step-free option. That
would strengthen the precondition: clients of `RoutingPolicy` were allowed to pass
such a list.

It also cannot manufacture a new approximate option that was not in the list. That
would weaken the postcondition. A client may rely on receiving one of the exact
offered values.

A conforming policy can filter internally and state a result that remains within the
original promise. If at least one option is step-free, it returns the best such
option; otherwise it returns the best available option. Alternatively, an interface
whose contract requires a step-free result should state that requirement and define
what happens when no such route exists. That is a different abstraction, not merely
an implementation variant.

Behavioural subtyping also preserves other observable properties:

- a subtype must not expose new checked failures where the supertype promises a
  normal result;
- it must preserve invariants that clients may rely on;
- it must respect stated mutation and aliasing effects; and
- it must not return a result weaker than the supertype's postcondition.

Methods may accept more inputs than the supertype requires, and they may return a
result that satisfies a stronger guarantee. Those changes do not invalidate existing
client reasoning.

Java's type checker verifies method signatures and access rules. It does not prove
these behavioural relationships. Specifications, tests, and review must address
them.

## 7. Common Misconception: Matching Fields Imply Equality

Two objects with matching displayed fields are not necessarily equal. A pair of open
sockets may show the same local and remote addresses while representing different
connections. Two timetable entries may display the same route and time while carrying
different service identifiers that affect cancellation updates.

The reverse mistake also occurs. Two objects need not have identical concrete fields
to represent the same abstract value. Chapter 6 showed that two adjacency maps with
different iteration orders can denote the same graph. An equality method for an
abstract graph should ignore representation order if clients cannot observe it.

Field comparison is an implementation technique. The abstraction decides which
comparisons mean equality.

## 8. Practice by Predicting Collection Behaviour

For each situation, predict the result before running code. Explain the prediction
using the relevant contract.

1. A class overrides `equals` using `tripId` but inherits `Object.hashCode`. One
   allocation is inserted into a `HashSet`; an equal allocation is passed to
   `contains`. State what the Java specifications guarantee and what they do not.
2. A record contains a mutable `ArrayList<String>` component. The list changes after
   the record becomes a `HashMap` key. Explain why the record syntax does not make
   this use safe.
3. A `TreeSet` orders `JourneyOption` values only by arrival. Two unequal options
   arrive at 08:30. Predict the result of adding both.
4. A subtype accepts fewer valid inputs than its supertype documents. Construct a
   client that is correct under the supertype contract and fails with the subtype.
5. A generated class includes a cache field in `equals` but omits it from
   `hashCode`. Does it violate the hash contract? Does that make the equality
   decision suitable for the abstraction?

Then inspect a generated value class from a code-generation tool. Identify the
fields used by `equals`, `hashCode`, and any ordering operation. Check those choices
against the class's specification rather than assuming that generated code selected
the intended abstraction.

## 9. Summary

- `==` compares references; `equals` expresses a type's value relation.
- `equals` must be reflexive, symmetric, transitive, consistent, and false for
  `null`.
- Equal objects must have equal hash codes. Unequal objects may collide.
- A hash key must not change in a way that affects equality while stored.
- Ordering equivalence can differ from `equals`, but sorted collections then behave
  differently from hash-based collections.
- A subtype must preserve the behavioural promises of its supertype. Compatible
  signatures alone do not establish substitutability.

## References

- Euclid. [*The Elements*, Book I, common notions](https://www.gutenberg.org/files/21076/21076-h/21076-h.htm).
- Oracle. [`Object` (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Object.html).
- Oracle. [`Map` (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Map.html).
- Oracle. [`Comparable` (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Comparable.html).
- Oracle. [`Record` (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Record.html).
- Barbara Liskov and Jeannette Wing. [“A Behavioral Notion of Subtyping”](https://www.cs.cmu.edu/~wing/publications/LiskovWing94.pdf), *ACM Transactions on Programming Languages and Systems*, 1994.
