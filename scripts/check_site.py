#!/usr/bin/env python3

from __future__ import annotations

from html.parser import HTMLParser
from hashlib import sha256
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlsplit
import re
import sys
import xml.etree.ElementTree as ET


SITE_ROOT = Path(__file__).resolve().parent.parent
IGNORED_PARTS = {".git", ".gradle", "build"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.references: list[str] = []
        self.image_alt: list[Optional[str]] = []
        self.has_english_canadian_language = False
        self.has_main = False
        self.in_title = False
        self.title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attributes = dict(attrs)
        if tag == "html" and attributes.get("lang", "").lower() == "en-ca":
            self.has_english_canadian_language = True
        if tag == "main":
            self.has_main = True
        if tag == "title":
            self.in_title = True
        if "id" in attributes and attributes["id"] is not None:
            self.ids.append(attributes["id"])
        if tag == "img":
            self.image_alt.append(attributes.get("alt"))
        for attribute in ("href", "src"):
            value = attributes.get(attribute)
            if value is not None:
                self.references.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)


def parse_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def local_target(source: Path, url: str) -> tuple[Optional[Path], str]:
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        return None, ""
    if parsed.path.startswith("/"):
        raise ValueError("root-relative URLs break GitHub project Pages sites")

    target = source if not parsed.path else (source.parent / unquote(parsed.path)).resolve()
    try:
        target.relative_to(SITE_ROOT)
    except ValueError as error:
        raise ValueError("URL leaves the publication directory") from error

    if parsed.path.endswith("/") or target.is_dir():
        target = target / "index.html"
    return target, unquote(parsed.fragment)


def check_svg(path: Path, failures: list[str]) -> None:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        failures.append(f"{path.relative_to(SITE_ROOT)}: malformed SVG: {error}")
        return

    namespace = {"svg": "http://www.w3.org/2000/svg"}
    title = root.find("svg:title", namespace)
    description = root.find("svg:desc", namespace)
    if title is None or not "".join(title.itertext()).strip():
        failures.append(f"{path.relative_to(SITE_ROOT)}: missing a non-empty title")
    if description is None or not "".join(description.itertext()).strip():
        failures.append(f"{path.relative_to(SITE_ROOT)}: missing a non-empty description")


def is_published(path: Path) -> bool:
    return not IGNORED_PARTS.intersection(path.relative_to(SITE_ROOT).parts)


html_files = sorted(path for path in SITE_ROOT.rglob("*.html") if is_published(path))
pages = {path: parse_page(path) for path in html_files}
failures: list[str] = []

for path, page in pages.items():
    display_name = path.relative_to(SITE_ROOT)
    if not page.has_english_canadian_language:
        failures.append(f'{display_name}: missing lang="en-CA"')
    if not page.has_main:
        failures.append(f"{display_name}: missing a main landmark")
    if not "".join(page.title_parts).strip():
        failures.append(f"{display_name}: missing a non-empty title")
    page_source = path.read_text(encoding="utf-8")
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", page_source):
        failures.append(f"{display_name}: contains an unexpected control character")
    if "fonts.googleapis.com" in page_source or "fonts.gstatic.com" in page_source:
        failures.append(f"{display_name}: loads a font from an external Google host")

    source_digest = re.search(r"source-sha256:\s*([0-9a-f]{64})", page_source)
    source_file = re.search(r"source-file:\s*([A-Za-z0-9_.-]+\.md)", page_source)
    if path.parent.parent == SITE_ROOT / "chapters":
        if "references" not in page.ids:
            failures.append(f"{display_name}: missing references section")
        if source_digest is None:
            failures.append(f"{display_name}: missing source digest")
        if source_file is None:
            failures.append(f"{display_name}: missing source filename")
        elif source_digest is not None:
            source_target = SITE_ROOT / "sources" / source_file.group(1)
            if not source_target.is_file():
                failures.append(
                    f"{display_name}: missing source file {source_target.name}"
                )
            elif (
                sha256(source_target.read_bytes()).hexdigest()
                != source_digest.group(1)
            ):
                failures.append(
                    f"{display_name}: generated page is stale relative to "
                    f"{source_target.relative_to(SITE_ROOT)}"
                )

    for identifier in set(page.ids):
        if page.ids.count(identifier) > 1:
            failures.append(f"{display_name}: duplicate id #{identifier}")
    for alt_text in page.image_alt:
        if alt_text is None:
            failures.append(f"{display_name}: image missing an alt attribute")

    for reference in page.references:
        try:
            target, fragment = local_target(path, reference)
        except ValueError as error:
            failures.append(f"{display_name}: {reference}: {error}")
            continue
        if target is None:
            continue
        if not target.exists():
            failures.append(f"{display_name}: missing target for {reference}")
            continue
        if fragment and target.suffix == ".html":
            target_page = pages.get(target)
            if target_page is None or fragment not in target_page.ids:
                failures.append(
                    f"{display_name}: missing fragment #{fragment} in "
                    f"{target.relative_to(SITE_ROOT)}"
                )

svg_files = sorted(path for path in SITE_ROOT.rglob("*.svg") if is_published(path))
for svg_file in svg_files:
    check_svg(svg_file, failures)

css_files = sorted(path for path in SITE_ROOT.rglob("*.css") if is_published(path))
for css_file in css_files:
    css = css_file.read_text(encoding="utf-8")
    for reference in re.findall(r"url\(\s*['\"]?([^'\")]+)", css):
        try:
            target, _ = local_target(css_file, reference)
        except ValueError as error:
            failures.append(f"{css_file.relative_to(SITE_ROOT)}: {reference}: {error}")
            continue
        if target is not None and not target.exists():
            failures.append(
                f"{css_file.relative_to(SITE_ROOT)}: missing target for {reference}"
            )

if failures:
    print("\n".join(failures), file=sys.stderr)
    raise SystemExit(1)

print(
    f"Checked {len(html_files)} HTML pages, {len(css_files)} CSS files, and "
    f"{len(svg_files)} SVG files: local links, fragments, "
    "font assets, image text, and page landmarks are valid."
)
