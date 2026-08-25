# Chapter 8 | Composition, Delegation, and API Design

> All are but parts of one stupendous whole.
>
> <cite>Alexander Pope, *An Essay on Man*</cite>

The journey planner already has a router. A new requirement asks it to count
completed requests for operational monitoring. Another asks it to cache repeated
requests. A third asks it to record how long route computation takes.

None of these requirements changes what routing means. Each adds behaviour around a
routing operation. Extending the concrete router class for every combination soon
produces `CachedAuditedRouter`, `TimedCachedRouter`, and several other classes whose
names reveal that the design is combining independent concerns through inheritance.

The client needs a route. It should not need to know which concrete algorithm,
monitor, or cache supplied it. We can state a small interface around that client need
and assemble implementations by composition.

By the end of this chapter, you should be able to:

- distinguish inheritance from composition and delegation;
- design an interface around a stable client responsibility;
- use a wrapper to add behaviour while preserving a contract;
- identify implementation coupling caused by inheritance;
- decide where validation and failure translation belong in a composed system;
- recognise an interface that is too broad or too dependent on representation; and
- test a component independently by replacing its collaborators.

## 1. The Client-Facing Route API

A trip-planning client submits a request and receives a route. The interface can say
exactly that:

```java
public interface Router {
    Route route(RouteRequest request);
}
```

This interface is small because its purpose is narrow. It does not expose the graph,
the priority queue used by a shortest-path algorithm, cache controls, or counters.
Those details may matter to particular implementations, but a client that requests a
route has no reason to depend on them.

The request and result types carry the values shared across the boundary:

```java
public record RouteRequest(
        String origin,
        String destination,
        boolean stepFreeRequired) { }

public record Route(List<String> stops, boolean stepFree) {
    public Route {
        stops = List.copyOf(stops);
    }
}
```

`Route` takes a snapshot of the stop list. A client therefore receives a value whose
contents cannot change through an alias to the constructor argument. This ownership
decision is part of the application programming interface (API), just as the method
signature is.

An interface does not have to be minimal in character count. It should contain the
operations that form one coherent client role. If route computation also supports
explicit cancellation, the interface may need a cancellation abstraction. If only
an administrator clears caches, cache management belongs in a separate interface
used by that administrator.

> **Design principle:** Put a stable responsibility behind an interface, and
> compose implementations whose contracts match that responsibility.

## 2. Composition and Delegation

An object uses **composition** when it contains references to other objects and uses
them to perform its work. The composed object has a collaborator rather than being a
specialised version of that collaborator.

An audited router contains another router:

```java
public static final class AuditedRouter implements Router {
    private final Router delegate;
    private int completedRequests;

    public AuditedRouter(Router delegate) {
        this.delegate = Objects.requireNonNull(delegate);
    }

    @Override
    public Route route(RouteRequest request) {
        Route result = delegate.route(request);
        completedRequests++;
        return result;
    }

    public int completedRequests() {
        return completedRequests;
    }
}
```

The field has the interface type `Router`. The wrapper can therefore use a direct
router, a timetable router, a test implementation, or another wrapper. It depends on
the routing contract rather than a particular algorithm.

The call to `delegate.route(request)` is **delegation**: the wrapper forwards work to
its collaborator. Composition describes the object structure; delegation describes
the forwarding action. They often occur together but are not synonyms. A composed
object may use a collaborator without exposing the same operation, and a method can
delegate to an object obtained from elsewhere rather than one stored in a field.

The validated companion program placed `DirectRouter` inside `AuditedRouter`, made
one request, and printed:

```text
[UBC, WATERFRONT], audited=1
```

The wrapper returned the route produced by its delegate and updated its own state
after the delegate completed normally.

## 3. Observable Audit Events

The audit example contains a specification decision that the code alone cannot
settle. It increments the counter only after `delegate.route` returns. A request that
throws is not counted as completed.

Other useful measures include attempted requests, successful requests, failed
requests, and requests cancelled by a client. One integer cannot represent all four.
The monitoring requirement must define the event being counted, then the wrapper can
place updates at the corresponding control-flow points.

For attempted requests, increment before delegation. For separate success and
failure counts, use a `try` statement:

```java
attempted.increment();
try {
    Route result = delegate.route(request);
    succeeded.increment();
    return result;
} catch (RuntimeException failure) {
    failed.increment();
    throw failure;
}
```

The wrapper rethrows the same failure because the `Router` contract has not granted
it permission to replace routing failures with an unrelated result. If the public API
defines a domain exception, an adapter at the relevant boundary may translate a
lower-level exception into that type while retaining the cause.

The plain `int` in the first example is suitable only when calls are confined to one
thread. If multiple threads share the wrapper, `completedRequests++` is not an atomic
operation. Chapter 13 develops the thread-safety argument and appropriate counters.
The API should either promise thread safety and implement it, or document that the
object requires confinement or external synchronisation.

## 4. Wrapper Composition and Order

A cache wrapper can implement the same interface:

```java
public final class CachingRouter implements Router {
    private final Router delegate;
    private final Map<RouteRequest, Route> cache = new HashMap<>();

    public CachingRouter(Router delegate) {
        this.delegate = Objects.requireNonNull(delegate);
    }

    @Override
    public Route route(RouteRequest request) {
        return cache.computeIfAbsent(request, delegate::route);
    }
}
```

This code assumes that `RouteRequest` is an immutable value with suitable equality,
as Chapter 7 required. It also assumes that caching is semantically valid. If the
underlying timetable changes, an indefinitely cached result may violate the router's
freshness contract. A real cache needs a policy for versioning, expiration, or
invalidation.

Wrappers can be nested:

```java
Router router = new AuditedRouter(
        new CachingRouter(
                new TimetableRouter(network, timetable)));
```

The order is observable. In this arrangement, the auditor sees every client request,
including cache hits. If the cache surrounds the auditor, only cache misses reach the
auditor. Neither order is inherently correct. The monitoring specification decides
which event the system needs to measure.

The same analysis applies to timing. A timer outside the cache measures client
latency, while a timer inside measures route computation on misses. Composition makes
the choice visible at assembly time.

Changing wrapper order can change behaviour. Authentication before caching may
prevent an
unauthorised request from observing cached data. Caching before authentication could
be a security defect. An architectural diagram may show the sequence, but the
contracts determine which sequences are valid.

## 5. Composition and Inheritance

Java class inheritance establishes an `is-a` relationship and permits a subclass to
reuse or override accessible implementation. This mechanism is appropriate when the
subclass is a behavioural subtype and the superclass was designed for extension.

Using inheritance only to obtain code reuse creates stronger coupling. A subclass
can depend on protected methods, call order, self-use, and other details that do not
appear in the public contract. A superclass update can then change subclass
behaviour without changing any public signature.

Suppose a router superclass implements `routeAll` by repeatedly calling its public
`route` method. An auditing subclass overrides `route` to increment a counter. One
call to `routeAll` then increments once per element. A later superclass version
optimises `routeAll` to call a private batch algorithm. The subclass still compiles,
but the count changes. The subclass depended on whether one superclass method called
another overrideable method.

A wrapper has a clearer boundary. It sees the calls that clients make through the
wrapper's interface. It cannot depend on private control flow inside its delegate.
The delegate may change its algorithm while preserving the `Router` contract.

Composition has costs. A wrapper must forward every operation it promises. When a
large interface gains a method, each wrapper needs a deliberate implementation.
Object assembly also requires a place that chooses and connects collaborators. These
costs are useful feedback: repeated forwarding can reveal an interface that serves
too many client roles.

Inheritance remains useful for frameworks with documented extension points and for
true taxonomies whose behavioural contracts hold. The decision should follow the
relationship. “Needs the services of” suggests composition. “Can replace every use
of” is a necessary condition for public subtyping.

## 6. Validation and Failure Boundaries

Each component should validate the conditions its own contract assigns to it. A
`RouteRequest` constructor can reject null stops because no valid request contains
them. A router can reject an unknown stop because only the network can answer whether
a syntactically valid identifier belongs to it. A protocol adapter can reject an
invalid response because it owns the external format boundary.

Duplicating every check in every wrapper adds code without necessarily adding
protection. Omitting checks at trust boundaries allows invalid state to travel into
components that cannot diagnose its source. The specification should identify where
an assumption first becomes available and where untrusted data becomes a domain
value.

Failure translation follows the same rule. A file-backed timetable may throw an
`IOException`; a routing API may promise `TimetableUnavailableException`. The
adapter that knows both abstractions can translate the exception and preserve the
cause. An auditing wrapper should not translate it merely because the call passed
through that wrapper.

Resource ownership also belongs at a boundary. If a component opens a file, socket,
or executor for one operation, it should normally close that resource. If assembly
provides a long-lived resource, the owning application should define its lifetime.
An interface that accepts a collaborator does not imply ownership of that
collaborator.

### Construction policy outside the components

The place that creates the object graph decides which concrete router and wrappers
the application uses. A command-line program may assemble a file-backed timetable,
a cache with a fixed clock, and an auditor. A test can assemble an in-memory router
and a recording monitor. None of the components needs to read a global configuration
or construct its own replacement.

Constructor injection makes required collaborators visible and prevents an object
from being used before assembly is complete. Optional behaviour should still have a
clear representation. Passing `null` for “no auditor” spreads conditional checks;
using a no-operation implementation or constructing the unwrapped router keeps the
normal call path explicit.

Assembly also owns startup failure. If constructing the timetable requires a file
that is absent, the program can stop before accepting requests. Delaying the same
failure until the first route call changes the operational contract and may expose a
partially available service. Both policies can be valid, but the application entry
point should choose deliberately.

### Default methods are part of the contract

Java interfaces may provide `default` method implementations. A default can evolve
an interface or express an operation in terms of more fundamental ones. It is not a
free compatibility guarantee. Existing implementations may have performance,
atomicity, or failure properties that the default does not preserve.

If `Router` gained `routeAll` as a loop over `route`, a remote implementation would
make one network round trip per request. A batch-capable server could provide a
different atomicity and latency profile. The interface must specify those properties
before clients can substitute either implementation confidently.

## 7. Component Substitution in Tests

Composition allows a test to replace one collaborator without constructing the
whole transit system. An in-memory test router can record its input and return a
fixed route:

```java
final class RecordingRouter implements Router {
    RouteRequest received;

    @Override
    public Route route(RouteRequest request) {
        received = request;
        return new Route(List.of("UBC", "WATERFRONT"), true);
    }
}
```

A test of `AuditedRouter` can then check three separate facts: it forwarded the same
request, returned the delegate's result, and changed the counter according to its
specification. The test does not need a graph search or timetable file.

This replacement is useful because the interface represents a genuine boundary. An
interface introduced solely so every class can be mocked may scatter abstractions
that have no stable meaning. Small concrete value objects such as `RouteRequest`
usually need ordinary construction, not replacement.

Tests should also cover wrapper order when order matters. A cache-and-audit
integration test can issue the same request twice and state whether the expected
count is one route computation or two client calls. That test records an architectural
decision which a unit test of either wrapper alone cannot see.

## 8. Common Misconception: An Interface Removes Coupling

Changing a field type from a class to an interface does not by itself produce a
decoupled design. Components remain coupled to every promise and data type in that
interface.

An interface such as `TransitSystemService` with methods for routing, cache clearing,
health checks, timetable replacement, metrics, and raw graph access couples every
implementation and client to a broad administrative surface. Most clients use only a
small part, yet changes affect all implementers.

Likewise, an interface that returns an implementation-specific `HashMap` exposes a
representation choice despite the interface declaration. Returning `Map` is better,
but even that may expose more operations than a client needs. A domain result type can
state ordering, immutability, and absence more precisely.

Interfaces move dependencies onto contracts. Good API design makes those contracts
coherent and no larger than the client role requires.

## 9. Practice by Reviewing a Composition

For each design, identify the contract at the boundary and explain whether the
composition preserves it.

1. `FallbackRouter` calls its secondary router whenever the primary returns an empty
   route. The `Router` contract says an empty route means origin equals destination.
   Determine whether the wrapper confuses a valid result with failure.
2. `RetryingRouter` repeats every failed call three times. Some failures report an
   invalid request, while others report a temporarily unavailable timetable. Decide
   which failures may justify retry and where that policy belongs.
3. `CachingRouter` accepts mutable `RouteRequest` keys. Trace a lookup after a caller
   changes a key.
4. `AuditedRouter` is shared between request threads and uses `int++`. State the
   additional thread-safety contract or confinement rule needed.
5. A subclass overrides `route` to remove inaccessible options even though the
   superclass promises to return the fastest route. Apply behavioural subtyping from
   Chapter 7.

Design a `TimingRouter` that records elapsed time without changing the result or
failure promised by its delegate. State whether it measures failed calls, which
clock abstraction it accepts, and who owns the measurements. Then describe a test
that does not depend on the computer's wall clock.

## 10. Summary

- Composition gives an object collaborators; delegation forwards an operation to a
  collaborator.
- An interface should describe a coherent client responsibility rather than expose
  an implementation's controls and representation.
- A wrapper can add auditing, caching, timing, validation, or translation while
  preserving the wrapped contract.
- Wrapper order can change observable behaviour and must follow the specification.
- Inheritance is suitable only when the subclass remains a behavioural subtype and
  the superclass supports extension.
- Component boundaries make focused testing possible, but interfaces still create
  coupling to their contracts.

## References

- Alexander Pope. [*An Essay on Man*](https://www.gutenberg.org/files/9413/9413-h/9413-h.htm).
- Joshua Bloch. *Effective Java*, 3rd ed., Item 18, “Favor composition over
  inheritance.” Addison-Wesley, 2018.
- Erich Gamma, Richard Helm, Ralph Johnson, and John Vlissides. *Design Patterns:
  Elements of Reusable Object-Oriented Software*, “Decorator.” Addison-Wesley, 1994.
- Oracle. [Java Language Specification, Java SE 25, Chapter 9: Interfaces](https://docs.oracle.com/javase/specs/jls/se25/html/jls-9.html).
