#!/usr/bin/env python3
"""Build the complete CPEN 221 static site from the revised Markdown chapters."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html import escape
from pathlib import Path
import re
import shutil
import subprocess


SITE_ROOT = Path(__file__).resolve().parent.parent
COURSE_ROOT = SITE_ROOT.parent
PUBLISHED_SOURCES = SITE_ROOT / "sources"


@dataclass(frozen=True)
class Chapter:
    source: str
    slug: str
    number: str
    title: str
    description: str
    deck: str
    part: str
    reading_time: str
    optional: bool = False


CHAPTERS = (
    Chapter(
        "chapter-01-engineering-reliable-software.md",
        "engineering-reliable-software",
        "1",
        "Engineering Reliable Software",
        "Build a short Java feedback loop around an observed transit-system failure.",
        "Correctness begins with a failure we can reproduce, inspect, and preserve as evidence.",
        "Foundations",
        "About 15 minutes",
    ),
    Chapter(
        "chapter-02-types-and-specifications.md",
        "types-and-specifications",
        "2",
        "Types and Specifications",
        "Use domain types and behavioural contracts to state what transit software means.",
        "Types rule out meaningless combinations; specifications divide responsibility between clients and implementations.",
        "Foundations",
        "About 15 minutes",
    ),
    Chapter(
        "chapter-03-exceptions-testing-and-evidence.md",
        "exceptions-testing-and-evidence",
        "3",
        "Exceptions, Testing, and Evidence",
        "Design failure paths and derive useful tests from a transit-feed contract.",
        "Exceptions name failed obligations, while tests turn specifications into bounded evidence.",
        "Foundations",
        "About 20 minutes",
    ),
    Chapter(
        "chapter-04-mutability-aliasing-and-debugging.md",
        "mutability-aliasing-and-debugging",
        "4",
        "Mutability, Aliasing, and Debugging",
        "Follow references, close representation leaks, and debug mutable state with evidence.",
        "A reference can carry a mutation farther than the code that performed it.",
        "State and abstraction",
        "About 20 minutes",
    ),
    Chapter(
        "chapter-05-adts-and-representation-independence.md",
        "adts-and-representation-independence",
        "5",
        "ADTs and Representation Independence",
        "Design an immutable transit-network ADT whose clients do not depend on its data structures.",
        "A useful abstraction lets clients speak about stops and connections instead of maps and sets.",
        "State and abstraction",
        "About 20 minutes",
    ),
    Chapter(
        "chapter-06-representation-invariants-and-abstraction-functions.md",
        "representation-invariants-and-abstraction-functions",
        "6",
        "Representation Invariants and Abstraction Functions",
        "Connect concrete transit-network fields to valid abstract graph values.",
        "The abstraction function states what a representation means; the invariant states which representations may occur.",
        "State and abstraction",
        "About 20 minutes",
    ),
    Chapter(
        "chapter-12-how-java-runs.md",
        "how-java-runs",
        "12",
        "How a Java Program Runs",
        "Trace Java calls, frames, recursion, exceptions, and shared reachable objects.",
        "A call-stack model explains method calls and failures without pretending to be a photograph of memory.",
        "The running program",
        "About 20 minutes",
    ),
    Chapter(
        "optional-beyond-the-java-call-stack.md",
        "beyond-java-call-stack",
        "+",
        "Beyond the Java Call Stack",
        "Investigate bytecode, optimized execution, thread dumps, and native stack safety.",
        "Open the frame and compare Java guarantees with observations from bytecode, HotSpot, and native code.",
        "Optional deep dive",
        "About 35 minutes",
        optional=True,
    ),
)


def source_root() -> Path:
    course_sources = COURSE_ROOT / "notes" / "revised"
    if all((course_sources / chapter.source).is_file() for chapter in CHAPTERS):
        return course_sources
    if all((PUBLISHED_SOURCES / chapter.source).is_file() for chapter in CHAPTERS):
        return PUBLISHED_SOURCES
    raise SystemExit("Cannot find the complete revised chapter source set")


def run_pandoc(markdown: str) -> str:
    try:
        result = subprocess.run(
            [
                "pandoc",
                "--from=gfm",
                "--to=html5",
                "--wrap=none",
                "--syntax-highlighting=none",
            ],
            input=markdown,
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as error:
        raise SystemExit("Pandoc is required to build the chapter pages") from error
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr) from error
    return result.stdout.strip()


def plain_text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


def rewrite_markdown_links(markdown: str) -> str:
    replacements = {
        "chapter-12-how-java-runs.md": "../how-java-runs/",
        "optional-beyond-the-java-call-stack.md": "../beyond-java-call-stack/",
    }
    for old, new in replacements.items():
        markdown = markdown.replace(f"]({old})", f"]({new})")
    return markdown


def transform_body(body: str, chapter: Chapter) -> tuple[str, list[tuple[str, str, str]]]:
    body = re.sub(
        r"<p>(<img\s+[^>]+\s*/>)</p>\n<p><em>(Figure\s+.*?)</em></p>",
        r'<figure class="chapter-figure">\1<figcaption>\2</figcaption></figure>',
        body,
        flags=re.DOTALL,
    )
    body = re.sub(
        r"(<pre(?:\s+class=\"[^\"]+\")?><code>.*?</code></pre>)",
        r'<div class="code-block">\1</div>',
        body,
        flags=re.DOTALL,
    )
    body = re.sub(
        r"<blockquote>\s*(<p><strong>Design principle:)",
        r'<blockquote class="design-note">\1',
        body,
    )

    outcome_pattern = re.compile(
        r"<p>By the end(?: of this chapter)?, you should be able to:</p>\n(<ul>.*?</ul>)",
        flags=re.DOTALL,
    )
    body = outcome_pattern.sub(
        lambda match: (
            '<section class="chapter-note" aria-labelledby="learning-outcomes">'
            '<h2 id="learning-outcomes">By the end of this chapter</h2>'
            f"{match.group(1)}</section>"
        ),
        body,
        count=1,
    )

    sections: list[tuple[str, str, str]] = []

    def heading_replacement(match: re.Match[str]) -> str:
        level, identifier, content = match.groups()
        visible = plain_text(content)
        local_number = ""
        numeric = re.match(r"^(\d+)\.\s+(.*)$", visible)
        if numeric:
            local_number = numeric.group(1)
            prefix = re.compile(r"^\d+\.\s+")
            content = prefix.sub("", content, count=1)
            visible = numeric.group(2)
        display_number = ""
        if local_number and level == "2":
            display_number = (
                f"+.{local_number}"
                if chapter.optional
                else f"{chapter.number}.{local_number}"
            )
        if level == "2" and identifier != "learning-outcomes":
            sections.append((identifier, display_number or "§", visible))
        number_html = (
            f'<span class="section-number">{escape(display_number)}</span>'
            if display_number
            else ""
        )
        return (
            f'<h{level} id="{identifier}"><a href="#{identifier}">'
            f"{number_html}{content}</a></h{level}>"
        )

    body = re.sub(
        r'<h([23]) id="([^"]+)">(.*?)</h\1>',
        heading_replacement,
        body,
        flags=re.DOTALL,
    )
    return body, sections


def typeface_tools(prefix: str) -> str:
    return f"""  <div class="typeface-tools">
    <label>
      <span>Reading type</span>
      <select data-typeface-picker aria-label="Reading typeface combination">
        <option value="literata">Literata + IBM Plex Sans</option>
        <option value="newsreader">Newsreader + Public Sans</option>
        <option value="source">Source Serif 4 + Source Sans 3</option>
        <option value="fraunces">Fraunces heads + Literata text</option>
      </select>
    </label>
  </div>"""


def chapter_page(
    chapter: Chapter,
    body: str,
    sections: list[tuple[str, str, str]],
    previous: Chapter | None,
    following: Chapter | None,
    digest: str,
) -> str:
    nav_items = "\n".join(
        "        <li>"
        f'<a href="#{escape(identifier)}"><small>{escape(number)}</small>'
        f"<span>{escape(title)}</span></a></li>"
        for identifier, number, title in sections
    )
    previous_link = (
        f'<a href="../{previous.slug}/">← Previous</a>'
        if previous
        else '<a href="../../">← Contents</a>'
    )
    next_link = (
        f'<a href="../{following.slug}/">Next →</a>'
        if following
        else '<a href="../../">Contents ↑</a>'
    )
    mobile_previous = f"../{previous.slug}/" if previous else "../../"
    mobile_previous_label = previous.title if previous else "contents"
    mobile_next = f"../{following.slug}/" if following else "../../"
    mobile_next_label = following.title if following else "contents"
    footer_next = (
        f'<a class="next" href="../{following.slug}/">'
        f"{'Optional: ' if following.optional else ''}{escape(following.title)} →</a>"
        if following
        else '<a class="next" href="../../">Return to contents ↑</a>'
    )
    optional_kicker = (
        '        <p class="optional-kicker">Optional deep dive · Not required later</p>\n'
        if chapter.optional
        else ""
    )
    kind = "Optional reading" if chapter.optional else "Core reading"
    source_href = f"../../sources/{chapter.source}"

    return f"""<!doctype html>
<html lang="en-CA">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{escape(chapter.description)}">
  <title>{escape(chapter.title)} · CPEN 221 Notes</title>
  <link rel="stylesheet" href="../../assets/fonts/fonts.css">
  <link rel="stylesheet" href="../../assets/css/site.css">
  <script src="../../assets/js/typeface-switcher.js"></script>
</head>
<body id="top">
  <!-- source-sha256: {digest} -->
  <a class="skip-link" href="#chapter-content">Skip to chapter content</a>

  <nav class="book-nav" aria-label="Chapter navigation">
    <a class="wordmark" href="../../">
      <strong>CPEN 221</strong>
      <span>Software Construction</span>
    </a>
    <div class="nav-contents">
      <p class="part-label">{escape(chapter.part)}</p>
      <h2><a href="#top" aria-current="page">{escape(chapter.title)} <small>{escape(chapter.number)}</small></a></h2>
      <ul>
{nav_items}
      </ul>
      <div class="prev-next">
        {previous_link}
        <a href="../../">Up</a>
        {next_link}
      </div>
    </div>
  </nav>

  <nav class="book-nav-mobile" aria-label="Compact chapter navigation">
    <a class="mobile-arrow" href="{mobile_previous}" aria-label="Previous: {escape(mobile_previous_label)}">←</a>
    <a class="mobile-title" href="../../">CPEN 221</a>
    <a class="mobile-arrow" href="{mobile_next}" aria-label="Next: {escape(mobile_next_label)}">{'→' if following else '↑'}</a>
  </nav>

{typeface_tools('../..')}

  <main id="chapter-content" class="page">
    <article class="chapter">
      <div class="chapter-number" aria-hidden="true">{escape(chapter.number)}</div>
      <header class="chapter-header">
{optional_kicker}        <h1>{escape(chapter.title)}</h1>
        <p class="deck">{escape(chapter.deck)}</p>
        <ul class="chapter-meta" aria-label="Chapter information">
          <li>{kind}</li>
          <li>{escape(chapter.reading_time)}</li>
          <li>Java 25</li>
          <li><a href="{source_href}">Markdown source</a></li>
        </ul>
      </header>

{body}

      <footer class="book-footer">
        {footer_next}
        CPEN 221 · Software Construction I · Fall 2026
      </footer>
    </article>
  </main>
</body>
</html>
"""


def contents_page() -> str:
    core_items = []
    optional_items = []
    for chapter in CHAPTERS:
        item = f"""            <li>
              <span class="num">{escape(chapter.number)}</span>
              <div>
                {('<span class="optional-label">Optional deep dive</span>' if chapter.optional else '')}
                <strong><a href="chapters/{chapter.slug}/">{escape(chapter.title)}</a></strong>
                <p>{escape(chapter.description)}</p>
              </div>
            </li>"""
        (optional_items if chapter.optional else core_items).append(item)
    core = "\n".join(core_items)
    optional = "\n".join(optional_items)
    return f"""<!doctype html>
<html lang="en-CA">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Revised CPEN 221 Software Construction notes for Fall 2026.">
  <title>CPEN 221 Notes · Software Construction</title>
  <link rel="stylesheet" href="assets/fonts/fonts.css">
  <link rel="stylesheet" href="assets/css/site.css">
  <script src="assets/js/typeface-switcher.js"></script>
</head>
<body id="top">
  <a class="skip-link" href="#main-content">Skip to the book</a>

  <nav class="book-nav" aria-label="Book navigation">
    <a class="wordmark" href="./" aria-current="page">
      <strong>CPEN 221</strong>
      <span>Software Construction</span>
    </a>
    <div class="nav-contents">
      <p class="part-label">Fall 2026 notes</p>
      <h2><a href="#top" aria-current="page">Contents</a></h2>
      <ul>
        <li><a href="chapters/engineering-reliable-software/"><small>1</small><span>Begin the core readings</span></a></li>
        <li><a href="#further-exploration"><small>+</small><span>Further exploration</span></a></li>
      </ul>
      <div class="prev-next">
        <a href="#about">About</a>
        <a href="chapters/engineering-reliable-software/">Read →</a>
      </div>
    </div>
  </nav>

  <nav class="book-nav-mobile" aria-label="Compact book navigation">
    <span class="mobile-arrow" aria-hidden="true">❧</span>
    <a class="mobile-title" href="./" aria-current="page">CPEN 221</a>
    <a class="mobile-arrow" href="chapters/engineering-reliable-software/" aria-label="Next: Engineering Reliable Software">→</a>
  </nav>

{typeface_tools('.')}

  <main id="main-content" class="page">
    <article class="contents-page">
      <header class="contents-header">
        <p class="kicker">Software Construction I · Fall 2026</p>
        <h1>CPEN 221</h1>
        <p class="deck">Build programs we can reason about, test, and change without losing the plot.</p>
      </header>

      <p>Software construction begins after the syntax starts making sense. These chapters connect Java programs to the contracts, representations, tests, and design arguments that make software dependable.</p>

      <div class="ornament" aria-hidden="true">❧</div>

      <div class="contents-group contents-group-complete">
        <section aria-labelledby="core-heading">
          <h2 id="core-heading">Core readings</h2>
          <ol class="contents-list">
{core}
          </ol>
        </section>

        <section id="further-exploration" aria-labelledby="extra-heading">
          <h2 id="extra-heading">Further exploration</h2>
          <ol class="contents-list">
{optional}
          </ol>
        </section>
      </div>

      <aside id="about" class="prototype-note" aria-labelledby="about-heading">
        <h2 id="about-heading">About these notes</h2>
        <p>These are the current Fall 2026 readings. Each chapter includes its complete prose, practice questions, sources, and provenance. The linked Java projects target Java 25 and are checked before publication.</p>
      </aside>

      <footer class="book-footer">
        <a class="next" href="chapters/engineering-reliable-software/">Begin Chapter 1 →</a>
        CPEN 221 · University of British Columbia · Fall 2026
      </footer>
    </article>
  </main>
</body>
</html>
"""


def copy_publication_assets() -> None:
    external_figures = COURSE_ROOT / "assets" / "diagrams" / "rendered"
    published_figures = SITE_ROOT / "assets" / "diagrams" / "rendered"
    if external_figures.is_dir():
        if published_figures.exists():
            shutil.rmtree(published_figures)
        shutil.copytree(external_figures, published_figures)

    external_examples = COURSE_ROOT / "examples"
    for project_name in ("chapters-01-04", "chapters-05-06"):
        source = external_examples / project_name
        target = SITE_ROOT / "examples" / project_name
        if source.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(
                source,
                target,
                ignore=shutil.ignore_patterns(".gradle", "build", ".DS_Store"),
            )


def example_index(project_name: str, title: str) -> str:
    project = SITE_ROOT / "examples" / project_name
    links = []
    for path in sorted(project.rglob("*")):
        if path.is_file() and path.name != "index.html":
            relative = path.relative_to(project).as_posix()
            links.append(f'<li><a href="{escape(relative)}">{escape(relative)}</a></li>')
    return f"""<!doctype html>
<html lang="en-CA">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Downloadable Java sources for {escape(title)}.">
  <title>{escape(title)} · CPEN 221 Notes</title>
  <link rel="stylesheet" href="../../assets/fonts/fonts.css">
  <link rel="stylesheet" href="../../assets/css/site.css">
</head>
<body>
  <main class="page">
    <article class="chapter example-index">
      <header class="chapter-header">
        <p class="optional-kicker">Downloadable Java project</p>
        <h1>{escape(title)}</h1>
        <p class="deck">Complete sources and tests used by the revised notes.</p>
      </header>
      <p><a href="../../">← Return to the book contents</a></p>
      <ul class="file-list">{''.join(links)}</ul>
      <footer class="book-footer">CPEN 221 · Software Construction I · Fall 2026</footer>
    </article>
  </main>
</body>
</html>
"""


def build() -> None:
    sources = source_root()
    PUBLISHED_SOURCES.mkdir(parents=True, exist_ok=True)
    copy_publication_assets()

    rendered: list[tuple[Chapter, str, list[tuple[str, str, str]], str]] = []
    for chapter in CHAPTERS:
        source_path = sources / chapter.source
        markdown = source_path.read_text(encoding="utf-8")
        if sources != PUBLISHED_SOURCES:
            (PUBLISHED_SOURCES / chapter.source).write_text(markdown, encoding="utf-8")
        digest = sha256(markdown.encode("utf-8")).hexdigest()
        markdown_without_title = markdown.split("\n", 1)[1].lstrip()
        markdown_without_title = rewrite_markdown_links(markdown_without_title)
        body, sections = transform_body(run_pandoc(markdown_without_title), chapter)
        rendered.append((chapter, body, sections, digest))

    chapters_root = SITE_ROOT / "chapters"
    if chapters_root.exists():
        shutil.rmtree(chapters_root)
    chapters_root.mkdir()

    for index, (chapter, body, sections, digest) in enumerate(rendered):
        target = chapters_root / chapter.slug
        target.mkdir()
        previous = CHAPTERS[index - 1] if index > 0 else None
        following = CHAPTERS[index + 1] if index + 1 < len(CHAPTERS) else None
        (target / "index.html").write_text(
            chapter_page(chapter, body, sections, previous, following, digest),
            encoding="utf-8",
        )

    (SITE_ROOT / "index.html").write_text(contents_page(), encoding="utf-8")

    example_pages = {
        "chapters-01-04": "Chapters 1–4 companion project",
        "chapters-05-06": "Chapters 5–6 companion project",
    }
    for project_name, title in example_pages.items():
        project = SITE_ROOT / "examples" / project_name
        if project.is_dir():
            (project / "index.html").write_text(
                example_index(project_name, title), encoding="utf-8"
            )

    print(f"Built {len(CHAPTERS)} complete chapter pages and the contents page.")


if __name__ == "__main__":
    build()
