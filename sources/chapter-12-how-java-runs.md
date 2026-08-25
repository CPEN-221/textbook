# Chapter 12 | How a Java Program Runs

This method is too small to look mysterious:

```java
static int middle(int[] values) {
    return values[values.length / 2];
}
```

Then it fails.

Perhaps `values` is `null`. Perhaps it is empty. The exception points at `middle`, but the bad array may have travelled through five other methods before arriving there. The line that failed is only the end of the story.

To work backward, we need a picture of the computation that led to that line. We need to know which methods are active, what each invocation remembers, and where execution goes when a method returns or throws. That picture is the **call stack**.

We will build the picture one call at a time. By the end, you will be able to draw a stack, trace ordinary and exceptional returns, use a stack trace as evidence, and explain why a local reference can still lead to shared mutable state.

> **Optional deep dive:** [Beyond the Java Call Stack](optional-beyond-the-java-call-stack.md) follows the same ideas into bytecode, thread dumps, and native machine stacks. The chapters that follow do not require that material; treat it as a reward for wanting to lift the floorboards.

## 1. From Source Code to Execution

Before a method can run, our source code has to become something the JVM understands:

```text
Java source (.java)
        |
        | javac
        v
Java bytecode (.class)
        |
        | class loading, verification, and execution
        v
Running JVM
```

`javac` translates Java source into JVM instructions called **bytecode**. When we run the program, the JVM loads and verifies that bytecode. It may interpret instructions directly, compile frequently executed code into native machine instructions, or mix the two approaches.

That gives us our first boundary. Java source describes required behaviour; it is not a transcript of processor instructions. One source expression may expand into several bytecode instructions, and the JVM may later reorganize the work again.

If you are curious, `javap` lets you peek at the bytecode:

```bash
javac FrameDemo.java
javap -c FrameDemo
```

The view is useful, but it is usually the wrong place to begin debugging application code. Our contracts, tests, debugger, and stack traces all speak in terms of Java methods. We will stay at that level for now and return to bytecode in the optional chapter.

## 2. The Call Stack

Suppose `main` calls `load`, which calls `parse`. While `parse` runs, `load` has not vanished. It is waiting to resume, and `main` is waiting beneath it. The JVM needs to remember enough about every paused call to pick up exactly where it left off.

For each active invocation, it must retain:

- which method is active;
- where that method should resume;
- the arguments its caller supplied;
- its local variables;
- any intermediate values the computation needs.

The JVM organizes these active invocations as a **call stack**. Each invocation contributes a **frame**. The newest frame sits on top because it is the one currently running.

The active method is at the top:

```text
top     +-----------------------------+
        | frame for current method    |
        +-----------------------------+
        | frame for its caller        |
        +-----------------------------+
        | frame for caller's caller   |
bottom  +-----------------------------+
```

Calling a method adds a frame. Returning removes it and uncovers the caller. `parse` must finish before `load` can continue, and `load` must finish before `main` can continue. The stack is last-in, first-out because nested calls leave no other sensible order.

### Watching frames come and go

Here is a concrete call chain:

```java
public final class FrameDemo {
    public static void main(String[] args) {
        int answer = twicePlusOne(20);
        System.out.println(answer);
    }

    static int twicePlusOne(int value) {
        int doubled = twice(value);
        return doubled + 1;
    }

    static int twice(int value) {
        return value * 2;
    }
}
```

When `twicePlusOne(20)` calls `twice(20)`, three invocations are active:

```text
top     +----------------------------------+
        | twice                            |
        | value = 20                       |
        +----------------------------------+
        | twicePlusOne                     |
        | value = 20                       |
        | doubled = not assigned yet       |
        +----------------------------------+
        | main                             |
        | args -> String[]                 |
        | answer = not assigned yet        |
bottom  +----------------------------------+
```

Now unwind it. `twice` returns `40`, and its frame comes off the top. `twicePlusOne` resumes, stores `40` in `doubled`, and returns `41`. Its frame comes off too. Finally, `main` resumes and stores `41` in `answer`.

We can now predict calls and returns without knowing a single machine register. That is exactly what the picture is for.

It is still a model, not a photograph of RAM. The JVM specification says what a frame must support, but a just-in-time compiler may keep a value in a register, eliminate `doubled`, or inline `twice` into its caller. The furniture may move; the behaviour may not.

## 3. What Is in a Frame?

Our stack diagram records method names and a few variables, but the JVM needs a little more machinery. Conceptually, each frame carries three kinds of information.

### Local variables

First, an invocation needs its parameters and local variables:

```java
static int addOne(int x) {
    int result = x + 1;
    return result;
}
```

Two calls to `addOne` may execute at the same time. One can have `x == 10` while the other has `x == 50`; each invocation owns a separate local-variable slot. This separation will matter when we introduce threads.

### An operand stack

Local variables are not enough. The JVM also needs somewhere to place values while it combines them. Bytecode commonly pushes operands onto an **operand stack**, performs an operation, and pushes the result. To evaluate `x + 1`, it obtains `x`, obtains `1`, adds them, and keeps the sum.

The terminology is annoyingly economical: we now have a stack inside a frame inside another stack. The **call stack** organizes method invocations. The **operand stack** inside one frame organizes intermediate values.

### Return and bookkeeping information

Finally, the JVM must know how to resume the caller and how the current method refers to fields, methods, and constants. We can leave the linking details below the abstraction barrier for now.

That is enough machinery for the rest of this chapter: each invocation has its own state, scratch space for computation, and a well-defined caller. The optional chapter opens the box further.

## 4. References, Objects, Stacks, and the Heap

Frames separate invocations, but they do not automatically separate objects. Here is the smallest example that exposes the difference:

```java
static void rename(StringBuilder builder) {
    StringBuilder alias = builder;
    alias.append("!");
}
```

`builder` and `alias` are distinct local variables. Their values, however, are references to the same mutable `StringBuilder`:

```text
frame for rename                    shared object
+-------------------+              +------------------+
| builder ----------+------------->| StringBuilder    |
| alias   -----------+------------->| contents: "Hi"   |
+-------------------+              +------------------+
```

Calling `alias.append("!")` therefore changes the object that the caller passed as `builder`. A new local variable did not produce a new object; it produced one more route to the old one.

Programmers often summarize this model as “locals live on the stack and objects live on the heap.” That is a useful sketch, with several limits:

- A local variable of reference type contains a reference, not the object itself.
- Two frames can contain references to the same object.
- An object reachable through a local reference can also be reachable from fields or other threads.
- A JVM may optimize storage as long as the optimization preserves Java's observable behaviour.

For software design, “stack or heap?” is usually less useful than “who can reach this mutable object?” **Aliasing** gives multiple references access to one object. Reachability determines who can observe a mutation. We will use that question again when several threads enter the picture.

## 5. Recursion Repeats Method Invocation

Recursion can look as though a method loops back into itself. It does not. Every recursive call creates a fresh invocation and therefore a fresh frame.

```java
static long factorial(int n) {
    if (n < 0) {
        throw new IllegalArgumentException("n must be non-negative");
    }
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}
```

Trace `factorial(4)`. Each call postpones its multiplication until the smaller call returns:

```text
factorial(4)
factorial(4) -> factorial(3)
factorial(4) -> factorial(3) -> factorial(2)
factorial(4) -> factorial(3) -> factorial(2) -> factorial(1)
```

At `factorial(1)`, the base case can answer without another call. Now the postponed work climbs back through the frames:

```text
factorial(1) returns 1
factorial(2) returns 2 * 1  = 2
factorial(3) returns 3 * 2  = 6
factorial(4) returns 4 * 6  = 24
```

The stack makes the recursive design obligations visible. We need:

1. a base case that can produce an answer directly;
2. a recursive case that reduces the problem;
3. an argument explaining why repeated reduction must reach the base case.

### Stack exhaustion

What if the base case never gets a turn? This version keeps shortening the string but never checks whether it is empty:

```java
static int length(String text) {
    return 1 + length(text.substring(1)); // no base case
}
```

Frames accumulate until the thread runs out of stack space, and the JVM throws `StackOverflowError`. Catching the error would treat the smoke alarm as a kitchen timer. Fix the missing base case or the lack of progress. If valid inputs can produce extreme depth, choose an iterative algorithm with an explicit work structure.

Java does not guarantee tail-call optimization. Do not assume that a tail-recursive Java method uses constant stack space.

## 6. Exceptions Unwind the Stack

So far every frame has left politely through `return`. Exceptions take the fire exit.

When a method throws, the JVM looks for a matching handler in the current invocation. If it finds none, that frame ends and the search continues in the caller. Frames come off the stack until a handler accepts the exception or no Java frame remains. This process is **stack unwinding**.

```java
public final class ParsingDemo {
    public static void main(String[] args) {
        printDouble("twenty");
    }

    static void printDouble(String text) {
        int value = parse(text);
        System.out.println(2 * value);
    }

    static int parse(String text) {
        return Integer.parseInt(text);
    }
}
```

`Integer.parseInt("twenty")` cannot produce an integer, so it throws `NumberFormatException`. `parse` has no handler. Neither does `printDouble`. Their frames unwind, the exception remains uncaught, and the JVM prints a trace resembling:

```text
Exception in thread "main" java.lang.NumberFormatException: For input string: "twenty"
    at java.base/java.lang.Integer.parseInt(...)
    at ParsingDemo.parse(ParsingDemo.java:12)
    at ParsingDemo.printDouble(ParsingDemo.java:7)
    at ParsingDemo.main(ParsingDemo.java:3)
```

Do not read the trace as a wall of blame. Read it as a call chain:

1. Identify the exception type and message.
2. Find the first frame belonging to your code.
3. Inspect that source line.
4. Continue downward to understand how control reached the bad call.

The first application frame shows where the failure became visible. It may not show where the defective value originated. The frames below it tell us how we arrived there.

### Preserve causes when translating exceptions

Sometimes an abstraction should translate a low-level failure into its own vocabulary. A configuration loader should not force every client to reason about file-system details. We can wrap the exception—but we should keep the evidence:

```java
static Configuration loadConfiguration(Path path) {
    try {
        String text = Files.readString(path);
        return Configuration.parse(text);
    } catch (IOException e) {
        throw new ConfigurationException(
            "Unable to load configuration from " + path, e);
    }
}
```

The client now receives `ConfigurationException`, while a debugger or log can still follow the cause back to the original `IOException`. Translation changes the abstraction; it should not erase the trail.

## 7. Each Thread Has a Stack

One call stack can describe one flow of control. A concurrent program has several flows, so each Java thread gets its own JVM stack:

```text
Thread A stack          Thread B stack            shared objects
+---------------+      +---------------+         +--------------+
| update()      |      | render()      |-------->| Model        |
+---------------+      +---------------+         +--------------+
| run()         |      | run()         |
+---------------+      +---------------+
```

`update` has no direct access to `render`'s local-variable slots. Nevertheless, both frames may contain references to the same `Model`. Separate stacks isolate invocation state, not the objects reachable from that state.

This distinction leads to a useful rule:

> Each thread owns its invocation state; several threads may still share reachable mutable objects.

That is why one thread's trace may not solve a concurrent failure. A request thread may be waiting for a lock while another thread holds the lock and waits for network input. The first trace shows the queue; the second shows who parked the truck across the road.

> **Aside:** Modern Java provides `StackWalker` for controlled inspection of the current thread's stack. It is useful for diagnostics and tooling. Business rules that depend on the exact stack shape are usually brittle, especially once optimization enters the story.

We now have the bridge to concurrency: each thread owns its stack, but several threads may share mutable objects. Later chapters will show us how to control that sharing.

## 8. Java Memory Safety and Native Stack Corruption

Programmers use the phrase *stack overflow* for two failures that sound related but behave very differently. We should separate them before the vocabulary causes trouble.

### Java `StackOverflowError`

Too many active invocations exhaust the space available to one Java thread. The JVM detects the condition and throws `StackOverflowError`. The program does not gain permission to wander into neighbouring objects or redirect execution.

### Native stack buffer overflow

In a memory-unsafe native language, a program may instead write beyond the bounds of an array that a native frame stores. Depending on the platform and compiler, that write may corrupt adjacent data, including information that controls execution.

Java prevents ordinary code from performing an out-of-bounds array access:

```java
byte[] data = new byte[8];
data[8] = 1; // throws ArrayIndexOutOfBoundsException
```

The bounds check changes the failure mode. Instead of silently writing somewhere else, Java raises a specified exception at the invalid access. Failure is not pleasant, but local, defined failure is far easier to test and diagnose than memory corruption.

This does not make Java programs automatically secure. Java software can still contain injection flaws, unsafe deserialization, authorization bugs, denial-of-service vulnerabilities, races, and misuse of native libraries. Memory safety removes an important class of defects; it does not remove the need for secure design.

> **Optional direction:** The companion chapter examines native frames, stack canaries, address randomization, and related mitigations. We stop here because the software-construction lesson does not need those details:

> Prefer language and API designs that make invalid states or dangerous operations impossible, and otherwise make failures immediate and diagnosable.

## 9. Debugging with the Stack Model

We began with a tiny method and a failure whose origin was unclear. The stack model now gives us a disciplined way to investigate it.

### Start from evidence

First, reproduce the failure and save the complete exception and trace. Changing code before preserving the evidence is how one bug becomes a shy bug.

### Locate the first relevant frame

Library frames explain the mechanism. Application frames show where our program entered it. Start with the first frame in code you control.

### Inspect values and contracts

At the relevant frame, ask:

- Which arguments and local variables matter?
- Which object references are aliases?
- Which precondition did the code assume?
- Which earlier caller was responsible for establishing it?

### Move down the call chain when necessary

If a method received a bad argument, its caller may contain the defect. Walk down the trace until you find the earliest violated assumption that your code should have established.

### Add a regression test

Before repairing the implementation, turn the failing input into an automated test. The test records the discovery and makes the repair earn its keep.

## 10. Design Lessons

The stack is implementation machinery, but it pays rent at the design level too.

### Keep methods small enough to understand

Small methods do not reduce the number of frames. They make those frames informative. A trace through `readFeed`, `parseTrip`, and `validateStop` communicates more than three consecutive methods named `process`.

### Fail near the violated assumption

Check important preconditions at the abstraction boundary. When a method rejects a bad value there, it produces a useful failure. When the method allows the same value to drift through six calls, the value tends to fail later, farther from its cause.

### Do not expose mutable representation

Local references can alias shared objects. If an observer returns a private mutable collection, client code can change the object without passing through its methods. The frame is private; the reachable collection is not.

### Preserve diagnostic context

Use informative messages, preserve causes, and avoid catch blocks that swallow failures. A stack trace can only report evidence that the program kept.

### Treat diagrams as models

Stack diagrams, heap diagrams, and bytecode listings answer different questions. Choose the smallest model that explains the behaviour. A teaching diagram is a map, not a land survey.

## Try the Model

The diagrams are useful only if you can build and challenge them yourself. These problems ask you to transfer the model rather than repeat the worked example.

### 1. Draw the stack

Draw the active frames immediately after `g(1)` begins:

```java
static int f(int x) {
    return g(x + 1);
}

static int g(int y) {
    return 3 * y;
}

public static void main(String[] args) {
    System.out.println(f(0));
}
```

Then show the order in which the frames complete.

### 2. Find the alias

Explain why this method changes the caller's list even though `items` is a local variable:

```java
static void addDefault(List<String> items) {
    List<String> working = items;
    working.add("default");
}
```

Rewrite the method to return a new list without changing the input.

### 3. Diagnose the recursion

State the intended base case, progress measure, and failure mode:

```java
static int sum(int[] values, int index) {
    if (index == values.length - 1) {
        return values[index];
    }
    return values[index] + sum(values, index);
}
```

### 4. Read a trace

Given a trace whose first application frame is `TransitFeed.parseTime`, but whose caller is `TransitFeed.loadTrip`, decide what evidence you would inspect before changing either method.

### 5. Compare failures

Explain the difference between:

- `StackOverflowError`;
- `ArrayIndexOutOfBoundsException`;
- a native stack buffer overflow.

## Where We Have Arrived

We can now account for the route from a method call to a failure. A call adds a frame; a return removes it. Recursion repeats that mechanism, exceptions unwind it, and a stack trace leaves us a record of the route.

Frames keep invocation state separate, but references in those frames may still reach the same mutable objects. That distinction connects this chapter to both abstraction and concurrency. Java's bounds checks add another kind of boundary: an invalid array access becomes a defined exception rather than an arbitrary memory write.

The model is deliberately modest. It tells us how to reason about calls without pretending to reproduce a JVM's optimized memory layout. That is enough for debugging and design. If you want to see how bytecode, inlining, thread dumps, and native frames fit underneath it, the [optional deep dive](optional-beyond-the-java-call-stack.md) picks up from here.

## Sources and provenance

We wrote this chapter anew for CPEN 221. It does not reproduce the prose, diagrams, or worked examples from the previous Chapter 12.

Technical reference material:

- [The Java Virtual Machine Specification, §2.5.2: Java Virtual Machine Stacks](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-2.html#jvms-2.5.2)
- [The Java Virtual Machine Specification, §2.6: Frames](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-2.html#jvms-2.6)
- [`javap` documentation for JDK 25](https://docs.oracle.com/en/java/javase/25/docs/specs/man/javap.html)
- [`StackWalker` API documentation](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/StackWalker.html)
- [CWE-121: Stack-based Buffer Overflow](https://cwe.mitre.org/data/definitions/121.html)
