# CPEN 221 readings website

This repository publishes the Fall 2026 revision of the CPEN 221 Software
Construction I readings at <https://cpen-221.github.io/>.

The site is static and uses stable, unnumbered chapter URLs. It includes every
current revised chapter, the supplemental readings, original SVG figures, the
human-edited Markdown sources, and a Java 25 companion project for each core
chapter.

## Preview locally

From this repository root, run:

```bash
python3 -m http.server 8000
```

Then open <http://localhost:8000/>. Do not open the HTML files directly: serving
them over HTTP catches path errors that a `file:` preview can hide.

Before publishing, run the dependency-free site check and compile the downloadable
examples:

```bash
python3 scripts/check_site.py
javac -d /tmp/cpen221-example-classes \
  examples/how-java-runs/FrameDemo.java \
  examples/beyond-java-call-stack/BytecodeDemo.java
```

## Build the chapter pages

The committed HTML is generated from the Markdown under `sources/`. In the complete
course-materials workspace, the build uses `../notes/revised/` and refreshes the
published source copies, rendered diagrams, and companion projects at the same time.

The build requires Pandoc:

```bash
python3 scripts/build_site.py
```

Generated pages carry a SHA-256 digest of their Markdown source. The site checker
fails if a source changes without a corresponding rebuild.

## Validate before publishing

Run the structural and link checks:

```bash
python3 scripts/check_site.py
```

Run the Java 25 companion suites:

```bash
for project in examples/*; do
  if test -x "$project/gradlew"; then
    "$project/gradlew" -p "$project" --no-daemon test
  fi
done
```

The GitHub Actions workflow repeats those checks, compiles the standalone stack
examples, and publishes the repository as a GitHub Pages artifact after a successful
push to `main`.

## Layout

- `chapters/` contains the generated HTML pages.
- `sources/` contains the published Markdown source for each page.
- `assets/` contains the stylesheet, JavaScript, fonts, and static SVG figures.
- `examples/` contains one downloadable and testable Java project for each core
  chapter, plus the standalone examples for the supplemental readings.
- `scripts/build_site.py` performs the deterministic Markdown-to-HTML build.
- `scripts/check_site.py` checks links, fragments, page landmarks, image text,
  source freshness, and SVG metadata.

The visual direction adapts the book-like information architecture of
[*Crafting Interpreters*](https://craftinginterpreters.com/) without reusing its
logo, illustrations, font files, or stylesheet.
