# Chapter 9 | Recursion and Recursive Datatypes

> To see a World in a Grain of Sand
> And a Heaven in a Wild Flower
>
> <cite>William Blake, “Auguries of Innocence”</cite>

A journey can contain one travel leg followed by the rest of the journey. The rest
has exactly the same possibilities: it may contain another leg, or it may state that
the traveller has arrived. This description is finite, but one of its cases refers
back to the whole type.

Lists, directory trees, arithmetic expressions, and many protocol messages have the
same form. Their data has no fixed number of layers. A recursive datatype represents
the alternatives directly, and a recursive method follows the structure one case at
a time.

The method still needs a termination argument. A recursive call is not justified
merely because it eventually returned for the examples tried in a test. We must
identify a smaller subproblem and a base case that stops the descent.

By the end of this chapter, you should be able to:

- define a recursive datatype using records and a sealed interface;
- identify the base and recursive cases in a representation;
- implement structurally recursive observers;
- argue that a recursive method terminates and returns the specified result;
- distinguish object structure from call-stack state;
- recognise malformed or excessively deep recursive data; and
- choose an iterative implementation when recursion depth is not safely bounded.

## 1. A Recursive Journey Representation

Our model has two alternatives:

1. `Arrive(stop)` contains no further leg.
2. `Travel(route, from, to, minutes, rest)` contains one leg and another journey.

In Java 25, a sealed interface can list the permitted implementations:

```java
public sealed interface Journey permits Arrive, Travel { }

public record Arrive(String stop) implements Journey { }

public record Travel(String route, String from, String to,
                     int minutes, Journey rest) implements Journey {
    public Travel {
        if (minutes < 0) {
            throw new IllegalArgumentException("negative duration");
        }
        if (!to.equals(firstStop(rest))) {
            throw new IllegalArgumentException("disconnected journey");
        }
    }
}
```

`Journey` is a **recursive datatype** because the `Travel` case contains a `Journey`
component. The declaration does not create an infinite object. Each constructed
`Travel` refers to one already constructed, finite remainder. Construction ends at
an `Arrive` value.

The sealed declaration closes the set of direct implementations in this module. The
compiler can use that information when checking a pattern-matching `switch`. If a
later revision permits a third case, such as `Wait`, switches over `Journey` must
either handle it or retain a suitable default. That compiler check connects the data
definition to the operations that consume it.

The compact constructor enforces two local conditions. Durations are non-negative,
and the destination of a leg equals the first stop of its remainder. The second
condition makes disconnected chains unrepresentable through this constructor. A
production version would also reject null components and might use the `StopId` and
`RouteId` domain types introduced earlier.

> **Design principle:** For data defined by alternatives, make each alternative
> explicit and make recursive calls only on structurally smaller components.

## 2. Structurally Recursive Observers

The total duration mirrors the two cases:

```java
public static int totalMinutes(Journey journey) {
    return switch (journey) {
        case Arrive(String stop) -> 0;
        case Travel(String route, String from, String to,
                    int minutes, Journey rest) ->
                minutes + totalMinutes(rest);
    };
}
```

For `Arrive`, no travel remains, so the duration is zero. For `Travel`, the duration
is the current leg's minutes plus the duration of the remainder. The recursive call
receives `rest`, a proper component with one fewer `Travel` node than the original
value.

The switch is an expression, so both cases produce the returned `int`. It has no
`default` because `Journey` is sealed and the two permitted record patterns are
exhaustive. Several pattern variables do not affect this computation. Java still
checks their component types while matching the record pattern.

Leg count has the same structure:

```java
public static int legCount(Journey journey) {
    return switch (journey) {
        case Arrive(String stop) -> 0;
        case Travel(String route, String from, String to,
                    int minutes, Journey rest) -> 1 + legCount(rest);
    };
}
```

The similarity is not accidental. The datatype definition tells us what cases every
total observer must consider. It also identifies the recursive component available
in the `Travel` case.

The companion program constructed an R4 leg followed by a Canada Line leg and an
arrival. The validated Java 25 run printed:

```text
minutes=42, legs=2
```

The arithmetic followed the constructed values: `28 + 14 + 0` minutes and
`1 + 1 + 0` legs.

## 3. Termination

A useful termination argument identifies a non-negative measure that decreases on
every recursive call. For `totalMinutes`, let the measure be the number of `Travel`
nodes reachable from the argument.

- The `Arrive` case makes no recursive call.
- The `Travel` case calls `totalMinutes(rest)`, whose measure is one smaller.
- A finite journey cannot decrease this non-negative integer forever.

Therefore the method reaches `Arrive` and terminates for every finite valid journey.

A useful termination argument names the dimension that decreases and connects it to
a lower bound. A binary tree method may call itself
twice, once on each child; node count or height still decreases along every call
path. A numeric method that calls itself on `n / 2` needs a precondition that makes
the measure well founded. For negative integers, division and rounding may not follow
the intended argument.

Termination and correctness are separate obligations. A method that always returns
zero terminates but does not compute travel duration. A method that adds minutes
correctly but recurses on the original journey does not terminate.

## 4. Correctness by Structural Induction

Structural induction matches the datatype.

Claim: `totalMinutes(journey)` returns the sum of the duration of every `Travel` node
in a valid finite journey.

**Base case.** The journey is `Arrive`. It has no `Travel` nodes, the sum is zero, and
the method returns zero.

**Recursive case.** The journey is `Travel(route, from, to, minutes, rest)`. Assume
the method returns the correct sum for `rest`. The method adds the current node's
`minutes` to that sum. Those values are exactly the durations in the complete
journey, so the result is correct.

The assumption about `rest` is the induction hypothesis. It applies because `rest`
is structurally smaller. The proof does not depend on a particular journey length.

The same case analysis supports representation-invariant arguments. Suppose every
`Travel` constructor verifies that its `to` stop equals `firstStop(rest)`. The base
`Arrive` value is connected by definition. Adding a verified `Travel` in front of a
valid remainder preserves connectivity. Induction then establishes that the entire
constructed chain is connected.

Tests still matter. A proof concerns the method and specification as written; tests
can reveal a mistaken implementation, constructor path, or assumption. The two forms
of evidence address different risks.

## 5. Heap Structure and Call Frames

The journey nodes are objects on the heap. A call to `totalMinutes` does not copy the
whole remainder. Each invocation receives a reference to one node and creates a call
frame containing its parameter, pattern variables, and return location.

For the two-leg example, the active calls develop in this order:

```text
totalMinutes(first Travel)
  totalMinutes(second Travel)
    totalMinutes(Arrive)
```

`totalMinutes(Arrive)` returns zero. The second call adds 14 and returns 14. The first
adds 28 and returns 42. The object links exist independently of these temporary call
frames; another method could traverse the same immutable journey at the same time.

Java does not guarantee tail-call elimination. Even a recursive call in final
position may use another frame. A sufficiently deep valid structure can therefore
cause `StackOverflowError`. The Java language does not specify a portable maximum
recursion depth, and the available stack depends on runtime and implementation
conditions.

An implementation must therefore consider expected depth. A journey normally has a
modest number of legs. A syntax tree produced from untrusted nested input or a linked
structure with millions of nodes needs a different risk assessment.

The optional reading [How a Java Program Runs](chapter-12-how-java-runs.md) traces
frames, exception unwinding, and runtime observations in more detail.

## 6. Iterative Traversal for Unbounded Depth

A chain-shaped journey can be processed with a loop:

```java
public static int totalMinutesIterative(Journey journey) {
    int total = 0;
    Journey current = journey;
    while (current instanceof Travel travel) {
        total = Math.addExact(total, travel.minutes());
        current = travel.rest();
    }
    return total;
}
```

The loop keeps one current reference rather than one Java call frame per leg. It also
uses `Math.addExact` to turn integer overflow into `ArithmeticException`. The
recursive version could use the same checked addition.

For a branching tree, an iterative traversal usually needs an explicit stack or
queue. That data structure consumes memory too, but the program controls its
representation and may apply limits or use breadth-first order. Replacing recursion
with iteration does not remove the need for a termination argument. The loop must
advance to a smaller remainder, and its explicit worklist must eventually empty.

Choose between the forms using the data and operational constraints. A recursive
method often states the definition directly and supports a short correctness
argument. An iterative method avoids dependence on call-stack depth and can expose
the traversal order more explicitly.

### Immutable recursive values can share structure

Because a `Journey` does not change, two values can safely refer to the same
remainder. Suppose two alternative first legs both arrive at Oakridge and then use
the same Canada Line remainder. The program can allocate that remainder once and use
its reference in both `Travel` records.

This **structural sharing** does not merge the two abstract journeys. Each root still
defines its own complete sequence. It saves allocation and preserves old versions
when a producer adds a new prefix. A method that prepends one leg can run in constant
time because it creates one record and reuses the existing remainder.

Mutation would make this sharing observable in a more dangerous way. If one client
could change the shared remainder, both journeys would change. The immutable record
design permits sharing without an ownership negotiation between readers.

Recursive equality follows the same links. Generated record equality compares the
remainder by value, so structurally distinct allocations with equal sequences compare
equal. Hashing a long chain also traverses the remainder and may be costly; caching a
hash would introduce more representation state and require a new invariant.

## 7. Cycles in Recursive Representations

The `Journey` records are immutable and constructed from an existing remainder.
Ordinary construction cannot later redirect `rest` to form a cycle. Immutability
supports the finite-chain argument.

A mutable node type can create a different structure:

```text
first.rest = second
second.rest = first
```

A traversal that expects a finite chain will revisit the same objects forever or
until the call stack is exhausted. The type may still be recursively declared, but
its values now include cyclic graphs.

If cycles belong to the abstraction, the traversal needs a visited set or another
cycle-aware algorithm. If cycles do not belong, the representation should prevent
them or check for them at construction boundaries. A representation invariant such
as “following `rest` reaches an `Arrive` node without revisiting an object” is
meaningful, though a mutable implementation must also prevent later mutation from
invalidating it.

Object equality can complicate cycle detection. A visited set intended to detect
object revisits may need identity semantics rather than value equality. Two distinct
equal nodes are not necessarily a cycle, while returning to the same allocation is.
`IdentityHashMap` can support an identity-based set when that is the required
relation.

## 8. Structural and Numeric Recursion

Structural recursion follows a component of recursively defined data. The
termination measure usually comes from the construction: list length, tree height,
or node count.

Numeric recursion computes a new numeric argument, as factorial does with `n - 1`.
Its safety depends on an explicit precondition and arithmetic reasoning. Mutual
recursion distributes the recursive path across multiple methods, so the measure must
decrease across the combined call sequence.

Some algorithms recurse on a problem that is not stored recursively. Binary search
recurses on a smaller index interval. Merge sort recurses on smaller array regions.
The same obligations apply: define the base case, show that every recursive branch
makes progress, and combine sub-results according to the postcondition.

Memoisation changes the cost of repeated recursive subproblems but not the basic
correctness argument. It also introduces a cache whose equality, ownership, and
thread-safety properties must be designed. Techniques from Chapters 7, 8, and 13
then become part of the implementation.

## 9. Common Misconception: A Base Case Guarantees Termination

A method can contain a base case that its recursive calls never reach. Consider a
method intended to count down to zero but called with a negative number while each
step subtracts one. The base case `n == 0` exists, but the distance from zero grows.

A tree traversal can have a leaf case yet recurse repeatedly on the original root. A
graph traversal can reach nodes with no outgoing edges but loop inside a reachable
cycle. The presence of a conditional branch does not establish termination.

The required evidence is a progress argument for every recursive call under the
method's precondition. When no simple decreasing measure exists, termination may
need a visited set, a stronger precondition, or a different algorithm.

## 10. Practice by Tracing Structure and Calls

Perform each trace without running the code first.

1. Draw the three journey objects in the companion example and the references between
   them. Then list the active `totalMinutes` frames at maximum depth.
2. Add a `Wait(stop, minutes, rest)` case to the sealed hierarchy. State the changes
   required in `firstStop`, `totalMinutes`, and `legCount`. Decide whether waiting
   counts as a leg.
3. Specify and implement `lastStop(Journey)`. Give its termination and correctness
   arguments.
4. Change `Travel.minutes` to an arbitrary `int`. Construct an input for which plain
   addition overflows. Decide whether the datatype or observer should reject it.
5. Design an iterative traversal that returns the route names in encounter order.
   State the ownership of the returned list.
6. Consider a binary itinerary tree in which a traveller may choose either branch.
   Identify a measure that decreases along both recursive calls.

Review a recursive method produced by a code generator or assistant. Check all
cases against the datatype declaration, identify the exact measure used for
termination, and test the smallest value in every case. Reject an explanation that
only says the method “eventually reaches the base case.”

## 11. Summary

- A recursive datatype contains values of its own general type in at least one case.
- Sealed interfaces and records can make a closed set of cases explicit.
- Structural recursion handles each case and recurses on smaller components.
- A termination argument names a non-negative measure that decreases on every call.
- Structural induction proves results using the same base and recursive cases.
- Heap objects and recursive call frames are different runtime structures.
- Java does not guarantee tail-call elimination, so unbounded depth may require an
  iterative traversal or explicit worklist.

## References

- William Blake. [“Auguries of Innocence”](https://gutenberg.org/cache/epub/79363/pg79363-images.html).
- Oracle. [Sealed Classes and Interfaces](https://docs.oracle.com/en/java/javase/25/language/sealed-classes-interfaces.html), Java SE 25.
- Oracle. [Pattern Matching with `switch`](https://docs.oracle.com/en/java/javase/25/language/pattern-matching-switch.html), Java SE 25.
- Oracle. [Pattern Matching](https://docs.oracle.com/en/java/javase/25/language/pattern-matching.html), Java SE 25.
- Oracle. [Java Language Changes Summary](https://docs.oracle.com/en/java/javase/25/language/java-language-changes-summary.html), Java SE 25.
