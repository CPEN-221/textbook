#!/usr/bin/env python3
"""Build the public 2025 lab archive without publishing teaching-team guides."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html import escape, unescape
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import unquote, urlsplit


SITE_ROOT = Path(__file__).resolve().parent.parent
COURSE_ROOT = SITE_ROOT.parent
COURSE_LABS = COURSE_ROOT / "labs" / "2025"
PUBLISHED_LABS = SITE_ROOT / "lab-sources" / "2025"
LABS_ROOT = SITE_ROOT / "labs"
YEAR_ROOT = LABS_ROOT / "2025"
PANDOC_VERSION = "3.10.2"


@dataclass(frozen=True)
class Lab:
    source: str
    slug: str
    number: str
    title: str
    description: str


LABS = (
    Lab(
        "Lab 0: String Chopping.md",
        "string-chopping",
        "0",
        "String Chopping",
        "Develop an algorithm that isolates letters by repeatedly removing parts of a string.",
    ),
    Lab(
        "Lab 1: Problem Solving.md",
        "problem-solving",
        "1",
        "Problem Solving",
        "Practise iteration and problem decomposition with three short programming tasks.",
    ),
    Lab(
        "Lab 2: Datatypes and DNA.md",
        "datatypes-and-dna",
        "2",
        "Datatypes and DNA",
        "Implement a Java datatype for DNA sequences, codons, mass, and mutation.",
    ),
    Lab(
        "Lab 3: DNA Cut-and-Splice.md",
        "dna-cut-and-splice",
        "3",
        "DNA Cut-and-Splice",
        "Debug a provided DNA implementation and add a cut-and-splice operation.",
    ),
    Lab(
        "Lab 4: Abstract Algebra.md",
        "abstract-algebra",
        "4",
        "Abstract Algebra",
        "Implement and test operations that determine whether a finite table defines a group.",
    ),
    Lab(
        "Lab 5: ADTs (The JobManager) .md",
        "adts-and-job-manager",
        "5",
        "ADTs and the JobManager",
        "Design and implement an abstract data type for assigning jobs to robots.",
    ),
    Lab(
        "Lab 6: Representation Invariants (featuring JobManager) .md",
        "representation-invariants-and-job-manager",
        "6",
        "Representation Invariants and the JobManager",
        "State and check a representation invariant, then use it to locate implementation bugs.",
    ),
    Lab(
        "Lab 7: Interfaces + Subtypes + Rep Invariants.md",
        "interfaces-subtypes-and-representation-invariants",
        "7",
        "Interfaces, Subtypes, and Representation Invariants",
        "Extend the JobManager with robot subtypes, scheduling policies, records, and comparators.",
    ),
    Lab(
        "Lab 8: Streams and Lambdas.md",
        "streams-and-lambdas",
        "8",
        "Streams and Lambdas",
        "Use stream pipelines, optional values, lambdas, and functional interfaces.",
    ),
    Lab(
        "Lab 9: Evaluating Arithmetic Expressions.md",
        "evaluating-arithmetic-expressions",
        "9",
        "Evaluating Arithmetic Expressions",
        "Build infix and postfix evaluators and practise running and packaging Java applications.",
    ),
    Lab(
        "Lab 10: Client-Server Pattern and Text Document Processing.md",
        "client-server-and-text-processing",
        "10",
        "Client-Server Pattern and Text Processing",
        "Compute document metrics through a JSON client-server protocol and examine concurrency.",
    ),
    Lab(
        "Lab 11: Stable Marriages, Shared Memory and Concurrency.md",
        "stable-matching-and-concurrency",
        "11",
        "Stable Matching, Shared Memory, and Concurrency",
        "Complete a concurrent stable-matching implementation and reason about shared state.",
    ),
    Lab(
        "Programming Practice.md",
        "programming-practice",
        "+",
        "Programming Practice",
        "Links to the short programming exercises used alongside the 2025 labs.",
    ),
)


PUBLIC_ASSET_DIRECTORIES = (
    "Lab 2: Datatypes and DNA.assets",
    "Lab 3: DNA Cut-and-Splice.assets",
    "Lab 9: Evaluating Arithmetic Expressions.assets",
    "Lab 10: Client-Server Pattern and Text Document Processing.assets",
)


IMAGE_ALTS = {
    "Lab 2: Datatypes and DNA.assets/SEO-DNA-Images-Codons-2019-01-09-12-12-20.jpeg": (
        "A DNA sequence grouped into codons, its corresponding RNA codons, and the "
        "amino acids in the resulting protein chain."
    ),
    "Lab 3: DNA Cut-and-Splice.assets/Image.png": (
        "A DNA strand containing the EcoRI recognition sequence GAATTC, shown intact "
        "and cut between G and A."
    ),
    "Lab 3: DNA Cut-and-Splice.assets/Image (2).png": (
        "Two cut DNA fragments with complementary ends aligned to a DNA segment that "
        "will be inserted between them."
    ),
    "Lab 3: DNA Cut-and-Splice.assets/Image (3).png": (
        "The recombined DNA strand after the inserted segment joins the two original "
        "fragments."
    ),
    "Lab 9: Evaluating Arithmetic Expressions.assets/AST-JavaExample.png": (
        "An abstract syntax tree for three Java assignments, with the final expression "
        "representing result equals b times the difference a minus b, plus a."
    ),
    "Lab 10: Client-Server Pattern and Text Document Processing.assets/Image.png": (
        "A Dockerfile is built into a Docker image, which is then run as a Docker "
        "container."
    ),
}


def source_root() -> Path:
    if all((COURSE_LABS / lab.source).is_file() for lab in LABS):
        return COURSE_LABS
    if all((PUBLISHED_LABS / lab.source).is_file() for lab in LABS):
        return PUBLISHED_LABS
    raise SystemExit("Cannot find the complete public 2025 lab source set")


def require_pandoc() -> None:
    try:
        result = subprocess.run(
            ["pandoc", "--version"], text=True, capture_output=True, check=True
        )
    except FileNotFoundError as error:
        raise SystemExit(f"Pandoc {PANDOC_VERSION} is required to build the labs") from error
    first_line = result.stdout.splitlines()[0]
    if first_line != f"pandoc {PANDOC_VERSION}":
        raise SystemExit(
            f"The lab archive is pinned to pandoc {PANDOC_VERSION}; observed {first_line}"
        )


def normalize_markdown(markdown: str) -> str:
    """Remove export-only trailing spaces without changing the archived source."""
    return "\n".join(line.rstrip() for line in markdown.splitlines()) + "\n"


def sync_public_sources(sources: Path) -> None:
    if sources == PUBLISHED_LABS:
        return
    if PUBLISHED_LABS.exists():
        shutil.rmtree(PUBLISHED_LABS)
    PUBLISHED_LABS.mkdir(parents=True)
    for lab in LABS:
        markdown = (sources / lab.source).read_text(encoding="utf-8")
        (PUBLISHED_LABS / lab.source).write_text(
            normalize_markdown(markdown), encoding="utf-8"
        )
    for directory_name in PUBLIC_ASSET_DIRECTORIES:
        shutil.copytree(sources / directory_name, PUBLISHED_LABS / directory_name)


def rewrite_images(markdown: str) -> str:
    image_pattern = re.compile(
        r"!\[([^]]*)\]\((.+?\.(?:png|jpe?g|gif|svg))\)", re.IGNORECASE
    )

    def replace_image(match: re.Match[str]) -> str:
        existing_alt, reference = match.groups()
        parsed = urlsplit(reference)
        if parsed.scheme or parsed.netloc or reference.startswith("/"):
            return match.group(0)
        local_path = unquote(parsed.path)
        alt = IMAGE_ALTS.get(local_path, existing_alt)
        published_reference = f"../../../lab-sources/2025/{reference}"
        return f"![{alt}]({published_reference})"

    return image_pattern.sub(replace_image, markdown)


def run_pandoc(markdown: str) -> str:
    result = subprocess.run(
        [
            "pandoc",
            "--from=gfm+tex_math_dollars",
            "--to=html5",
            "--mathml",
            "--wrap=none",
            "--syntax-highlighting=none",
        ],
        input=markdown,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def plain_text(value: str) -> str:
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", value))).strip()


def transform_body(markdown: str, lab: Lab) -> tuple[str, list[tuple[str, str]]]:
    body_markdown = markdown.split("\n", 1)[1].lstrip()
    if lab.number == "0":
        body_markdown = body_markdown.replace("### Overview", "## Overview", 1)
    if lab.number == "1":
        body_markdown = body_markdown.replace("$d $", "$d$")
    body = run_pandoc(rewrite_images(body_markdown))
    body = re.sub(r"<h1(\s[^>]*)?>", r"<h2\1>", body)
    body = body.replace("</h1>", "</h2>")
    body = re.sub(r"<h4(\s[^>]*)?>", r"<h3\1>", body)
    body = body.replace("</h4>", "</h3>")
    body = re.sub(
        r"(<pre(?:\s+class=\"[^\"]+\")?><code>.*?</code></pre>)",
        r'<div class="code-block">\1</div>',
        body,
        flags=re.DOTALL,
    )
    body = body.replace("<blockquote>", '<div class="lab-callout">')
    body = body.replace("</blockquote>", "</div>")
    body = re.sub(r"<img\s", '<img loading="lazy" ', body)

    sections: list[tuple[str, str]] = []

    def heading_link(match: re.Match[str]) -> str:
        level, identifier, content = match.groups()
        if level == "2":
            sections.append((identifier, plain_text(content)))
        return f'<h{level} id="{identifier}"><a href="#{identifier}">{content}</a></h{level}>'

    body = re.sub(
        r'<h([23]) id="([^"]+)">(.*?)</h\1>',
        heading_link,
        body,
        flags=re.DOTALL,
    )
    return body, sections


def typeface_tools(prefix: str) -> str:
    return f"""  <div class="typeface-tools">
    <label>
      <span>Reading type</span>
      <select data-typeface-picker aria-label="Reading typeface combination">
        <option value="plex">IBM Plex Serif + IBM Plex Sans + IBM Plex Mono</option>
        <option value="google-sans">Google Sans Flex + Google Sans Code</option>
      </select>
    </label>
  </div>"""


def lab_page(
    lab: Lab,
    body: str,
    sections: list[tuple[str, str]],
    previous: Lab | None,
    following: Lab | None,
    digest: str,
) -> str:
    nav_items = "\n".join(
        "        <li>"
        f'<a href="#{escape(identifier)}"><small>§</small>'
        f"<span>{escape(title)}</span></a></li>"
        for identifier, title in sections
    )
    previous_link = (
        f'<a href="../{previous.slug}/">← Previous</a>'
        if previous
        else '<a href="../">← All labs</a>'
    )
    next_link = (
        f'<a href="../{following.slug}/">Next →</a>'
        if following
        else '<a href="../">All labs ↑</a>'
    )
    mobile_previous = f"../{previous.slug}/" if previous else "../"
    mobile_next = f"../{following.slug}/" if following else "../"
    footer_next = (
        f'<a class="next" href="../{following.slug}/">Lab {following.number}: '
        f"{escape(following.title)} →</a>"
        if following and following.number != "+"
        else (
            f'<a class="next" href="../{following.slug}/">'
            f"{escape(following.title)} →</a>"
            if following
            else '<a class="next" href="../">Return to the 2025 labs ↑</a>'
        )
    )
    number_label = f"L{lab.number}" if lab.number != "+" else "+"
    page_label = (
        f"Lab {escape(lab.number)}: {escape(lab.title)}"
        if lab.number != "+"
        else escape(lab.title)
    )
    return f"""<!doctype html>
<html lang="en-CA">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{escape(lab.description)}">
  <title>{page_label} · CPEN 221</title>
  <link rel="stylesheet" href="../../../assets/fonts/fonts.css">
  <link rel="stylesheet" href="../../../assets/css/site.css">
  <script src="../../../assets/js/typeface-switcher.js"></script>
</head>
<body id="top">
  <!-- lab-source-sha256: {digest} -->
  <!-- lab-source-file: {escape(lab.source)} -->
  <a class="skip-link" href="#lab-content">Skip to lab content</a>

  <nav class="book-nav" aria-label="Lab navigation">
    <a class="wordmark" href="../">
      <strong>CPEN 221</strong>
      <span>Laboratory activities</span>
    </a>
    <div class="nav-contents">
      <p class="part-label">2025 lab archive</p>
      <h2><a href="#top" aria-current="page">{escape(lab.title)} <small>{escape(lab.number)}</small></a></h2>
      <ul>
{nav_items}
      </ul>
      <div class="prev-next">
        {previous_link}
        <a href="../../../">Readings</a>
        {next_link}
      </div>
    </div>
  </nav>

  <nav class="book-nav-mobile" aria-label="Compact lab navigation">
    <a class="mobile-arrow" href="{mobile_previous}" aria-label="Previous lab">←</a>
    <a class="mobile-title" href="../">2025 Labs</a>
    <a class="mobile-arrow" href="{mobile_next}" aria-label="Next lab">{'→' if following else '↑'}</a>
  </nav>

{typeface_tools('../../..')}

  <main id="lab-content" class="page">
    <article class="chapter lab-page">
      <div class="chapter-number" aria-hidden="true">{escape(number_label)}</div>
      <header class="chapter-header">
        <p class="optional-kicker">2025 lab archive</p>
        <h1>{page_label}</h1>
      </header>

      <aside class="archive-note" aria-label="Archive status">
        <strong>Archived activity.</strong> This page preserves the 2025 lab. Submission
        instructions, starter repositories, and external links may have changed.
      </aside>

{body}

      <footer class="book-footer">
        {footer_next}
        CPEN 221 · Software Construction I · 2025 lab archive
      </footer>
    </article>
  </main>
</body>
</html>
"""


def year_index() -> str:
    items = []
    for lab in LABS:
        label = f"Lab {lab.number}" if lab.number != "+" else "+"
        items.append(
            "            <li>"
            f'<span class="num">{escape(label)}</span><div>'
            f'<strong><a href="{escape(lab.slug)}/">{escape(lab.title)}</a></strong>'
            f"<p>{escape(lab.description)}</p></div></li>"
        )
    return f"""<!doctype html>
<html lang="en-CA">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Archived CPEN 221 laboratory activities from 2025.">
  <title>2025 Laboratory Activities · CPEN 221</title>
  <link rel="stylesheet" href="../../assets/fonts/fonts.css">
  <link rel="stylesheet" href="../../assets/css/site.css">
  <script src="../../assets/js/typeface-switcher.js"></script>
</head>
<body id="top">
  <a class="skip-link" href="#main-content">Skip to the lab list</a>
  <nav class="book-nav" aria-label="Lab collection navigation">
    <a class="wordmark" href="../../">
      <strong>CPEN 221</strong>
      <span>Laboratory activities</span>
    </a>
    <div class="nav-contents">
      <p class="part-label">Lab archive</p>
      <h2><a href="#top" aria-current="page">2025</a></h2>
      <ul>
        <li><a href="#lab-list"><small>0–11</small><span>Laboratory activities</span></a></li>
        <li><a href="programming-practice/"><small>+</small><span>Programming practice</span></a></li>
      </ul>
      <div class="prev-next"><a href="../../">Readings</a><a href="../">All years</a></div>
    </div>
  </nav>
  <nav class="book-nav-mobile" aria-label="Compact lab collection navigation">
    <a class="mobile-arrow" href="../../" aria-label="Readings">←</a>
    <a class="mobile-title" href="../">CPEN 221 Labs</a>
    <span class="mobile-arrow" aria-hidden="true">❧</span>
  </nav>
{typeface_tools('../..')}
  <main id="main-content" class="page">
    <article class="contents-page lab-contents">
      <header class="contents-header">
        <p class="kicker">Software Construction I</p>
        <h1>2025 Laboratory Activities</h1>
        <p class="deck">The lab activities used in the 2025 offering of CPEN 221.</p>
      </header>
      <aside class="archive-note" aria-label="Archive status">
        <strong>Archived material.</strong> These pages preserve the 2025 activities.
        Submission instructions, starter repositories, and external links may have changed.
        Teaching-team guides are not published here.
      </aside>
      <section id="lab-list" aria-labelledby="lab-list-heading">
        <h2 id="lab-list-heading">Laboratory activities</h2>
        <ol class="contents-list lab-list">
{''.join(items)}
        </ol>
      </section>
      <footer class="book-footer">
        <a class="next" href="string-chopping/">Begin with Lab 0 →</a>
        CPEN 221 · University of British Columbia · 2025 lab archive
      </footer>
    </article>
  </main>
</body>
</html>
"""


def labs_index() -> str:
    return f"""<!doctype html>
<html lang="en-CA">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="CPEN 221 laboratory activity archive.">
  <title>Laboratory Activities · CPEN 221</title>
  <link rel="stylesheet" href="../assets/fonts/fonts.css">
  <link rel="stylesheet" href="../assets/css/site.css">
  <script src="../assets/js/typeface-switcher.js"></script>
</head>
<body id="top">
  <a class="skip-link" href="#main-content">Skip to the available years</a>
  <nav class="book-nav" aria-label="Lab archive navigation">
    <a class="wordmark" href="../">
      <strong>CPEN 221</strong>
      <span>Laboratory activities</span>
    </a>
    <div class="nav-contents">
      <p class="part-label">Lab archive</p>
      <h2><a href="#top" aria-current="page">Available years</a></h2>
      <ul><li><a href="2025/"><small>2025</small><span>Labs 0–11</span></a></li></ul>
      <div class="prev-next"><a href="../">Readings</a><a href="2025/">2025 →</a></div>
    </div>
  </nav>
  <nav class="book-nav-mobile" aria-label="Compact lab archive navigation">
    <a class="mobile-arrow" href="../" aria-label="Readings">←</a>
    <a class="mobile-title" href="#top" aria-current="page">CPEN 221 Labs</a>
    <a class="mobile-arrow" href="2025/" aria-label="2025 labs">→</a>
  </nav>
{typeface_tools('..')}
  <main id="main-content" class="page">
    <article class="contents-page lab-contents">
      <header class="contents-header">
        <p class="kicker">CPEN 221 · Software Construction I</p>
        <h1>Laboratory Activities</h1>
        <p class="deck">Activities and programming exercises from prior offerings.</p>
      </header>
      <section aria-labelledby="available-years">
        <h2 id="available-years">Available years</h2>
        <ol class="contents-list lab-list">
          <li><span class="num">2025</span><div><strong><a href="2025/">2025 lab archive</a></strong><p>Labs 0–11 and the accompanying programming-practice links.</p></div></li>
        </ol>
      </section>
      <footer class="book-footer">
        <a class="next" href="../">Return to the readings →</a>
        CPEN 221 · University of British Columbia
      </footer>
    </article>
  </main>
</body>
</html>
"""


def link_from_readings_home() -> None:
    home = SITE_ROOT / "index.html"
    if not home.is_file():
        raise SystemExit("Build the readings site before building the lab archive")
    page = home.read_text(encoding="utf-8")
    if 'href="labs/"' in page:
        return

    nav_marker = (
        '        <li><a href="#further-exploration"><small>+</small>'
        '<span>Supplemental readings</span></a></li>'
    )
    nav_link = (
        f"{nav_marker}\n"
        '        <li><a href="labs/"><small>Lab</small>'
        '<span>Laboratory activities</span></a></li>'
    )
    if nav_marker not in page:
        raise SystemExit("Cannot find the readings navigation marker")
    page = page.replace(nav_marker, nav_link, 1)

    footer_marker = '      <footer class="book-footer">'
    lab_section = """      <section class="home-labs" aria-labelledby="labs-heading">
        <h2 id="labs-heading">Laboratory activities</h2>
        <p><a href="labs/">Browse the 2025 lab archive →</a></p>
      </section>

"""
    if footer_marker not in page:
        raise SystemExit("Cannot find the readings footer marker")
    page = page.replace(footer_marker, f"{lab_section}{footer_marker}", 1)
    home.write_text(page, encoding="utf-8")


def build() -> None:
    require_pandoc()
    sources = source_root()
    sync_public_sources(sources)

    if YEAR_ROOT.exists():
        shutil.rmtree(YEAR_ROOT)
    YEAR_ROOT.mkdir(parents=True)

    for index, lab in enumerate(LABS):
        markdown = normalize_markdown(
            (sources / lab.source).read_text(encoding="utf-8")
        )
        digest = sha256(markdown.encode("utf-8")).hexdigest()
        body, sections = transform_body(markdown, lab)
        target = YEAR_ROOT / lab.slug
        target.mkdir()
        previous = LABS[index - 1] if index > 0 else None
        following = LABS[index + 1] if index + 1 < len(LABS) else None
        (target / "index.html").write_text(
            lab_page(lab, body, sections, previous, following, digest),
            encoding="utf-8",
        )

    (YEAR_ROOT / "index.html").write_text(year_index(), encoding="utf-8")
    LABS_ROOT.mkdir(exist_ok=True)
    (LABS_ROOT / "index.html").write_text(labs_index(), encoding="utf-8")
    link_from_readings_home()
    print(f"Built {len(LABS)} public pages in the 2025 lab archive.")


if __name__ == "__main__":
    build()
