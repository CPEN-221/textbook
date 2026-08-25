# Supplemental Reading | How a Java Program Runs

> We can only see a short distance ahead, but we can see plenty there that needs to
> be done.
>
> <cite>Alan Turing, “Computing Machinery and Intelligence”</cite>

The following method can fail even though it contains only one expression:

```java
static int middle(int[] values) {
    return values[values.length / 2];
}
```

It fails when `values` is `null` or empty. The exception points at `middle`, but an
earlier method may have supplied the invalid array. The failing line identifies where
the program detected the problem, not necessarily where the problem began.

To investigate, we need to reconstruct the computation that led to that line. We
need to know which methods are active, what each invocation stores, and where
execution continues after a method returns or throws. The **call stack** represents
this information.

We will develop the call-stack model one invocation at a time. By the end, you will
be able to draw a stack, trace ordinary and exceptional returns, use a stack trace as
evidence, and explain why a local reference can still lead to shared mutable state.

> **Supplemental reading:**
> [Beyond the Java Call Stack](optional-beyond-the-java-call-stack.md) follows the
> same ideas into bytecode, thread dumps, and native machine stacks.

## 1. From Source Code to Execution

Before a method can run, our source code has to become something the Java Virtual
Machine (JVM) understands:

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

`javac` translates Java source into JVM instructions called **bytecode**. When we run
the program, the JVM loads and verifies that bytecode. It may interpret instructions
directly, compile frequently executed code into native machine instructions, or mix the
two approaches.

Java source describes required behaviour; it is not a transcript of processor
instructions. One source expression may expand into several bytecode instructions,
and the JVM may later reorganise the work while preserving observable behaviour.

The `javap` tool displays the bytecode in a class file:

```bash
javac FrameDemo.java
javap -c FrameDemo
```

The view is useful, but most application debugging should begin with contracts,
tests, debugger state, and stack traces at the Java method level. We will stay at
that level for now and return to bytecode in the supplemental reading.

## 2. The Call Stack

Suppose `main` calls `load`, which calls `parse`. While `parse` runs, the invocations
of `load` and `main` remain suspended. The JVM needs to store enough information
about each invocation to resume it later.

For each active invocation, it must retain:

- which method is active;
- where that method should resume;
- the arguments its caller supplied;
- its local variables;
- any intermediate values the computation needs.

The JVM organises these active invocations as a call stack. Each invocation
contributes a **frame**. The newest frame sits on top because it is the one currently
running.

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

Calling a method adds a frame. Returning removes it and resumes the caller. `parse`
must finish before `load` can continue, and `load` must finish before `main` can
continue. Nested calls therefore use last-in, first-out order.

### Trace frame creation and removal

Consider this call chain:

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

Now unwind it. `twice` returns `40`, and its frame comes off the top. `twicePlusOne`
resumes, stores `40` in `doubled`, and returns `41`. Its frame comes off too. Finally,
`main` resumes and stores `41` in `answer`.

This model lets us predict calls and returns without reasoning about machine
registers.

It is still a model rather than a description of physical memory. The JVM
specification says what a frame must support, but a just-in-time compiler may keep a
value in a register, eliminate `doubled`, or inline `twice` into its caller. These
choices must preserve the program's observable behaviour.

## 3. Frame Contents

Our stack diagram records method names and a few variables, but the JVM needs more than
that. Conceptually, each frame carries three kinds of information.

### Local variables

First, an invocation needs its parameters and local variables:

```java
static int addOne(int x) {
    int result = x + 1;
    return result;
}
```

Two calls to `addOne` may execute at the same time. One can have `x == 10` while the
other has `x == 50`; each invocation owns a separate local-variable slot. This
separation will matter when we introduce threads.

### An operand stack

Local variables are not enough. The JVM also needs somewhere to place values while it
combines them. Bytecode commonly pushes operands onto an **operand stack**, performs an
operation, and pushes the result. To evaluate `x + 1`, it obtains `x`, obtains `1`, adds
them, and keeps the sum.

The call stack organises method invocations. The operand stack inside one
frame organises intermediate values used by that invocation.

### Return and bookkeeping information

Finally, the JVM must know how to resume the caller and how the current method refers
to fields, methods, and constants. How the JVM resolves those references does not
affect the reasoning in this chapter.

That is enough machinery for the rest of the chapter: each invocation has its own
state, space for intermediate computation, and a well-defined caller. The
supplemental reading examines the lower-level details.

## 4. Local References Can Designate Shared Objects

Frames separate invocations, but they do not automatically separate objects. This
example shows the difference:

```java
static void rename(StringBuilder builder) {
    StringBuilder alias = builder;
    alias.append("!");
}
```

`builder` and `alias` are distinct local variables. Their values, however, are
references to the same mutable `StringBuilder`:

```text
frame for rename                    shared object
+-------------------+              +------------------+
| builder ----------+------------->| StringBuilder    |
| alias   -----------+------------->| contents: "Hi"   |
+-------------------+              +------------------+
```

Calling `alias.append("!")` therefore changes the object that the caller passed as
`builder`. A new local variable did not produce a new object; it produced another
reference to the existing object.

Programmers often summarise this model as “locals live on the stack and objects live on
the heap.” That is a useful sketch, with several limits:

- A local variable of reference type contains a reference, not the object itself.
- Two frames can contain references to the same object.
- An object reachable through a local reference can also be reachable from fields or
  other threads.
- A JVM may optimise storage as long as the optimisation preserves Java's observable
  behaviour.

For software design, the reachability of a mutable object is usually more useful than
whether a particular implementation stores a reference on a stack or heap.
Aliasing gives multiple references access to one object. Reachability determines
who can observe a mutation. The same analysis applies when several threads share
objects.

## 5. Recursive Calls Create Additional Frames

Recursion can look as though a method loops back into itself, but every recursive
call creates a fresh invocation and therefore a fresh frame.

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

At `factorial(1)`, the base case returns without another call. The remaining
multiplications then complete as each invocation returns:

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

This version keeps shortening the string but never checks whether it is empty:

```java
static int length(String text) {
    return 1 + length(text.substring(1)); // no base case
}
```

Frames accumulate until the thread runs out of stack space, and the JVM throws
`StackOverflowError`. The correct repair is to add the missing base case or establish
that each call makes progress. If valid inputs can produce extreme depth, then choose
an iterative algorithm with an explicit work structure.

Java does not guarantee tail-call optimisation. Do not assume that a tail-recursive Java
method uses constant stack space.

## 6. Exception Handling Removes Frames

So far every invocation has completed through `return`. An exception completes an
invocation by a different control-flow path.

When a method throws, the JVM looks for a matching handler in the current invocation.
If it finds none, then that frame ends and the search continues in the caller. Frames
come off the stack until a handler accepts the exception or no Java frame remains.
This process is **stack unwinding**.

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

`Integer.parseInt("twenty")` cannot produce an integer, so it throws
`NumberFormatException`. Neither `parse` nor `printDouble` declares a handler, so
their frames unwind, the exception remains uncaught, and the JVM prints a trace
resembling:

```text
Exception in thread "main" java.lang.NumberFormatException: For input string: "twenty"
    at java.base/java.lang.Integer.parseInt(...)
    at ParsingDemo.parse(ParsingDemo.java:12)
    at ParsingDemo.printDouble(ParsingDemo.java:7)
    at ParsingDemo.main(ParsingDemo.java:3)
```

Read the trace as a call chain:

1. Identify the exception type and message.
2. Find the first frame belonging to your code.
3. Inspect that source line.
4. Continue downward to understand how control reached the bad call.

The first application frame shows where the failure became visible. It may not show
where the defective value originated. The frames below it tell us how we arrived there.

### Preserve causes when translating exceptions

Sometimes an abstraction should translate a low-level failure into its own
vocabulary. A configuration loader should not force every client to reason about
file-system details. We can wrap the exception while preserving the original cause:

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

The client now receives `ConfigurationException`, while a debugger or log can still
inspect the original `IOException` through the recorded cause. Translation changes
the abstraction; it should preserve the diagnostic chain.

## 7. Each Thread Uses a Separate Stack

One call stack can describe one flow of control. A concurrent program has several flows,
so each Java thread gets its own JVM stack:

```text
Thread A stack          Thread B stack            shared objects
+---------------+      +---------------+         +--------------+
| update()      |      | render()      |-------->| Model        |
+---------------+      +---------------+         +--------------+
| run()         |      | run()         |
+---------------+      +---------------+
```

`update` has no direct access to `render`'s local-variable slots. Nevertheless, both
frames may contain references to the same `Model`. Separate stacks isolate invocation
state, not the objects reachable from that state.

This distinction leads to a useful rule:

> Each thread owns its invocation state; several threads may still share reachable
> mutable objects.

That is why one thread's trace may not explain a concurrent failure. A request thread
may be waiting for a lock while another thread holds the lock and waits for network
input. We need both traces to see the dependency.

> **Aside:** Modern Java provides `StackWalker` for controlled inspection of the
> current thread's stack. It is useful for diagnostics and tooling. Business rules
> that depend on an exact stack shape are brittle because optimisation can change
> that shape.

Later chapters examine how to control that sharing.

## 8. Distinguish Java Stack Exhaustion from Native Stack Corruption

Programmers use the phrase *stack overflow* for two failures with different causes
and consequences. The distinction matters when diagnosing or explaining a failure.

### Java `StackOverflowError`

Too many active invocations exhaust the space available to one Java thread. The JVM
detects the condition and throws `StackOverflowError`. The failed operation does not
write to adjacent memory or redirect execution.

### Native stack buffer overflow

In a memory-unsafe native language, a program may instead write beyond the bounds of an
array that a native frame stores. Depending on the platform and compiler, that write may
corrupt adjacent data, including information that controls execution.

Java prevents ordinary code from performing an out-of-bounds array access:

```java
byte[] data = new byte[8];
data[8] = 1; // throws ArrayIndexOutOfBoundsException
```

The bounds check changes the failure mode. Instead of writing outside the array, Java
raises a specified exception at the invalid access. A specified exception identifies
the failed operation and is easier to test and diagnose than memory corruption.

This does not make Java programs automatically secure. Java software can still contain
injection flaws, unsafe deserialisation, authorisation bugs, denial-of-service
vulnerabilities, races, and misuse of native libraries. Memory safety removes an
important class of defects; it does not remove the need for secure design.

The supplemental reading examines native frames, stack canaries, address
randomisation, and related mitigations. The comparison here needs only one principle.

> **Design principle: prefer language and library designs that make invalid states or
> dangerous operations impossible, and otherwise make failures immediate and
> diagnosable.**

## 9. Use the Stack Model for Debugging

We began with a one-expression method and a failure whose origin was unclear. The
stack model now provides a systematic way to investigate it.

### Start from evidence

First, reproduce the failure and save the complete exception and trace. If you change
the code first, then the failure may disappear before you have recorded the
conditions that produced it.

### Locate the first relevant frame

Library frames explain the mechanism. Application frames show where our program entered
it. Start with the first frame in code you control.

### Inspect values and contracts

At the relevant frame, complete four checks:

- Identify the arguments and local variables involved in the failure.
- Identify object references that are aliases.
- State the precondition assumed by the code.
- Find the earliest caller responsible for establishing that precondition.

### Move down the call chain when necessary

If a method received a bad argument, then its caller may contain the defect. Inspect
successive caller frames until you find the earliest violated assumption that your
code should have established.

### Add a regression test

Before repairing the implementation, turn the failing input into an automated test.
The test records the failure and verifies the repair.

## 10. Design Implications

The stack model also informs several design decisions.

### Keep methods small enough to understand

Small methods do not reduce the number of frames. They make those frames informative. A
trace through `readFeed`, `parseTrip`, and `validateStop` communicates more than three
consecutive methods named `process`.

### Fail near the violated assumption

Check important preconditions in the public method that first receives a value. When
the method rejects a bad value there, it produces a useful failure. If the program
passes the value through several calls without checking it, then a later operation
may fail farther from the cause.

### Do not expose mutable representation

Local references can alias shared objects. If an observer returns a private mutable
collection, then client code can change the object without passing through its
methods. The frame is private; the reachable collection is not.

### Preserve diagnostic context

Use informative messages, preserve causes, and avoid catch blocks that discard
failures. A stack trace can report only the diagnostic context that the program
preserved.

### Treat diagrams as models

Stack diagrams, heap diagrams, and bytecode listings answer different questions.
Choose the simplest model that explains the behaviour, and do not treat it as a
literal memory layout.

## Try the Model

The diagrams are useful only if you can build and challenge them yourself. These
problems ask you to transfer the model rather than repeat the worked example.

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

Given a trace whose first application frame is `TransitFeed.parseTime`, but whose caller
is `TransitFeed.loadTrip`, decide what evidence you would inspect before changing either
method.

### 5. Compare failures

Explain the difference between:

- `StackOverflowError`;
- `ArrayIndexOutOfBoundsException`;
- a native stack buffer overflow.

## Summary

We can now account for the sequence from a method call to a failure. A call adds a
frame; a return removes it. Recursion repeats that mechanism, exceptions unwind it,
and a stack trace records the active call chain.

Frames keep invocation state separate, but references in those frames may still
reach the same mutable objects. That distinction connects this chapter to both
abstraction and concurrency. Java's bounds checks add another boundary: an invalid
array access produces a defined exception rather than an arbitrary memory write.

The model is limited to information needed for reasoning about calls; it does not
reproduce a JVM's optimised memory layout. That is sufficient for the debugging and
design tasks in this chapter. The
[supplemental reading](optional-beyond-the-java-call-stack.md) examines bytecode,
inlining, thread dumps, and native frames.

## References

- Alan Turing, [“Computing Machinery and Intelligence”](https://cbmm.mit.edu/sites/default/files/documents/turing.pdf)
- [The Java Virtual Machine Specification, §2.5.2: Java Virtual Machine Stacks](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-2.html#jvms-2.5.2)
- [The Java Virtual Machine Specification, §2.6: Frames](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-2.html#jvms-2.6)
- [`javap` documentation for Java Development Kit (JDK) 25](https://docs.oracle.com/en/java/javase/25/docs/specs/man/javap.html)
- [`StackWalker` application programming interface (API) documentation](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/StackWalker.html)
- [Common Weakness Enumeration (CWE) 121: Stack-based Buffer Overflow](https://cwe.mitre.org/data/definitions/121.html)
