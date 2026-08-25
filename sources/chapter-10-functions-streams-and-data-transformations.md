# Chapter 10 | Functions, Streams, and Data Transformations

> Into the same river we go down, and we do not go down.
>
> <cite>Heraclitus, as translated by W. T. Stace</cite>

A transit feed supplies arrival observations for several routes. Some observations
are incomplete. The reliability report needs the mean delay for each route using
only complete observations.

One implementation can build mutable temporary lists, fill them in several loops,
and update a collection of running totals. Another can state a sequence of data
transformations: retain complete observations, group them by route, and average each
group's delays. Java streams support the second form.

The stream form is not automatically clearer or faster. It works well when each
stage has a precise meaning and does not depend on hidden mutation. We need to
understand when stream operations run, what order they preserve, and what their
function arguments may safely do.

By the end of this chapter, you should be able to:

- treat a function value as an object with an input-output contract;
- distinguish intermediate from terminal stream operations;
- explain stream laziness and single-use consumption;
- build a transformation using `filter`, `map`, and `collect`;
- preserve non-interference and avoid stateful behavioural parameters;
- reason about encounter order and collector results;
- decide when a loop communicates the algorithm more directly; and
- review a stream pipeline for correctness before considering parallel execution.

## 1. The Reporting Transformation

Each input value records a route, a delay, and whether the observation is complete:

```java
public record ArrivalObservation(
        String route,
        int delayMinutes,
        boolean complete) { }
```

The report has the following contract:

```text
meanDelayByRoute(observations)

requires: observations and every element are non-null
effects: none
returns: for each route with at least one complete observation, the arithmetic mean
         of delayMinutes among its complete observations, in the order in which such
         routes first occur in observations
```

This specification settles several questions before implementation. Incomplete
observations do not count as zero-delay arrivals. Routes represented only by
incomplete data do not appear. The result has a defined iteration order. The method
does not change its input.

The implementation follows the same stages:

```java
public static Map<String, Double> meanDelayByRoute(
        List<ArrivalObservation> observations) {
    return observations.stream()
            .filter(ArrivalObservation::complete)
            .collect(Collectors.groupingBy(
                    ArrivalObservation::route,
                    LinkedHashMap::new,
                    Collectors.averagingInt(
                            ArrivalObservation::delayMinutes)));
}
```

The method reference `ArrivalObservation::complete` supplies the predicate used by
`filter`. The first argument to `groupingBy` obtains the route key. The map factory
selects `LinkedHashMap` so that first-occurrence order is retained. The downstream
collector averages delay values inside each group.

The companion input contained complete R4 delays of 3 and 5, a complete 99 delay of
8, and an incomplete 99 observation. The validated Java 25 run printed:

```text
{R4=4.0, 99=8.0}
```

The incomplete observation did not become a zero. The R4 key appeared first because
the first complete R4 observation preceded the first complete 99 observation.

> **Design principle:** Use a stream when the computation can be stated as a sequence
> of data transformations with independent, non-interfering stages.

## 2. Functions Are Values with Contracts

The package `java.util.function` contains interfaces for common function shapes. A
`Predicate<T>` accepts a `T` and returns a boolean. A `Function<T, R>` maps a `T` to
an `R`. A `Consumer<T>` accepts a `T` and returns no value. A `Supplier<T>` produces
a `T` without an argument.

A lambda expression creates an object implementing a compatible functional
interface:

```java
Predicate<ArrivalObservation> usable = observation -> observation.complete();
Function<ArrivalObservation, String> route = observation -> observation.route();
```

Method references give shorter names to these two existing operations:

```java
Predicate<ArrivalObservation> usable = ArrivalObservation::complete;
Function<ArrivalObservation, String> route = ArrivalObservation::route;
```

The shorter form is useful when the referenced method already expresses the stage.
A lambda is clearer when it combines operations or needs a meaningful parameter
name.

Functional interfaces are ordinary Java types. Their methods need specifications.
For a route classifier, the contract must state its null policy and whether it may
throw. For a function supplied to a reusable library, mutation and thread-safety
properties can affect every caller.

Lambdas may capture local variables only if those variables are final or effectively
final. This language rule prevents a lambda from observing later reassignment of the
local variable itself. It does not make the referenced object immutable:

```java
List<String> seen = new ArrayList<>();
Consumer<String> remember = value -> seen.add(value);
```

`seen` is effectively final as a reference, but the consumer mutates the list. The
ownership and concurrency issues from earlier chapters remain.

## 3. Intermediate Operations Are Lazy

Calling `stream()` creates a stream associated with a data source. Intermediate
operations such as `filter`, `map`, `sorted`, and `limit` describe another stream.
They do not normally traverse the source immediately. A terminal operation such as
`collect`, `count`, `reduce`, or `forEach` starts traversal.

Consider:

```java
Stream<ArrivalObservation> complete = observations.stream()
        .filter(observation -> {
            System.out.println("checked " + observation.route());
            return observation.complete();
        });
```

With no terminal operation, the Java Stream specification does not require the
predicate to run. Adding `complete.count()` consumes the stream and may evaluate the
predicate. A debugger may therefore not enter a lambda when the
pipeline is merely assembled.

Laziness also permits short-circuiting. `findFirst` can stop after locating one
matching element. `limit(10)` allows later stages to avoid processing the rest when
the pipeline and source permit it. The implementation may also elide a stage if it
can prove that the stage cannot affect the terminal result; side effects in behavioural
parameters can therefore be skipped in some pipelines.

A stream is single-use. After a terminal operation consumes it, a second operation
may throw `IllegalStateException`. Store the source collection or a
`Supplier<Stream<T>>` when the program needs independent traversals. A stream object
is a computation pipeline, not a reusable collection of results.

## 4. Non-Interfering Behavioural Parameters

The Stream specification requires most behavioural parameters to be
**non-interfering**: they must not modify the stream's data source while the pipeline
executes. It also expects most parameters to be **stateless**, so a result does not
depend on mutable state that changes during traversal.

The following design is unsafe:

```java
List<ArrivalObservation> observations = new ArrayList<>(source);
long count = observations.stream()
        .filter(observation -> {
            if (!observation.complete()) {
                observations.remove(observation);
            }
            return observation.complete();
        })
        .count();
```

The predicate changes the list being traversed. The program may throw
`ConcurrentModificationException`, skip values, or otherwise produce a result that
does not follow the intended filter. The correct pipeline leaves the source alone
and expresses removal as exclusion from the result.

External accumulation is another common error:

```java
List<String> routes = new ArrayList<>();
observations.stream()
        .filter(ArrivalObservation::complete)
        .forEach(observation -> routes.add(observation.route()));
```

This works in many sequential runs, but the mutation is unnecessary and becomes
unsafe under parallel execution. A collector states both the desired result and the
rules for combining partial results:

```java
List<String> routes = observations.stream()
        .filter(ArrivalObservation::complete)
        .map(ArrivalObservation::route)
        .toList();
```

`Stream.toList()` returns an unmodifiable list. Code that needs a mutable result
should request one explicitly, for example with
`Collectors.toCollection(ArrayList::new)`. The API choice should reflect the
ownership contract rather than an assumption about the concrete list class.

## 5. Stateless and Stateful Operations

An operation such as `filter` can decide about one element without seeing other
elements, assuming its predicate is stateless. `map` can transform one element in
the same way. These are stateless intermediate operations.

`sorted` must observe enough elements to determine their relative order. `distinct`
must remember values already encountered. These are stateful intermediate
operations. They may buffer substantial data and limit how efficiently a pipeline
can produce early results.

Stateful does not mean incorrect. Sorting journey options by arrival is a legitimate
operation. It means that cost and evaluation differ from a simple element-by-element
map. A pipeline that sorts a million elements before taking five may be much more
expensive than an algorithm that maintains the best five in a bounded data
structure.

The distinction also affects infinite streams. Mapping or filtering an infinite
generated stream can still produce values one at a time. Sorting the whole infinite
stream cannot complete. A terminating consumer such as `limit` must appear where
the operation order permits progress.

## 6. Encounter Order

Some stream sources have an **encounter order**. A `List` stream encounters elements
in list order. A stream from a collection with no defined iteration order may have no
stable encounter order.

Operations interact with that order. `findFirst` respects it; `findAny` permits any
element, which can support more freedom in a parallel pipeline. `forEachOrdered`
preserves encounter order, while `forEach` does not promise it for parallel streams.
Sorting imposes an order according to a comparator.

Collectors also make order decisions. The two-argument `groupingBy` does not promise
a particular `Map` implementation. Our report's contract requires first-occurrence
order, so the implementation supplies `LinkedHashMap::new`. If the specification did
not expose iteration order, selecting a particular map merely for one observed print
format would overspecify the result.

Ordering has a cost under parallel execution. Operations such as ordered `limit` may
need coordination to return the first elements rather than any elements. Removing
ordering with `unordered()` is valid only if the result contract does not distinguish
orders.

## 7. Absence and Reduction

Some terminal operations may have no result. `min`, `max`, `findFirst`, and
`reduce(BinaryOperator)` return `Optional` values because an empty stream supplies
no element.

Calling `get()` without establishing presence replaces the domain question with
`NoSuchElementException`. The caller should choose behaviour that matches its
contract:

```java
JourneyOption earliest = options.stream()
        .min(Comparator.comparing(JourneyOption::arrival))
        .orElseThrow(() -> new IllegalArgumentException("no journey options"));
```

A reduction with an identity can return a plain value. Summing an empty stream of
durations produces zero because zero is the additive identity. The identity must be
neutral, and the accumulator and combiner must satisfy the reduction contract if the
pipeline may run in parallel.

Floating-point reduction deserves additional care. Addition is not associative in
finite-precision arithmetic, so regrouping operations can change the last bits of a
result. A parallel average may be mathematically equivalent without being bit-for-bit
identical to one sequential order. A specification for numerical software must say
which tolerance or reproducibility requirement applies.

The primitive specialisations `IntStream`, `LongStream`, and `DoubleStream` avoid
boxing every numeric element. Calling `mapToInt(ArrivalObservation::delayMinutes)`
produces an `IntStream` whose `sum`, `average`, and summary operations state the
numeric computation directly. Its `average` returns `OptionalDouble` because an
empty stream has no arithmetic mean. Choosing the primitive form can reduce
allocation, but the same questions about emptiness, overflow, floating-point order,
and measurement remain.

### Several outputs from one input with `flatMap`

`map` produces exactly one result for each input element. A route may instead contain
several stops. Mapping routes to stop lists produces a stream of lists:

```java
Stream<List<String>> stopLists = routes.stream().map(Route::stops);
```

If the next operation needs individual stop identifiers, `flatMap` maps each route to
a stream and concatenates those streams:

```java
List<String> stops = routes.stream()
        .flatMap(route -> route.stops().stream())
        .distinct()
        .toList();
```

The result preserves encounter order for an ordered source: it processes each route
in order and each route's stops in order before `distinct` retains the first
occurrence. This pipeline describes flattening and deduplication directly.

`flatMap` is also useful for optional results. A parser can return
`Optional<Prediction>` and a pipeline can flatten present values with
`Optional::stream`. Flattening is suitable when absence is an ordinary result. It is
not suitable when a malformed record must be reported, because flattening an empty
optional would silently discard the failure evidence.

### Null in the pipeline contract

Most stream operations can technically encounter null references, but method
references and comparators often reject them later with an uninformative
`NullPointerException`. A collection boundary should either reject null explicitly or
define its meaning. Our report requires every observation to be non-null.

Filtering with `Objects::nonNull` can be correct when null means “missing
observation” by specification. Adding that filter merely to prevent an exception
changes invalid input into silently omitted data. The specification must make that
policy visible.

## 8. Loops for Control-Flow-Oriented Algorithms

A stream is not a replacement for every loop. A parser that advances through tokens,
reports a precise error location, and changes state according to a grammar may be
clearer as explicit control flow. A search with several early exits and resource
operations may also read more directly as a loop or dedicated algorithm.

Long pipelines can hide intermediate types and duplicate computation. Naming a
helper function or materialising a well-defined intermediate value may improve both
the specification and diagnostics. The implementation should make the transformation
and its assumptions visible.

Performance requires measurement in the relevant workload. Streams add abstraction
and may enable library optimisations, but allocation, boxing, data layout, and
pipeline shape matter. A loop over primitive arrays can be more efficient. A stream
can be clearer enough to justify a modest cost. Benchmark evidence, not syntax,
settles the local decision.

## 9. Common Misconception: `parallel()` Makes a Pipeline Faster

Calling `parallel()` requests a parallel execution mode. It does not guarantee lower
latency. Splitting work, scheduling tasks, combining results, maintaining encounter
order, and sharing memory all add costs. Small or cheap operations often become
slower.

Correctness comes before performance. Stateful lambdas and external mutable
accumulators that appeared to work sequentially may race in parallel. Collectors
must have valid combination behaviour. Blocking input/output operations may occupy
workers in a pool whose design is unsuitable for that workload.

Chapter 12 separates concurrency from parallelism and introduces virtual threads for
blocking tasks. The choice of a parallel stream or executor follows the computation
and measurement; it is not a finishing switch applied to an arbitrary pipeline.

## 10. Practice by Explaining a Pipeline

For each exercise, state the source, intermediate stages, terminal operation, result
order, and mutation effects.

1. Produce the identifiers of routes whose mean delay exceeds five minutes, sorted
   alphabetically. Decide whether a route with only incomplete observations appears.
2. Predict which diagnostic messages can print before and after adding `findFirst`
   to a pipeline with a printing predicate.
3. Replace an external mutable list used by `forEach` with a collector. State whether
   the returned list is mutable.
4. Compare `findFirst` and `findAny` on an ordered parallel stream. Identify which
   client postcondition permits each choice.
5. Review a generated pipeline that uses `peek` to update a counter. Explain why the
   counter may not record every source element and redesign the measurement.
6. Write a loop equivalent to `meanDelayByRoute`. Compare the two versions by their
   stated invariants and intermediate state, not by line count.

Before changing a working sequential pipeline to parallel, identify the cost per
element, dataset size, ordering requirement, collector behaviour, and all shared
mutable state. Form a measurable performance claim and retain the sequential version
as a correctness reference.

## 11. Summary

- Functional interfaces give lambdas and method references explicit Java types and
  contracts.
- Intermediate stream operations are lazy; a terminal operation consumes the
  single-use pipeline.
- Behavioural parameters should not modify the source and should normally be
  stateless.
- Stateful operations such as sorting and deduplication may buffer data and affect
  termination or parallel cost.
- Encounter order comes from the source and operations; collectors must preserve it
  only when the result contract requires it.
- Streams communicate data transformations well. Explicit loops remain appropriate
  when control flow and mutable algorithm state are central.
- Parallel execution needs a correctness argument and measurements.

## References

- W. T. Stace. [*A Critical History of Greek Philosophy*, Chapter III](https://www.gutenberg.org/cache/epub/33411/pg33411-images.html).
- Oracle. [`java.util.function` Package Summary (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/function/package-summary.html).
- Oracle. [`java.util.stream` Package Summary (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/package-summary.html).
- Oracle. [`Stream` (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Stream.html).
- Oracle. [`Collectors` (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Collectors.html).
