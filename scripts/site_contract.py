#!/usr/bin/env python3
"""Definitions shared by build_site.py and check_site.py.

Both scripts must agree about where pages live, what every published page has to
contain, and how a page records the Markdown it was generated from. Keeping those
facts here means the generator cannot stop emitting something the checker still
requires, which is a failure this project has already seen once.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess


SITE_ROOT = Path(__file__).resolve().parent.parent
COURSE_ROOT = SITE_ROOT.parent
PUBLISHED_SOURCES = SITE_ROOT / "sources"
COURSE_SOURCES = COURSE_ROOT / "notes" / "revised"
CHAPTERS_ROOT = SITE_ROOT / "chapters"

# Pandoc renders every chapter body. Layout can change between pandoc releases, so
# the version is pinned here and verified before a build. The CI workflow installs
# this exact version; set CPEN221_ALLOW_PANDOC_MISMATCH=1 to override locally.
PANDOC_VERSION = "3.10.2"
PANDOC_ARGUMENTS = (
    "--from=gfm",
    "--to=html5",
    "--wrap=none",
    "--syntax-highlighting=none",
)

# Invariants every published page satisfies. check_site.py enforces them and
# build_site.py emits them.
LANG = "en-CA"
REFERENCES_ID = "references"

# Directories that exist in the working tree but are never published.
IGNORED_PARTS = {".git", ".gradle", "build"}


@dataclass(frozen=True)
class Chapter:
    source: str
    slug: str
    number: str
    title: str
    description: str
    part: str
    optional: bool = False


CHAPTERS = (
    Chapter(
        "chapter-01-engineering-reliable-software.md",
        "engineering-reliable-software",
        "1",
        "Engineering Reliable Software",
        "Build a short Java feedback loop around an observed transit-system failure.",
        "Foundations",
    ),
    Chapter(
        "chapter-02-types-and-specifications.md",
        "types-and-specifications",
        "2",
        "Types and Specifications",
        "Use domain types and behavioural contracts to state what transit software means.",
        "Foundations",
    ),
    Chapter(
        "chapter-03-exceptions-testing-and-evidence.md",
        "exceptions-testing-and-evidence",
        "3",
        "Exceptions, Testing, and Evidence",
        "Design failure paths and derive useful tests from a transit-feed contract.",
        "Foundations",
    ),
    Chapter(
        "chapter-04-mutability-aliasing-and-debugging.md",
        "mutability-aliasing-and-debugging",
        "4",
        "Mutability, Aliasing, and Debugging",
        "Follow references, close representation leaks, and debug mutable state with evidence.",
        "State and abstraction",
    ),
    Chapter(
        "chapter-05-adts-and-representation-independence.md",
        "adts-and-representation-independence",
        "5",
        "ADTs and Representation Independence",
        "Design an immutable transit-network ADT whose clients do not depend on its data structures.",
        "State and abstraction",
    ),
    Chapter(
        "chapter-06-representation-invariants-and-abstraction-functions.md",
        "representation-invariants-and-abstraction-functions",
        "6",
        "Representation Invariants and Abstraction Functions",
        "Connect concrete transit-network fields to valid abstract graph values.",
        "State and abstraction",
    ),
    Chapter(
        "chapter-07-equality-hashing-and-behavioural-subtyping.md",
        "equality-hashing-and-behavioural-subtyping",
        "7",
        "Equality, Hashing, and Behavioural Subtyping",
        "Define value equality, use hash-based collections correctly, and preserve supertype contracts.",
        "Interfaces and relationships",
    ),
    Chapter(
        "chapter-08-composition-delegation-and-api-design.md",
        "composition-delegation-and-api-design",
        "8",
        "Composition, Delegation, and API Design",
        "Assemble routing behaviour behind focused interfaces and explicit component boundaries.",
        "Interfaces and relationships",
    ),
    Chapter(
        "chapter-09-recursion-and-recursive-datatypes.md",
        "recursion-and-recursive-datatypes",
        "9",
        "Recursion and Recursive Datatypes",
        "Represent recursive journeys and justify recursive traversal, termination, and correctness.",
        "Data and transformations",
    ),
    Chapter(
        "chapter-10-functions-streams-and-data-transformations.md",
        "functions-streams-and-data-transformations",
        "10",
        "Functions, Streams, and Data Transformations",
        "Build ordered, non-interfering transformations over transit observations.",
        "Data and transformations",
    ),
    Chapter(
        "chapter-11-systems-model-and-network-protocols.md",
        "systems-model-and-network-protocols",
        "11",
        "Systems Model and Network Protocols",
        "Specify and implement a prediction exchange across a process boundary.",
        "Networked and concurrent systems",
    ),
    Chapter(
        "chapter-12-parallelism-concurrency-and-virtual-threads.md",
        "parallelism-concurrency-and-virtual-threads",
        "12",
        "Parallelism, Concurrency, and Virtual Threads",
        "Coordinate blocking tasks with virtual threads, explicit lifetimes, and resource limits.",
        "Networked and concurrent systems",
    ),
    Chapter(
        "chapter-13-thread-safety-integration-and-reliability.md",
        "thread-safety-integration-and-reliability",
        "13",
        "Thread Safety, Integration, and Reliability",
        "Publish coherent snapshots and connect local contracts to system reliability.",
        "Networked and concurrent systems",
    ),
    Chapter(
        "supplemental-how-java-runs.md",
        "how-java-runs",
        "+",
        "How a Java Program Runs",
        "Trace Java calls, frames, recursion, exceptions, and shared reachable objects.",
        "Supplemental readings",
        optional=True,
    ),
    Chapter(
        "supplemental-beyond-the-java-call-stack.md",
        "beyond-java-call-stack",
        "+",
        "Beyond the Java Call Stack",
        "Investigate bytecode, optimised execution, thread dumps, and native stack safety.",
        "Supplemental readings",
        optional=True,
    ),
)

def provenance_comments(source_name: str, digest: str) -> str:
    """Render the comments that tie a generated page to its Markdown source."""
    return (
        f"<!-- source-sha256: {digest} -->\n"
        f"  <!-- source-file: {source_name} -->"
    )


SOURCE_DIGEST_PATTERN = re.compile(r"source-sha256:\s*([0-9a-f]{64})")
SOURCE_FILE_PATTERN = re.compile(r"source-file:\s*([A-Za-z0-9_.-]+\.md)")


def read_provenance(page_source: str) -> tuple[str | None, str | None]:
    """Recover (source filename, digest) from a generated page."""
    digest = SOURCE_DIGEST_PATTERN.search(page_source)
    source_file = SOURCE_FILE_PATTERN.search(page_source)
    return (
        source_file.group(1) if source_file else None,
        digest.group(1) if digest else None,
    )


def chapter_directory(chapter: Chapter) -> Path:
    return CHAPTERS_ROOT / chapter.slug


def chapter_page(chapter: Chapter) -> Path:
    return chapter_directory(chapter) / "index.html"


def is_chapter_page(path: Path) -> bool:
    return path.name == "index.html" and path.parent.parent == CHAPTERS_ROOT


def is_published(path: Path) -> bool:
    """True for files that belong in the Pages artifact."""
    return (
        not IGNORED_PARTS.intersection(path.relative_to(SITE_ROOT).parts)
        and "conflicted copy" not in path.name
    )


def source_root() -> Path:
    """Locate the chapter Markdown.

    Prefer the editable manuscript in the course workspace. The published repository
    does not contain it, so continuous integration falls back to the copies under
    sources/, which is what makes a rebuild-and-compare check possible there.
    """
    if all((COURSE_SOURCES / chapter.source).is_file() for chapter in CHAPTERS):
        return COURSE_SOURCES
    if all((PUBLISHED_SOURCES / chapter.source).is_file() for chapter in CHAPTERS):
        return PUBLISHED_SOURCES
    raise SystemExit("Cannot find the complete revised chapter source set")


def installed_pandoc_version() -> str:
    try:
        result = subprocess.run(
            ["pandoc", "--version"], text=True, capture_output=True, check=True
        )
    except FileNotFoundError as error:
        raise SystemExit(
            f"Pandoc {PANDOC_VERSION} is required to build the chapter pages"
        ) from error
    first_line = result.stdout.splitlines()[0]
    match = re.search(r"pandoc\s+([0-9][0-9.]*)", first_line)
    if match is None:
        raise SystemExit(f"Cannot read a version from: {first_line}")
    return match.group(1)
