# Chapters 5–6 companion project

This project contains the complete executable versions of the Java excerpts and
JUnit tests used in Chapters 5 and 6 of the revised CPEN 221 notes.

Requirements:

- JDK 25
- the Gradle wrapper in `../chapters-01-04/`

From the repository root, run the validation suite with:

```bash
examples/chapters-01-04/gradlew -p examples/chapters-05-06 test
```

Run the small observation program with:

```bash
examples/chapters-01-04/gradlew -p examples/chapters-05-06 runNetworkDemo
```

The build requests a Java 25 toolchain, enables Java assertions during tests, and
compiles with all `javac` lint warnings enabled.

