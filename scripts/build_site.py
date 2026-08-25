#!/usr/bin/env python3
"""Build the complete CPEN 221 static site from the revised Markdown chapters."""

from __future__ import annotations

from hashlib import sha256
from html import escape
from pathlib import Path
import os
import re
import shutil
import subprocess

from site_contract import (
    CHAPTERS,
    CHAPTERS_ROOT,
    COURSE_ROOT,
    Chapter,
    LANG,
    PANDOC_ARGUMENTS,
    PANDOC_VERSION,
    PUBLISHED_SOURCES,
    SITE_ROOT,
    installed_pandoc_version,
    provenance_comments,
    source_root,
)


def require_pinned_pandoc() -> None:
    """Fail unless the pinned pandoc is in use, because layout can change with it."""
    observed = installed_pandoc_version()
    if observed == PANDOC_VERSION:
        return
    if os.environ.get("CPEN221_ALLOW_PANDOC_MISMATCH") == "1":
        print(
            f"Warning: building with pandoc {observed}, not the pinned "
            f"{PANDOC_VERSION}."
        )
        return
    raise SystemExit(
        f"This site is pinned to pandoc {PANDOC_VERSION} but pandoc {observed} is "
        f"installed. Install the pinned version, or set "
        f"CPEN221_ALLOW_PANDOC_MISMATCH=1 to build anyway."
    )


def run_pandoc(markdown: str) -> str:
    try:
        result = subprocess.run(
            ["pandoc", *PANDOC_ARGUMENTS],
            input=markdown,
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as error:
        raise SystemExit(
            f"Pandoc {PANDOC_VERSION} is required to build the chapter pages"
        ) from error
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr) from error
    return result.stdout.strip()


def plain_text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


def rewrite_markdown_links(markdown: str) -> str:
    for chapter in CHAPTERS:
        markdown = markdown.replace(
            f"]({chapter.source})", f"](../{chapter.slug}/)"
        )
    return markdown


def transform_body(body: str, chapter: Chapter) -> tuple[str, list[tuple[str, str, str]]]:
    body = re.sub(
        r"<blockquote>(?=\s*<p>.*?</p>\s*<p><cite>)",
        '<blockquote class="epigraph">',
        body,
        count=1,
        flags=re.DOTALL,
    )
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
        <option value="plex">IBM Plex Serif + Sans + Mono</option>
        <option value="google-sans">Google Sans Flex + Code</option>
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
        f"{'Supplemental: ' if following.optional else ''}{escape(following.title)} →</a>"
        if following
        else '<a class="next" href="../../">Return to contents ↑</a>'
    )
    optional_kicker = (
        '        <p class="optional-kicker">Supplemental reading</p>\n'
        if chapter.optional
        else ""
    )

    return f"""<!doctype html>
<html lang="{LANG}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{escape(chapter.description)}">
  <title>{escape(chapter.title)} · CPEN 221 Readings</title>
  <link rel="stylesheet" href="../../assets/fonts/fonts.css">
  <link rel="stylesheet" href="../../assets/css/site.css">
  <script src="../../assets/js/typeface-switcher.js"></script>
</head>
<body id="top">
  {provenance_comments(escape(chapter.source), digest)}
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
      </header>

{body}

      <p class="chapter-examples"><a href="../../examples/{escape(chapter.slug)}/">Java examples for this reading →</a></p>

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
    # The labs archive is hand-maintained under labs/ rather than generated from
    # Markdown. The contents page links to it only when it is present, so a rebuild
    # neither invents the link nor discards it.
    has_labs = (SITE_ROOT / "labs" / "index.html").is_file()
    labs_nav_item = (
        '\n        <li><a href="labs/"><small>Lab</small>'
        "<span>Laboratory activities</span></a></li>"
        if has_labs
        else ""
    )
    labs_section = (
        """
      <section class="home-labs" aria-labelledby="labs-heading">
        <h2 id="labs-heading">Laboratory activities</h2>
        <p><a href="labs/">Browse the 2025 lab archive \u2192</a></p>
      </section>
"""
        if has_labs
        else ""
    )
    core_items = []
    optional_items = []
    for chapter in CHAPTERS:
        optional_label = (
            '                <span class="optional-label">Supplemental reading</span>\n'
            if chapter.optional
            else ""
        )
        item = f"""            <li>
              <span class="num">{escape(chapter.number)}</span>
              <div>
{optional_label}                <strong><a href="chapters/{chapter.slug}/">{escape(chapter.title)}</a></strong>
                <p>{escape(chapter.description)}</p>
              </div>
            </li>"""
        (optional_items if chapter.optional else core_items).append(item)
    core = "\n".join(core_items)
    optional = "\n".join(optional_items)
    return f"""<!doctype html>
<html lang="{LANG}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Revised CPEN 221 Software Construction readings for Fall 2026.">
  <title>CPEN 221 Readings · Software Construction</title>
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
      <p class="part-label">Fall 2026 readings</p>
      <h2><a href="#top" aria-current="page">Contents</a></h2>
      <ul>
        <li><a href="chapters/engineering-reliable-software/"><small>1</small><span>Begin the core readings</span></a></li>
        <li><a href="#further-exploration"><small>+</small><span>Supplemental readings</span></a></li>{labs_nav_item}
      </ul>
      <div class="prev-next">
        <a href="#core-heading">Readings</a>
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
        <p class="deck">How do we build software that is correct, that we can reason about, and is designed to evolve over time?</p>
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
          <h2 id="extra-heading">Supplemental readings</h2>
          <ol class="contents-list">
{optional}
          </ol>
        </section>
      </div>
{labs_section}
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
    legacy_projects = ("chapters-01-04", "chapters-05-06", "chapters-07-13")
    for project_name in legacy_projects:
        target = SITE_ROOT / "examples" / project_name
        if target.exists():
            shutil.rmtree(target)

    for chapter in CHAPTERS:
        if chapter.optional:
            continue
        project_name = chapter.slug
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
<html lang="{LANG}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Downloadable Java sources for {escape(title)}.">
  <title>{escape(title)} · CPEN 221 Readings</title>
  <link rel="stylesheet" href="../../assets/fonts/fonts.css">
  <link rel="stylesheet" href="../../assets/css/site.css">
</head>
<body>
  <main class="page">
    <article class="chapter example-index">
      <header class="chapter-header">
        <p class="optional-kicker">Downloadable Java project</p>
        <h1>{escape(title)}</h1>
        <p class="deck">Complete sources and tests used by the revised readings.</p>
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
    require_pinned_pandoc()
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

    CHAPTERS_ROOT.mkdir(exist_ok=True)

    for index, (chapter, body, sections, digest) in enumerate(rendered):
        target = CHAPTERS_ROOT / chapter.slug
        target.mkdir(exist_ok=True)
        previous = CHAPTERS[index - 1] if index > 0 else None
        following = CHAPTERS[index + 1] if index + 1 < len(CHAPTERS) else None
        (target / "index.html").write_text(
            chapter_page(chapter, body, sections, previous, following, digest),
            encoding="utf-8",
        )

    (SITE_ROOT / "index.html").write_text(contents_page(), encoding="utf-8")

    example_pages = {
        chapter.slug: (
            f"Chapter {chapter.number}: {chapter.title} examples"
            if not chapter.optional
            else f"{chapter.title} examples"
        )
        for chapter in CHAPTERS
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
