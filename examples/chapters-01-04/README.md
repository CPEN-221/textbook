# Chapters 1–4 companion project

This project contains the complete executable versions of the Java excerpts and
JUnit tests used in the first four revised CPEN 221 chapters.

Requirements:

- JDK 25
- the included Gradle wrapper

Run the validation suite with:

```bash
./gradlew test
```

The build requests a Java 25 toolchain, enables Java assertions during tests, and
compiles with all `javac` lint warnings enabled.

