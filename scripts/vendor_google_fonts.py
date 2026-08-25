#!/usr/bin/env python3
"""Vendor the font files used by the typeface comparison control.

Run this script only when deliberately updating the fonts. Review every change to
assets/fonts before committing it: Google Fonts may serve newer font revisions.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.request import Request, urlopen


SITE_ROOT = Path(__file__).resolve().parent.parent
FONT_ROOT = SITE_ROOT / "assets" / "fonts"
FILE_ROOT = FONT_ROOT / "files"
LICENSE_ROOT = FONT_ROOT / "licenses"
CACHED_CSS = Path("/tmp/cpen221-google-fonts-woff2.css")
RETRIEVED = "2026-08-04"
GOOGLE_CSS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Fraunces:opsz,wght@9..144,600&"
    "family=IBM+Plex+Mono:wght@400;600&"
    "family=IBM+Plex+Sans:ital,wght@0,400;0,600;1,400&"
    "family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,600;1,7..72,400&"
    "family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&"
    "family=Public+Sans:ital,wght@0,400;0,600;1,400&"
    "family=Source+Code+Pro:wght@400;600&"
    "family=Source+Sans+3:ital,wght@0,400;0,600;1,400&"
    "family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&"
    "display=swap"
)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
LICENSES = {
    "fraunces": "Fraunces",
    "ibmplexmono": "IBM Plex Mono",
    "ibmplexsans": "IBM Plex Sans",
    "literata": "Literata",
    "newsreader": "Newsreader",
    "publicsans": "Public Sans",
    "sourcecodepro": "Source Code Pro",
    "sourcesans3": "Source Sans 3",
    "sourceserif4": "Source Serif 4",
}


def download(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request) as response:
        return response.read()


def safe_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def main() -> None:
    if CACHED_CSS.exists():
        source_css = CACHED_CSS.read_text(encoding="utf-8")
    else:
        source_css = download(GOOGLE_CSS_URL).decode("utf-8")

    blocks = re.findall(r"/\* ([^*]+) \*/\s*(@font-face\s*\{.*?\})", source_css, re.S)
    selected = [(subset, block) for subset, block in blocks if subset in {"latin", "latin-ext"}]
    if not selected:
        raise RuntimeError("Google Fonts CSS did not contain Latin WOFF2 subsets")

    FILE_ROOT.mkdir(parents=True, exist_ok=True)
    LICENSE_ROOT.mkdir(parents=True, exist_ok=True)
    local_blocks = []

    for subset, block in selected:
        family = re.search(r"font-family: '([^']+)'", block).group(1)
        style = re.search(r"font-style: ([^;]+)", block).group(1)
        weight = re.search(r"font-weight: ([^;]+)", block).group(1)
        remote_url = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)", block).group(1)
        digest = hashlib.sha256(remote_url.encode("utf-8")).hexdigest()[:10]
        filename = "{}-{}-{}-{}-{}.woff2".format(
            safe_name(family), safe_name(style), safe_name(weight), subset, digest
        )
        (FILE_ROOT / filename).write_bytes(download(remote_url))
        local_block = block.replace(
            "url({})".format(remote_url), 'url("files/{}")'.format(filename)
        )
        local_blocks.append("/* {} */\n{}".format(subset, local_block))

    header = """/*
 * Self-hosted typefaces for the CPEN 221 readings prototype.
 * Retrieved from Google Fonts on {retrieved}; Latin and Latin Extended only.
 * The original CSS request and update procedure are recorded in README.md.
 */

""".format(retrieved=RETRIEVED)
    (FONT_ROOT / "fonts.css").write_text(
        header + "\n\n".join(local_blocks) + "\n", encoding="utf-8"
    )

    for slug, family in LICENSES.items():
        url = "https://raw.githubusercontent.com/google/fonts/main/ofl/{}/OFL.txt".format(slug)
        license_text = download(url).decode("utf-8")
        (LICENSE_ROOT / "{}-OFL.txt".format(slug)).write_text(
            license_text, encoding="utf-8"
        )

    print("Vendored {} WOFF2 files and {} licence files.".format(len(selected), len(LICENSES)))


if __name__ == "__main__":
    main()
