# Optional Reading | Beyond the Java Call Stack

> A little learning is a dangerous thing;<br>
> Drink deep, or taste not the Pierian spring.
>
> <cite>Alexander Pope, “An Essay on Criticism”</cite>

In [How a Java Program Runs](chapter-12-how-java-runs.md), we treated a frame as one
box on a thread's call stack. That model held enough invocation state to trace calls,
recursion, and exceptions, but it omitted several implementation details.

This optional chapter examines the operand stack, method invocation in bytecode,
inlining, thread diagnostics, and native stack memory. Later core readings do not
require these details. The goal is to distinguish source-level reasoning, Java
Virtual Machine (JVM) requirements, and observations about a particular
implementation.

## 1. Separate Guarantees from Observations

Before interpreting a bytecode listing, we need to identify what kind of claim the
listing supports.

As we investigate, sort claims into three layers:

1. **Language guarantee:** the Java Language Specification requires it.
2. **Virtual-machine guarantee:** every conforming JVM must provide it.
3. **Implementation observation:** something seen in one compiler, JVM, operating system, or processor.

Java guarantees the specified result of `a + b`. The JVM instruction set includes `iadd`. A particular JVM may compile the method into native code that never interprets that `iadd` at all. All three statements can be true because they describe different layers.

For each claim, identify which layer guarantees it. This prevents us from treating an
observation from one JVM run as a Java guarantee.

We will begin with two tools included in the Java Development Kit (JDK):

```bash
javac -g BytecodeDemo.java
javap -c -l -p BytecodeDemo
```

`javap` displays bytecode, line and local-variable tables, and non-public members. Its
output may change with the compiler version and options. Predict, run, and inspect;
do not generalise from one listing without checking which details the specifications
require.

## 2. Tracing an Operand Stack

The source expression `x + y` corresponds to several bytecode operations. The JVM
must load two values, add them, and retain the result. We can inspect those operations
in this method:

```java
public final class BytecodeDemo {
    static int adjust(int x, int y) {
        int sum = x + y;
        return sum * 2;
    }
}
```

Compile the class and inspect it. A typical `javac` produces:

```text
0: iload_0
1: iload_1
2: iadd
3: istore_2
4: iload_2
5: iconst_2
6: imul
7: ireturn
```

The instruction names are compact once we split them up. `iload_0` loads an integer from local slot 0. `istore_2` stores an integer in slot 2. For this static method, the slots begin as:

```text
slot 0: x
slot 1: y
slot 2: sum
```

Now call `adjust(4, 7)` and follow the values. The rightmost item is the top of the operand stack:

| Instruction | Local variables after the instruction | Operand stack after the instruction |
|---|---|---|
| initial | `[4, 7, ?]` | `[]` |
| `iload_0` | `[4, 7, ?]` | `[4]` |
| `iload_1` | `[4, 7, ?]` | `[4, 7]` |
| `iadd` | `[4, 7, ?]` | `[11]` |
| `istore_2` | `[4, 7, 11]` | `[]` |
| `iload_2` | `[4, 7, 11]` | `[11]` |
| `iconst_2` | `[4, 7, 11]` | `[11, 2]` |
| `imul` | `[4, 7, 11]` | `[22]` |
| `ireturn` | invocation completes | return value `22` |

At `iadd`, the operands disappear and their sum takes their place. `istore_2` then moves that sum into the local slot for `sum`. Finally, `ireturn` sends `22` back to the caller.

The trace illustrates the distinction from the core chapter: local slots hold values
across expressions, while the operand stack holds values used by the expression the
JVM currently evaluates.

### Limits of the bytecode trace

That trace is exact about the bytecode's meaning. It does not imply that an optimised
JVM performs the same sequence of physical memory operations.

A JVM may:

- interpret the bytecode directly;
- keep values the program uses frequently in processor registers;
- compile the method into native code;
- eliminate `sum` as an unnecessary temporary;
- inline `adjust` into its caller;
- calculate a constant result at compile time when the compiler knows the arguments.

The JVM may interpret, compile, inline, eliminate `sum`, or keep values in registers.
`adjust(4, 7)` must still produce `22`; Java does not otherwise specify which rows of
the table correspond to physical operations.

## 3. Method Calls and New Frames

We can see how an invocation begins and ends by adding a caller:

```java
static int score(int raw) {
    return adjust(raw, 3) + 1;
}
```

The caller's bytecode now needs an invocation:

```text
0: iload_0
1: iconst_3
2: invokestatic  #...  // Method adjust:(II)I
5: iconst_1
6: iadd
7: ireturn
```

Just before `invokestatic`, the caller has placed the arguments on its operand stack:

```text
[raw, 3]
```

The instruction crosses a frame boundary. Conceptually, the JVM:

1. identifies the target method;
2. creates a frame for the new invocation;
3. transfers argument values into that frame's local variables;
4. makes the new frame current;
5. executes the target method;
6. removes its frame when it returns; and
7. places the value it returned on the caller's operand stack.

For `score(4)`, the new frame receives `4` and `3`. `adjust` returns `14`; the caller resumes with `14` on its operand stack, adds `1`, and returns `15`. We have connected the operand stack inside a frame to the call stack around it.

An instance method needs one more argument: the receiver. In an ordinary instance method, local slot 0 contains `this`; the declared parameters occupy the slots that follow.

### Invocation instructions

Not every call selects its target in the same way. The JVM therefore has several invocation instructions:

- `invokestatic` for static methods;
- `invokevirtual` for ordinary dynamically dispatched instance methods;
- `invokeinterface` for calls through interface types;
- `invokespecial` for operations with special selection rules, including constructors;
- `invokedynamic` for a call site whose behaviour the runtime links dynamically.

The names help us read listings. The design connection matters more: a call written
against an interface can select an implementation from the receiver's run-time type.
These invocation instructions implement different method-selection rules.

## 4. Linking Symbolic Names

A class file must call methods that the JVM may not have loaded yet. A process-memory
address stored in the file would be invalid on another machine or when classes load
in a different order.

Instead, the class file carries a **constant pool**: symbolic information about classes, methods, fields, literals, and method types. When bytecode refers to a method, the JVM resolves that symbolic reference and links it to the appropriate run-time entity. It may perform some resolution early and defer other parts until execution needs them.

Symbolic references support several JVM capabilities:

- the JVM can load classes at run time;
- the same class file can run on different processor architectures;
- the JVM can select overridden methods according to the receiver's run-time class;
- the verifier can check bytecode before execution;
- JVM implementations can choose different internal layouts.

Each frame can reach its method's class-level run-time constant pool. We omitted that
connection from the core diagram because it does not help us trace `factorial(4)`.
It matters here because we are examining how the JVM resolves symbolic bytecode.

## 5. Frames Are Specification-Level Structures

Our bytecode trace makes a frame look concrete: three local slots beside a short
operand stack. The JVM specification is more careful. It requires the frame to
provide:

- an array of local variables;
- an operand stack;
- access to the run-time constant pool;
- information the frame needs for normal and abrupt method completion.

It does not require every JVM to arrange those components in the same physical layout.

A native application binary interface may prescribe registers, alignment, argument
locations, and return conventions for one platform. JVM bytecode does not encode
those platform-specific choices, so the same class file can run on different
platforms.

### Inlining and logical frames

Suppose `score` calls the short `adjust` method millions of times. A just-in-time
compiler may **inline** it: substitute the body of `adjust` into the compiled body of
`score`. The native code may contain no separate call and no ordinary physical frame
for `adjust`.

JVMs retain metadata that lets them reconstruct logical frames for debugging and
exception reporting. A method can therefore appear in a Java trace even when the
optimised native code used no separate call or physical frame for it.

Inlining shows the separation between the Java-level invocation model and its
optimised implementation.

## 6. Exceptional Completion

Our invocation trace handled normal completion: the callee reaches `ireturn` and
returns a value. An exception completes the invocation without a normal return.

At the bytecode level, an exception table associates protected instruction ranges with handlers. When a method throws, the JVM:

1. searches the current method's applicable handlers;
2. clears the operand stack, places the exception reference on it, and transfers
   control if a matching handler exists;
3. completes the current invocation abruptly if no handler matches;
4. restores the caller's frame and continues the search there; and
5. terminates the thread after uncaught-exception processing if no Java frame handles
   the exception.

These are the JVM-level steps behind stack unwinding.

### `finally` and try-with-resources

Source-level cleanup looks compact because the compiler does the bookkeeping. The JVM does not need one universal “run this `finally` block” instruction; `javac` emits control flow and handlers that reproduce the source semantics.

Try-with-resources has one especially useful edge case. If the main operation fails
and `close` fails too, then Java keeps the main exception and attaches the cleanup
failure as a **suppressed exception**. `Throwable.getSuppressed()` retrieves it.

The compiler generates more control flow than appears in the source. Experiment 3
shows how both failures remain available for inspection.

## 7. Inspecting Multiple Thread Stacks

One exception trace follows one thread. A concurrent program may be unable to
progress because of the state of another thread.

Imagine these two request handlers:

```text
request-handler-1:
    waiting to acquire inventoryLock

request-handler-2:
    holds inventoryLock
    blocked while reading from a socket
```

The first trace tells us where a thread waits, but not why the wait persists. The second reveals the dependency: a thread is holding `inventoryLock` while it waits for the network.

We can investigate without guessing:

1. Capture all thread stacks at approximately the same moment.
2. Group threads by state: runnable, waiting, timed waiting, or blocked.
3. Identify locks that blocked threads are waiting to acquire.
4. Find the threads that own those locks.
5. Inspect what the owners are doing while holding them.
6. Repeat the capture to distinguish a transient wait from persistent lack of progress.

The JDK's `jcmd` tool can request thread information from a running JVM. Integrated
development environments (IDEs) and monitoring systems often present the same
evidence graphically. Experiment 4 constructs a stable blocked thread for inspection.

### Deadlock as a cycle

A long wait is not automatically a deadlock. Deadlock requires a dependency cycle, such as:

```text
Thread A owns lock 1 and waits for lock 2.
Thread B owns lock 2 and waits for lock 1.
```

The stacks show where each thread requested a lock; lock ownership completes the cycle. Blocking is normal. A cycle with no possible resolution is the bug.

## 8. From JVM Frames to Native Frames

The JVM itself eventually runs native instructions, and native calls require their
own bookkeeping. This moves the discussion from the portable JVM model to
platform-specific calling conventions.

We might draw a simplified native frame as:

```text
higher addresses
+-----------------------------+
| arguments or saved values   |
+-----------------------------+
| return address              |
+-----------------------------+
| saved frame information     |
+-----------------------------+
| local variables             |
| including local buffers     |
+-----------------------------+
lower addresses
```

This picture is intentionally generic. Change the processor, operating system, compiler, optimisation level, or calling convention and the layout may change. Values may remain in registers, and a compiler may omit a dedicated frame pointer.

The portable requirement is smaller than the picture: the callee needs local state and a way to resume the caller.

### Return addresses and control flow

At the machine level, a return usually depends on an address that tells the processor
where the caller resumes. If an unsafe write corrupts that control information, then
the processor may transfer control to an unintended address.

## 9. Native Stack Buffer Overflows

This C-like function creates a 16-byte local buffer and then calls an input operation that knows nothing about the boundary:

```c
void receive(void) {
    char buffer[16];
    read_without_a_bound(buffer);
}
```

Write a seventeenth byte and the operation leaves the array. What it reaches next depends on the actual frame: another local value, saved state, padding, or control information.

The stack is not full. The write is out of bounds. That distinction separates a native **stack-buffer overflow** from Java stack exhaustion.

Possible consequences include:

- corrupted values and incorrect computation;
- a process crash;
- disclosure or alteration of sensitive data;
- control-flow redirection;
- execution of attacker-chosen behaviour.

The exact outcome depends on the platform and surrounding code. One overflow may crash immediately; another may corrupt a value that fails much later. We should not turn one historical layout into a universal recipe.

### Java array bounds checking

Now try the corresponding invalid index in ordinary Java:

```java
byte[] buffer = new byte[16];
buffer[16] = 1; // ArrayIndexOutOfBoundsException
```

The JVM checks the index before the store. The program receives a specified exception
at the invalid access instead of writing beyond the array.

The guarantee applies to ordinary safe Java operations. Native libraries, the Java
Native Interface (JNI), and low-level facilities cross into a different trust
boundary and require their own memory-safety controls.

## 10. Defence in Depth for Native Code

Preventing the write is best. Real native systems also assume that prevention may fail and add layers behind it.

### Bounds-aware programming

Native code should carry buffer lengths, reject oversized input, and use memory-safe
representations where practical. The remaining controls limit the consequences when
prevention fails.

### Stack canaries

A compiler can place a recognisable value between vulnerable local data and
sensitive frame information. The compiler inserts code that checks the **stack
canary** before returning. If the value changed, then the process terminates rather
than trusting damaged control state.

A canary detects some overwrites; it does not make the write valid and may miss some memory errors.

### Non-executable memory

Memory protection can mark writable data pages as non-executable. That blocks a traditional technique in which an attacker writes bytes into data memory and the processor executes them directly.

It does not prevent all control-flow attacks. Attackers may still misuse existing executable code if an unsafe write corrupts control data.

### Address-space layout randomisation

Address-space layout randomisation moves code, libraries, stacks, and other regions
between runs. Useful addresses become harder to predict. Information leaks can
weaken the protection, so randomisation must be combined with other controls.

### Control-flow protections

Compilers and processors can protect return addresses or restrict indirect
transfers. These mechanisms can limit exploitation, but the program must still
prevent the out-of-bounds write.

These controls form a defence-in-depth strategy:

> Prevent the invalid operation where possible; detect it when prevention fails; limit its consequences if detection also fails.

## 11. Summary of the Model

The detailed model adds the following information to the core frame model:

- JVM bytecode commonly evaluates expressions with an operand stack.
- Method parameters and locals occupy conceptual slots in a frame.
- Invocation transfers arguments into a new logical frame and returns a value to the caller.
- Constant-pool references allow class files to describe operations symbolically.
- A JVM may interpret, compile, inline, or otherwise optimise code while preserving Java behaviour.
- Exception tables support handler selection and stack unwinding.
- Multiple thread stacks reveal wait dependencies that one trace cannot show.
- JVM frames are portable specification-level structures; native frames follow platform-specific conventions.
- A Java `StackOverflowError` is not a native stack buffer overflow.
- Bounds checking and layered mitigations prevent or constrain native memory-corruption attacks.

## Experiments

The following six experiments compare the model with observations from actual tools
and programs.

Each experiment begins with a prediction and ends with an explanation. The Java
observations reported below came from Eclipse Temurin 25.0.4.1. Run the experiments
in a temporary project rather than an assignment repository. Record the JDK,
operating system, and command-line options you used; implementation observations can
legitimately differ across machines.

### Experiment 1: Predict bytecode before viewing it

**Question:** How do source-level temporary variables affect the bytecode's local slots and operand stack?

We have already traced `BytecodeDemo` on paper. Start by asking whether an explicit temporary variable leaves a visible mark:

```java
public final class BytecodeDemo {
    static int adjust(int x, int y) {
        int sum = x + y;
        return sum * 2;
    }
}
```

Before compiling, write down the local slots and instruction sequence you expect. Then run:

```bash
javac -g BytecodeDemo.java
javap -c -l -p BytecodeDemo
```

Now replace the method body with:

```java
return (x + y) * 2;
```

Compile and inspect it again.

**Observed during validation:** `javap` showed no local-variable entry for `sum` in
the second version; the bytecode retained the result of `x + y` on the operand stack.
The two versions compute the same value for every pair of `int` arguments even though
their bytecode differs.

Try a third version:

```java
int sum = x + y;
int doubled = sum * 2;
return doubled;
```

Compile once with `-g` and once with `-g:none`:

```bash
javac -g BytecodeDemo.java
javap -c -l -p BytecodeDemo

javac -g:none BytecodeDemo.java
javap -c -l -p BytecodeDemo
```

**Explain:**

1. Which differences change the computation?
2. Which differences only affect debugging metadata?
3. Does the presence of a local-variable-table entry prove that a value occupies a physical stack location during optimised execution?

### Experiment 2: Measure recursive stack depth

**Question:** Is there one universal maximum recursion depth for Java?

To make the limit visible, use this deliberately non-terminating recursion:

```java
public final class StackDepthDemo {
    private static int depth;

    static void descend() {
        depth++;
        descend();
    }

    public static void main(String[] args) {
        try {
            descend();
        } catch (StackOverflowError error) {
            System.out.println("Observed depth: " + depth);
        }
    }
}
```

Compile it and run it several times:

```bash
javac StackDepthDemo.java
java StackDepthDemo
java -Xss256k StackDepthDemo
java -Xss1m StackDepthDemo
```

Some JVMs reject stack sizes below an implementation-specific minimum. If that
happens, then report the rejection rather than repeatedly reducing the value.

**Observed during validation:** Each run ended with `StackOverflowError`, and the
reported depths changed with the thread-stack setting. The exact numbers may vary
between runs, JDKs, architectures, compilation states, and method shapes. Adding a
local `long` or another method call may also change the result.

This is one of the rare cases where catching `StackOverflowError` is useful: a controlled experiment that immediately terminates. Application code should not use it as a normal stopping condition.

**Explain:**

1. Why is “Java supports recursion to depth 10,000” not a valid general claim?
2. Why might adding an apparently irrelevant local variable change the observed depth?
3. Why does this experiment not show the size of a single abstract JVM frame?

### Experiment 3: Observe exception suppression

**Question:** What happens if the main computation and resource cleanup both fail?

We need two failures at once to expose suppression. Create a resource whose `close` method fails, then fail inside the try body as well:

```java
public final class SuppressedDemo {
    private static final class NoisyResource implements AutoCloseable {
        @Override
        public void close() {
            throw new IllegalStateException("close failed");
        }
    }

    public static void main(String[] args) {
        try (NoisyResource resource = new NoisyResource()) {
            throw new IllegalArgumentException("work failed");
        } catch (Exception exception) {
            System.out.println("Primary: " + exception);
            for (Throwable suppressed : exception.getSuppressed()) {
                System.out.println("Suppressed: " + suppressed);
            }
        }
    }
}
```

Run it:

```bash
javac SuppressedDemo.java
java SuppressedDemo
```

**Observed during validation:**

```text
Primary: java.lang.IllegalArgumentException: work failed
Suppressed: java.lang.IllegalStateException: close failed
```

Next, remove the exception from the body so that only `close` fails.

**Result of the change:** With no primary failure, the exception from `close` becomes
the exception caught by the `catch` block rather than a suppressed exception.

Finally, inspect the compiled method:

```bash
javap -c -p SuppressedDemo
```

The compiler will generate considerably more elaborate control flow than the source suggests.

**Explain:**

1. Why does Java preserve the failure from the body as the primary exception?
2. What debugging evidence would we lose if the program silently discarded the cleanup failure?
3. Why is try-with-resources a language construct rather than one simple bytecode instruction?

### Experiment 4: Capture a blocked thread

**Question:** Can the stack of one thread explain why another thread cannot progress?

To inspect a blocked thread, we first need one that stays blocked long enough to
observe. This program deliberately sleeps while holding a lock. Do not use this
locking pattern in production code:

```java
import java.util.concurrent.CountDownLatch;

public final class BlockedThreadDemo {
    public static void main(String[] args) throws InterruptedException {
        Object lock = new Object();
        CountDownLatch lockAcquired = new CountDownLatch(1);

        Thread holder = Thread.ofPlatform().name("lock-holder").start(() -> {
            synchronized (lock) {
                lockAcquired.countDown();
                try {
                    Thread.sleep(2_000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
        });

        lockAcquired.await();

        Thread waiter = Thread.ofPlatform().name("lock-waiter").start(() -> {
            synchronized (lock) {
                System.out.println("waiter acquired the lock");
            }
        });

        while (waiter.getState() != Thread.State.BLOCKED) {
            Thread.sleep(10);
        }

        System.out.println(waiter.getName() + ": " + waiter.getState());
        for (StackTraceElement frame : waiter.getStackTrace()) {
            System.out.println("  at " + frame);
        }

        holder.join();
        waiter.join();
    }
}
```

**Observed during validation:** `lock-waiter` reached the `BLOCKED` state, and its
trace pointed to the `synchronized` statement. After `lock-holder` woke and exited
its synchronized block, the waiter acquired the lock and the program terminated.

The polling loop is acceptable for stabilising this experiment, but it would be a poor synchronisation mechanism in production code.

For an external view, extend the sleep to 30 seconds. While the program is running, open another terminal:

```bash
jcmd -l
jcmd <process-id> Thread.print
```

Replace `<process-id>` with the identifier that `jcmd -l` reports for `BlockedThreadDemo`.

**Explain:**

1. What does the waiter's trace tell you?
2. What additional fact do you need from the holder's trace?
3. Why is `BLOCKED` not by itself evidence of deadlock?
4. How would moving the slow operation outside the synchronized block change the dependency?

### Experiment 5: Compare Java and native bounds failures

**Question:** How does a memory-safe boundary change the failure mode?

Begin on the memory-safe side:

```java
public final class JavaBoundsDemo {
    public static void main(String[] args) {
        int[] values = { 10, 20, 30, 40 };
        values[4] = 99;
    }
}
```

```bash
javac JavaBoundsDemo.java
java JavaBoundsDemo
```

**Observed during validation:** Java threw `ArrayIndexOutOfBoundsException` at the
invalid access and printed a source-level trace.

When a C compiler with AddressSanitizer is available, compare this small native
program:

```c
#include <stdio.h>

int main(void) {
    int values[4] = { 10, 20, 30, 40 };
    values[4] = 99;
    printf("%d\n", values[0]);
    return 0;
}
```

With Clang, a typical command is:

```bash
cc -O0 -g -fsanitize=address -fno-omit-frame-pointer \
   bounds_demo.c -o bounds_demo
./bounds_demo
```

**Observed during validation:** Clang with AddressSanitizer reported a stack-buffer
overflow and terminated the process with diagnostic information. A platform without
AddressSanitizer cannot reproduce that diagnostic with this command.

Without a sanitizer, C does not promise a particular result. The program has undefined behaviour: it might appear to continue, crash, or behave differently after an unrelated change. Do not infer safety from one run that appears successful.

This experiment demonstrates an invalid write; it does not construct an exploit.

**Explain:**

1. Which component detects the Java failure?
2. Which component detects the instrumented C failure?
3. What guarantee remains if you compile the C program without instrumentation?
4. Why is a deterministic exception easier to test and debug than undefined behaviour?

### Experiment 6: Look for compilation and inlining

**Question:** Can you observe a JVM changing its execution strategy?

Invoke a method often enough that the just-in-time compiler may optimise it:

```java
public final class HotMethodDemo {
    static int adjust(int value) {
        return value * 2 + 1;
    }

    public static void main(String[] args) {
        long total = 0;
        for (int i = 0; i < 10_000_000; i++) {
            total += adjust(i);
        }
        System.out.println(total);
    }
}
```

On the OpenJDK HotSpot JVM, try:

```bash
javac HotMethodDemo.java
java -XX:+PrintCompilation HotMethodDemo
```

For more detail, HotSpot also provides diagnostic inlining output:

```bash
java -XX:+UnlockDiagnosticVMOptions \
     -XX:+PrintCompilation \
     -XX:+PrintInlining \
     HotMethodDemo
```

These `-XX` options are implementation-specific. Another JVM may reject them or provide different diagnostic facilities. The output is verbose; search for `HotMethodDemo` rather than attempting to understand every compilation event.

**Observed during validation:** HotSpot listed `HotMethodDemo` methods in the
compilation log and reported an inlining decision for `adjust`. HotSpot does not
guarantee the same decision on another run or implementation.

Change `adjust` by making it larger, adding branches, or calling another method. Run the experiment again.

**Explain:**

1. Which results are Java guarantees and which are HotSpot observations?
2. If HotSpot inlines `adjust`, then why can an exception trace still describe
   logical Java methods?
3. Why should ordinary application correctness never depend on whether the JVM inlines a method?

## Summary of the Experiments

Bytecode uses local slots and an operand stack, calls cross frame boundaries, and the
JVM resolves symbolic references before using them. A JVM may optimise physical
execution while preserving Java-level semantics.

Stack depth depends on an implementation and a particular run. Suppressed exceptions
follow language semantics. Thread stacks expose cross-thread dependencies only when
we examine them together. Native out-of-bounds writes follow C's undefined-behaviour
rules rather than Java's exception guarantees.

Most debugging tasks do not require these details. Use them when the evidence points
to bytecode, optimisation, thread interaction, or native memory, and keep
implementation observations separate from specification guarantees.

## References

- Alexander Pope, [“An Essay on Criticism”](https://www.gutenberg.org/cache/epub/7409/pg7409-images.html)
- [The Java Virtual Machine Specification, Chapter 2](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-2.html)
- [The Java Virtual Machine Specification, §2.6: Frames](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-2.html#jvms-2.6)
- [The Java Virtual Machine Specification, §6.5: Invocation instructions](https://docs.oracle.com/javase/specs/jvms/se25/html/jvms-6.html)
- [`javap` documentation for JDK 25](https://docs.oracle.com/en/java/javase/25/docs/specs/man/javap.html)
- [`jcmd` documentation for JDK 25](https://docs.oracle.com/en/java/javase/25/docs/specs/man/jcmd.html)
- [`Throwable.getSuppressed()` application programming interface (API) documentation](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Throwable.html#getSuppressed())
- [Common Weakness Enumeration (CWE) 121: Stack-based Buffer Overflow](https://cwe.mitre.org/data/definitions/121.html)
- [CWE 787: Out-of-bounds Write](https://cwe.mitre.org/data/definitions/787.html)
