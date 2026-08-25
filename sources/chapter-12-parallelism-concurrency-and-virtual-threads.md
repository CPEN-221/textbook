# Chapter 12 | Parallelism, Concurrency, and Virtual Threads

> They also serve who only stand and wait.
>
> <cite>John Milton, “On His Blindness”</cite>

A journey request needs predictions from three transit services. A sequential client
sends the first request and waits, then sends the second and waits, then sends the
third. Each server may respond quickly, but the waiting times accumulate.

The three requests are independent. The client can start all of them before waiting
for their results. This is a concurrency problem: several tasks can be in progress
during overlapping periods. If the work is mainly waiting for network input, virtual
threads let us retain direct blocking code while supporting many concurrent tasks.

Concurrency also introduces new failure paths. One task may fail while the others
run. A caller may abandon the whole journey request. The program must decide which
task owns each result, how cancellation propagates, and which resources limit the
amount of work admitted.

By the end of this chapter, you should be able to:

- distinguish concurrency from parallelism;
- distinguish a task from the thread that executes it;
- explain the intended workload for Java virtual threads;
- submit independent blocking tasks to a virtual-thread-per-task executor;
- retrieve results and preserve interruption status;
- specify failure, cancellation, and lifetime for a group of tasks;
- limit access to a scarce external resource without pooling virtual threads; and
- identify Java 25 structured concurrency as an optional preview API.

## 1. Tasks, Concurrency, and Parallelism

A **task** is a unit of work with a result or effect. Fetching one prediction is a
task. A **thread** is an execution mechanism that can run instructions belonging to a
task.

Two tasks are **concurrent** when their lifetimes overlap. While one network request
waits for data, another can make progress. Concurrency is about the structure and
coordination of multiple tasks.

Two tasks run **in parallel** when processors execute their instructions at the same
instant. Parallelism can reduce the time needed for CPU-intensive independent work
when enough processing capacity is available.

A concurrent program may run on one processor by interleaving tasks. A parallel
calculation is also concurrent because its tasks overlap, but its purpose and cost
model differ. Fetching from three services benefits mainly from overlapping wait.
Multiplying large matrices benefits from distributing computation across cores.

These distinctions guide the implementation. Creating many threads does not create
more processors. A thousand CPU-bound tasks still compete for the available cores.
A thousand mostly waiting network tasks may benefit from a lightweight way to retain
their individual control flow.

> **Design principle:** Give each concurrent task a clear result, owner, lifetime,
> and cancellation policy. Choose the execution mechanism from the kind of work the
> task performs.

## 2. Platform and Virtual Threads

Traditional Java **platform threads** are implemented as thin wrappers around
operating-system threads. They are suitable for many workloads, but operating-system
threads are comparatively scarce. A server that assigns one platform thread to each
of a very large number of mostly waiting requests can exhaust memory or scheduling
capacity.

A **virtual thread** is a Java `Thread` scheduled by the Java runtime rather than
being permanently tied to one operating-system thread. When a virtual thread blocks
in many supported input/output operations, the runtime can suspend it and use the
underlying platform thread for other work. The virtual thread retains the familiar
sequential call structure.

Virtual threads became a final feature in Java 21 and remain available in Java 25.
They are intended to improve the scale and throughput of thread-per-request code
that spends substantial time waiting. They do not make code within a thread execute
faster, and they do not reduce the latency of one isolated operation by themselves.

Virtual threads should not be pooled. Each task can receive a new virtual thread. If
the application must limit concurrent access to a database that permits twenty
connections, the limit belongs to the database resource, for example through its
connection pool or a semaphore. Reducing a pool of virtual threads conflates task
representation with resource admission.

Platform threads remain appropriate for CPU-bound work when an executor sized near
the available processor count controls parallelism. Measurement and the workload
determine the configuration.

## 3. One Virtual Thread per Independent Request

`Executors.newVirtualThreadPerTaskExecutor()` returns an executor that starts a new
virtual thread for each submitted task. The companion example accepts a list of
`Callable<Integer>` prediction requests:

```java
public static List<Integer> fetchAll(List<Callable<Integer>> requests)
        throws InterruptedException {
    try (ExecutorService executor =
                 Executors.newVirtualThreadPerTaskExecutor()) {
        List<Future<Integer>> futures = executor.invokeAll(requests);
        return futures.stream().map(VirtualThreadsDemo::get).toList();
    }
}
```

`invokeAll` submits the tasks and waits until all complete. Its returned future list
has the same order as the input task list. Completion may occur in a different order,
but the result construction above preserves request order.

The executor is a resource with a lifetime. The try-with-resources statement closes
it after the method completes or fails. Closing waits for submitted tasks to finish.
A long-lived server may instead own one executor for its service lifetime, but the
owner and shutdown path should remain explicit.

The example tasks return fixed values so validation remains deterministic:

```java
List<Integer> predictions = fetchAll(List.of(
        () -> 7,
        () -> 4,
        () -> 11));
```

The validated Java 25 run printed:

```text
predictions=[7, 4, 11]
```

This output confirms result order. It does not reveal which task completed first and
does not measure a speed improvement. A performance claim would need tasks with
representative blocking behaviour and a controlled comparison.

## 4. Results and Failure Information

Submitting a `Callable<T>` produces a `Future<T>`. A successful `get` returns the
task's value. If the task threw, `get` throws `ExecutionException` whose cause is the
task failure. If the waiting thread is interrupted, `get` throws
`InterruptedException`.

The companion helper translates the first two failure categories for its internal
stream operation:

```java
private static int get(Future<Integer> future) {
    try {
        return future.get();
    } catch (InterruptedException error) {
        Thread.currentThread().interrupt();
        throw new IllegalStateException("interrupted", error);
    } catch (ExecutionException error) {
        throw new IllegalStateException(
                "request failed", error.getCause());
    }
}
```

Restoring the interrupt status matters. Throwing another unchecked exception without
calling `interrupt()` would consume the signal, and code farther up could no longer
observe that cancellation was requested.

This particular method calls `invokeAll` first, so all returned futures are complete
before the stream reads them. `invokeAll` itself remains interruptible and declares
`InterruptedException`. The helper still illustrates the general obligation for a
method that catches interruption and cannot rethrow it directly.

Translating every task failure to `IllegalStateException` is not a complete public
API design. A journey service may need to distinguish an unknown stop, a timed-out
provider, and an invalid remote response. The orchestration layer should preserve the
causes required by its contract and cancel work that no longer contributes to a
result.

## 5. Group Failure and Cancellation

Suppose the first provider returns a usable prediction, the second throws, and the
third remains blocked. Several policies are possible:

- fail the journey request when any required provider fails;
- return partial results with the unavailable provider identified;
- take the first valid result and cancel the remaining alternatives; or
- wait until a deadline and return all results obtained by then.

The task structure does not choose among them. The service specification must state
which providers are required and what a partial answer means.

Cancellation is cooperative. `Future.cancel(true)` requests interruption if the task
is running. The task must respond to interruption or call blocking operations that
do. Code that catches `InterruptedException` and continues its original work defeats
the cancellation policy.

A group also needs a bound on lifetime. Per-socket read timeouts help, but the caller
may have a shorter total deadline. A journey request abandoned by its client should
not leave remote calls running indefinitely. Ownership gives the rule: the component
that creates a group of tasks is normally responsible for joining or cancelling all
members before the group leaves its scope.

Unstructured use of `Thread.startVirtualThread` can make that responsibility hard to
see. Starting a thread and discarding its reference separates the task from the
caller that needs its result. An executor and retained futures give explicit handles,
though the program must still implement group policy.

## 6. Limits on Scarce Resources

A virtual thread is inexpensive relative to a platform thread, but the operation it
performs may consume scarce resources. A remote service may allow fifty concurrent
requests. A database may expose twenty connections. Memory may limit the number of
large response bodies being decoded.

A semaphore can state a request limit:

```java
private final Semaphore providerPermits = new Semaphore(50);

Prediction fetch(StopId stop) throws InterruptedException {
    providerPermits.acquire();
    try {
        return provider.fetch(stop);
    } finally {
        providerPermits.release();
    }
}
```

Every successful acquisition has a `finally`-protected release. Waiting for a permit
is interruptible, so cancellation can prevent a task that has not reached the remote
service from continuing.

The limit is part of system capacity planning. If requests arrive faster than the
limited resource can serve them, tasks queue and latency grows. The service may also
need admission control, a bounded request queue, or rejection before work consumes
too much memory. Virtual threads allow many blocked tasks; they do not make an
unbounded backlog safe.

Rate limits and concurrency limits differ. A semaphore caps simultaneous operations.
A provider that permits one hundred requests per second needs a time-based rate
policy even if only a few requests are in flight at once.

## 7. State Shared between Tasks

Independent tasks are easiest to reason about when they receive immutable inputs and
return values. The caller combines those values after completion. The `fetchAll`
example follows this form: each callable returns one integer, and the caller builds
an unmodifiable result list.

If tasks instead append to a shared `ArrayList`, updates may race and corrupt the
result. Replacing the list with a concurrent collection prevents some representation
failures, but it does not automatically define result order, duplicate handling, or
group completion.

Thread confinement is often simpler. Let each task parse its response into a new
immutable `Prediction`, return it, and let one owner assemble the journey result.
Shared caches and counters may still be useful, but their thread-safety contracts need
separate analysis in Chapter 13.

Thread-local variables deserve caution with virtual threads. A virtual-thread-per-task
design can create very many threads, so large thread-local values multiply memory
use. Values that represent request context should have a deliberate lifetime and
should not become an undeclared channel between components.

## 8. Concurrency and Parallel Streams

A parallel stream divides a data pipeline into tasks executed by a parallel
implementation, commonly using the shared fork-join pool. It can fit CPU-oriented
bulk operations whose behavioural parameters and reductions meet the stream
contracts.

A virtual-thread-per-task executor fits many independent tasks that block, such as
network calls using direct synchronous code. Replacing those calls with
`parallelStream()` gives less explicit control over executor ownership, blocking, and
failure policy. Conversely, creating one virtual thread for every element of a
fine-grained CPU calculation does not increase the number of cores.

Both mechanisms can be used correctly, but they answer different design questions.
Chapter 10's stream abstraction describes a data transformation. An executor
describes task submission and lifetime. The program should not select one merely
because it uses fewer lines.

## 9. Structured Concurrency as an Optional Preview

Java 25 includes a fifth preview of structured concurrency in JEP 505. Its API groups
related subtasks in a lexical scope so that their lifetimes, failure handling, and
observability can be managed as a unit. The model fits the ownership rule used in
this chapter: child tasks should not outlive the operation that created them.

The feature remains a preview in Java 25. Code that uses it must be compiled and run
with preview features enabled, and its API may change or disappear in a later
release. These core readings therefore use final `ExecutorService` and `Future` APIs.

Students may explore structured concurrency as an optional extension. Such an
experiment should record the exact JDK, the `--enable-preview` flags used for both
compilation and execution, and the policy chosen for success and failure. Production
code should not acquire an accidental preview dependency through a copied example.

## 10. Common Misconception: Virtual Threads Make Work Faster

Virtual threads improve the feasibility of representing many concurrent tasks with
straightforward blocking code. They do not make a remote server respond sooner, add
processor cores, or reduce the work in a calculation.

Three independent 200-millisecond waits can overlap so that their combined elapsed
time approaches the slowest wait rather than their sum. One 200-millisecond wait is
still a 200-millisecond wait. Three CPU computations that each fully occupy a core
need available cores to run in parallel; adding virtual threads beyond that capacity
adds scheduling rather than computation.

The relevant measurements are throughput, latency distribution, memory use, and
resource saturation under a representative load. A single elapsed-time print from a
development laptop cannot establish system capacity.

## 11. Practice by Defining Task Lifetimes

For each situation, name the tasks, owner, success condition, failure policy,
cancellation signal, and scarce resource.

1. Three providers are all required for a fare comparison. One fails immediately.
   State what happens to the other two tasks.
2. The planner needs the first accessible journey from either of two providers.
   Explain when the losing task is cancelled and how its socket closes.
3. Ten thousand requests call a provider that permits fifty concurrent connections.
   Place a semaphore and explain why a pool of fifty virtual threads states a
   different limit.
4. A task catches `InterruptedException`, logs it, and continues retrying. Explain
   how this conflicts with its owner's cancellation policy.
5. A generated solution uses `parallelStream()` for blocking HTTP calls. Review its
   executor ownership, exception handling, and dependence on the common pool.
6. A CPU-bound route scoring function runs for each candidate. Design a measurement
   comparing sequential execution, a bounded platform-thread executor, and virtual
   threads.

Modify the companion example so that one callable throws. Preserve its original
cause in the result or declared failure, and ensure every submitted task has
terminated or received cancellation before `fetchAll` returns.

## 12. Summary

- Concurrency overlaps task lifetimes; parallelism executes work simultaneously.
- A task is a unit of work, while a thread is one mechanism that executes it.
- Virtual threads support high-throughput workloads with many blocking tasks. They
  do not make individual operations or CPU-bound work inherently faster.
- A virtual-thread-per-task executor keeps task submission and handles explicit.
- Interruption and task failures must retain the information required by the caller's
  contract.
- Related tasks need a group success rule, deadline, and cancellation policy.
- Limit access to scarce resources directly rather than pooling virtual threads.
- Structured concurrency remains an optional preview feature in Java 25.

## References

- John Milton. [“On His Blindness,” *The Poetical Works of John Milton*](https://www.gutenberg.org/files/1745/1745-h/1745-h.htm).
- Ron Pressler. [JEP 444: Virtual Threads](https://openjdk.org/jeps/444). OpenJDK, 2023.
- Oracle. [`Executors` (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/Executors.html).
- Oracle. [`Future` (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/Future.html).
- Oracle. [`Semaphore` (Java SE 25)](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/Semaphore.html).
- Ron Pressler and Alan Bateman. [JEP 505: Structured Concurrency (Fifth Preview)](https://openjdk.org/jeps/505). OpenJDK, 2025.
- Alan Bateman. [JEP 491: Synchronize Virtual Threads without Pinning](https://openjdk.org/jeps/491). OpenJDK, 2024.
