# Self-hosted typefaces

The site uses the files in this directory; a reader's browser does not contact
Google Fonts. The typeface selector offers these combinations:

1. Literata, IBM Plex Sans, and IBM Plex Mono;
2. Newsreader, Public Sans, and Source Code Pro;
3. Source Serif 4, Source Sans 3, and Source Code Pro;
4. Fraunces headings, Literata text, IBM Plex Sans, and IBM Plex Mono.
5. IBM Plex Serif, IBM Plex Sans, and IBM Plex Mono;
6. Google Sans Flex and Google Sans Code.

`fonts.css` and the original WOFF2 files were retrieved through the Google Fonts
CSS API on 2026-08-04. IBM Plex Serif, Google Sans Flex, and Google Sans Code were
added from the same API on 2026-08-25. Only the Latin and Latin Extended subsets
are included. Every family is distributed under the SIL Open Font License 1.1;
verbatim licence files are in `licenses/`.

The filenames record the family, style, weight, subset, and a short hash of the
source URL. This makes an upstream revision visible during review. The CSS retains
Google Fonts' `unicode-range` declarations so browsers download only the subset a
page needs.

To update the assets deliberately, run this from the repository root:

```bash
python3 www/scripts/vendor_google_fonts.py
```

The script's CSS request is the provenance record for the selected variants. It
may produce different files when upstream families change, so review the generated
CSS, binaries, and licences before publishing an update.
