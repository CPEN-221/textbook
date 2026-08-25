# Chapter 1 | Engineering Reliable Software

The arrival board says the next bus is **−3 minutes away**.

The computing system executed the arithmetic operations correctly. The program
subtracted the current time from a prediction, converted the result to minutes, and
printed the number. And someone standing in the Vancouver rain saw something that
did not make sense.

The program ran, but its output was not useful. Software construction requires code
that expresses the right problem, rejects bad states, survives change, and gives us
enough evidence to find mistakes.

We will start by building one small part of a transit information system and using
it to establish the working loop for the course.

By the end, you should be able to:

- distinguish source code, a build, a test, and a running program;
- explain what *correct*, *comprehensible*, and *changeable* mean in a concrete case;
- use Java 25, Gradle, JUnit, and Git as one short feedback loop;
- turn an observed failure into a regression test;
- treat generated code as an implementation to inspect, not as evidence of
  correctness.

## 1. A Program Is More Than Its Happy Path

Suppose our first requirement reads:

> Given the scheduled and predicted arrival times, describe a vehicle as early, on
> time, or late.

Here is a plausible implementation:

```java
package ca.ubc.ece.cpen221.transit;

public final class ArrivalStatus {
    private ArrivalStatus() { }

    public static String describe(int scheduledMinute, int predictedMinute) {
        int difference = predictedMinute - scheduledMinute;
        if (difference > 0) {
            return "LATE";
        }
        return "ON TIME";
    }
}
```

It compiles. It returns `"LATE"` when a bus is two minutes late. It also calls a bus
that is seven minutes early `"ON TIME"`. The code has no branch for an early arrival,
so no input can produce the missing answer.

This is not primarily a syntax problem. It is a mismatch among three things:

1. the behaviour we need;
2. the behaviour the implementation provides;
3. the evidence we collected before trusting it.

The course will keep returning to those three views. A **specification** states the
required behaviour. An **implementation** attempts to provide it. Tests, reviews,
static checks, and observations supply evidence about the attempt.

No one tool closes the triangle by itself.

## 2. What We Mean by Reliable

“Reliable software” is easy to say and too vague to guide a design. For this course,
we will evaluate our work along three recurring dimensions.

### Correct

Software is **correct with respect to a specification** when its behaviour satisfies
that specification. Correctness is not a glow that code acquires after enough
polishing. We need a stated obligation before the word has technical meaning.

If the specification says an arrival exactly on schedule is `ON_TIME`, then returning
that status is correct for that input. If the specification says nothing about early
arrivals, we have found a hole in the specification before we have found a bug in the
implementation.

### Comprehensible

Software is **comprehensible** when another person can form an accurate model of it
without reconstructing every detail. Names, types, small methods, specifications, and
tests all help. Comprehensibility matters because code spends much more time being
read, reviewed, debugged, and changed than being typed for the first time.

Compare `difference` with `x`, or `predictedMinute` with `b`. The longer names do not
make the calculation more sophisticated. They make its meaning available.

### Changeable

Software is **changeable** when we can alter one decision without surprising damage
elsewhere. Transit data supplies a steady stream of changes: a new route, a renamed
stop, an accessibility rule, a feed-format revision, or a different way to classify
lateness. Modules and specifications let us change a part while preserving the
promises on which clients rely.

These qualities reinforce one another. A precise contract makes code easier to test.
Focused code is easier to understand. An automated test suite makes a later change
safer. They can also compete: an abstraction may add complexity, or an exhaustive
check may cost too much to run in production. Engineering begins where slogans run
out and trade-offs need reasons.

## 3. The Course System

Across these notes we will grow a small system for Metro Vancouver transit
reliability and journey planning. We will work with frozen, invented examples so
that builds stay deterministic. Optional extensions can consume public GTFS data or
live updates later.

The domain will give us recurring objects with real design pressure:

- stop and route identifiers that must not be mixed;
- service times that can continue past midnight;
- arrival predictions that can be malformed or stale;
- feed snapshots that should not change under a client's feet;
- routing policies with different guarantees;
- network requests and caches that eventually introduce concurrency.

We are not trying to reproduce a production trip planner in thirteen readings. The
system is a teaching model, and we will say when it leaves out a production concern.
Its job is to make abstract ideas earn their keep.

## 4. The Build–Test–Inspect Loop

A modern Java project is not a pile of `.java` files followed by good intentions. It
has a repeatable process for turning sources into checked results.

![A source edit flows through compilation and tests to an observed result; failures
return the developer to the source while successful results can become a small Git
commit.](../../assets/diagrams/rendered/chapter-01/build-test-inspect-loop.svg)

*Figure 1.1: The course feedback loop. A failure is information that sends us back
around the loop; it is not a ceremonial red light at the end of the project.*

The companion project for Chapters 1–4 lives in
[`examples/chapters-01-04`](../../examples/chapters-01-04/). Its important pieces are:

```text
examples/chapters-01-04/
├── build.gradle.kts
├── settings.gradle.kts
└── src/
    ├── main/java/ca/ubc/ece/cpen221/transit/
    └── test/java/ca/ubc/ece/cpen221/transit/
```

**Gradle** describes and runs the build. The Java **toolchain** setting asks Gradle to
compile and test with Java 25. **JUnit** supplies the test model and assertions. The
Gradle **wrapper** pins a suitable Gradle version so that the same command works for
the whole team.

From the project directory, one command runs the tests:

```bash
./gradlew test
```

That command does several jobs. Gradle locates the source sets and dependencies,
invokes `javac`, runs the JUnit tests, and reports whether the build succeeded. Your
IDE may put a friendly green triangle over the same machinery. Learn the command as
well; it gives your laptop, a teammate's laptop, and continuous integration a common
entry point.

### Read the first failure

When a build fails, begin with the first relevant diagnostic rather than scrolling
to the bottom and negotiating with the stack trace as a whole.

- A **compilation failure** means Java could not accept the program as well-typed,
  syntactically valid source.
- A **test failure** means the program ran but a JUnit assertion observed a result
  different from the test's required result.
- A **test error** usually means the test encountered an exception or failed to set
  up its environment.

These categories suggest different questions. A missing semicolon does not need a
debugger. A wrong status at a boundary does not need a clean reinstall of the IDE.
Match the tool to the evidence.

## 5. Our First Regression Test

The missing `EARLY` branch deserves a test before it deserves a fix. Here is the
complete JUnit test class from the companion project:

```java
package ca.ubc.ece.cpen221.transit;

import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.Test;

class ArrivalStatusTest {
    @Test
    void classifiesEarlyArrival() {
        assertEquals("EARLY", ArrivalStatus.describe(600, 593));
    }

    @Test
    void classifiesOnTimeArrival() {
        assertEquals("ON TIME", ArrivalStatus.describe(600, 600));
    }

    @Test
    void classifiesLateArrival() {
        assertEquals("LATE", ArrivalStatus.describe(600, 602));
    }
}
```

The first test records the failure we observed. The other two pin down the boundaries
on either side. Now we can repair the implementation:

```java
public static String describe(int scheduledMinute, int predictedMinute) {
    if (predictedMinute < scheduledMinute) {
        return "EARLY";
    }
    if (predictedMinute > scheduledMinute) {
        return "LATE";
    }
    return "ON TIME";
}
```

Running `./gradlew test` now gives us an observation: all three tests pass. That is
better than saying they *should* pass, but it remains a bounded claim. We checked
three cases against a small contract. We did not prove the method correct for every
integer, and we certainly did not prove the transit system reliable.

We will design stronger tests in Chapter 3. For now, notice the shape of the work:
failure, executable example, focused change, fresh observation.

## 6. Git Records Decisions

The tests protect behaviour; Git records change. A **repository** stores a history of
snapshots called **commits**. A useful commit is a small, coherent claim: “classify
early arrivals and test all three cases,” not “stuff from Tuesday.”

A typical local cycle is:

```bash
git status
git diff
git add src/main src/test
git diff --staged
git commit -m "Classify early arrival predictions"
```

`git status` tells you which files differ from the current commit. `git diff` shows
the unstaged changes. `git add` selects content for the next commit; it does not send
anything to a server. `git diff --staged` gives you one last review of the proposed
snapshot. Only then does `git commit` add it to local history.

There are two details worth making habitual.

First, inspect before you record. Generated files, credentials, debug output, and an
unrelated half-finished experiment do not improve when packed into the same commit.

Second, run the tests on the content you intend to commit. A passing build from
twenty minutes ago is evidence about twenty-minutes-ago code.

Branches let us develop a change without moving the main line of work:

```bash
git switch -c classify-arrivals
```

A branch is a movable name for a commit, not a second copy of the entire project.
That model becomes useful when we discuss collaboration. For now, one branch, small
commits, and an honest `git status` are plenty.

> **Recovery note:** `git restore` can discard uncommitted work. That can be exactly
> what you want, but inspect the target and diff first. Version control is a safety
> system only for work that actually reached version control.

## 7. Short Feedback Changes How We Design

Builds, tests, and commits are often introduced as chores around “the real coding.”
That gets the dependency backward. A short feedback loop changes which designs are
practical.

If a method can be tested in isolation, we can explore an alternative quickly. If a
commit contains one idea, review can focus on that idea. If the build is reproducible,
we can distinguish a code failure from a teammate's private machine setup. The tools
shape the program by making some mistakes cheap to discover.

Our first design principle follows:

> **Design principle: shorten the distance between a decision and trustworthy
> feedback about that decision.**

This does not mean running every conceivable analysis after every keystroke. It means
matching the cost of feedback to the risk of the change. Compile often. Run focused
tests while developing. Run the full suite before sharing. Ask for human review when
the difficult question is whether the contract itself is sensible.

## 8. Generated Code Enters the Same Loop

An AI tool can produce an `ArrivalStatus` implementation in seconds. It can also
invent a threshold, omit an edge case, use an API that does not exist, or explain a
wrong answer with impressive posture.

The engineering workflow does not change according to who typed the code:

1. Write or inspect the specification.
2. Treat the generated implementation as untrusted input.
3. Compile it with warnings enabled.
4. derive tests from the contract, especially boundaries and failure cases;
5. review surprising API calls against authoritative documentation;
6. record what was generated and what you verified independently.

Generated code can reduce mechanical effort. It cannot decide what “correct” means
for our system unless we have already supplied that meaning. A fluent implementation
with no contract is merely a mystery wearing good variable names.

## 9. A Common Misconception: Green Means Correct

Passing tests mean that the tested executions produced the asserted observations.
That is valuable and precise. It is not the same as proving the software correct.

Our three tests do not establish that the integers are plausible service-day times.
They do not define whether a one-minute deviation should count as on time. They use
strings, so a client can mistype `"ON_TIME"`. They say nothing about stale
predictions. Some of those gaps belong in more tests; others call for better types or
a stronger specification.

The right response to a green build is neither distrust nor celebration without
limit. Say what the evidence supports: *these tests passed for this version in this
environment*. Then decide what risk remains.

## Try the Loop

Answer these before running code. Prediction turns the tool's output into evidence
about your model instead of screen weather.

### 1. Predict the status

For the repaired `describe` method, what does each call return?

```java
ArrivalStatus.describe(600, 599)
ArrivalStatus.describe(600, 600)
ArrivalStatus.describe(600, 601)
```

Which line of the method decides each answer?

### 2. Break a boundary

Change `predictedMinute < scheduledMinute` to
`predictedMinute <= scheduledMinute`. Which existing test should fail? What incorrect
behaviour would go unnoticed if that test were missing?

### 3. Classify the diagnostic

For each event, decide whether compilation, a test assertion, or a runtime exception
should reveal it first:

- the method name is misspelled;
- `describe(600, 590)` returns `"ON TIME"`;
- the program reads a missing configuration file;
- a test expected `"EARLY"` but observed `"LATE"`.

### 4. Design a commit

You changed the classification logic, reformatted twenty unrelated files, and added
a temporary log statement containing an API token. What belongs in the next commit?
Explain what you would do with each remaining change instead of listing Git commands.

### 5. Audit a generated answer

An AI-generated implementation treats arrivals within five minutes of schedule as
`ON TIME`. The prompt never mentioned a tolerance. Is the implementation wrong? What
must you establish before that question has an answer?

## Where We Have Arrived

Software construction connects an intended behaviour, an implementation, and
evidence. We want programs that are correct with respect to their contracts,
comprehensible to their maintainers, and changeable without collateral damage.

Java 25, Gradle, JUnit, and Git support one repeatable loop: edit, build, test,
inspect, and record. A short loop does more than save time. It lets us discover a
wrong assumption while the decision that caused it is still close at hand.

Our example still describes times with ordinary integers and statuses with ordinary
strings. The compiler cannot tell a scheduled time from a predicted time, or a route
identifier from a stop identifier. In the next chapter, we will give those concepts
types and contracts of their own.

## Sources and provenance

This chapter was written anew for the Fall 2026 CPEN 221 notes. It keeps the former
manuscript's course-wide goals of correctness, comprehensibility, and changeability,
but it does not reuse the old chapter's prose, historical incidents, images, or
worked examples. The transit example and Figure 1.1 are original CPEN 221 material.

Technical references:

- [Java SE 25 and JDK 25 documentation](https://docs.oracle.com/en/java/javase/25/docs/)
- [Gradle Java compatibility matrix](https://docs.gradle.org/current/userguide/compatibility.html)
- [JUnit 6 user guide](https://docs.junit.org/current/user-guide/)
- [Git reference](https://git-scm.com/docs)
- [General Transit Feed Specification overview](https://gtfs.org/getting-started/what-is-gtfs/)
