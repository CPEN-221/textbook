# Self-hosted typefaces

The site uses the files in this directory; a reader's browser does not contact
Google Fonts. The typeface selector offers two combinations:

1. IBM Plex Serif, IBM Plex Sans, and IBM Plex Mono; and
2. Google Sans Flex and Google Sans Code.

The WOFF2 files were retrieved through the Google Fonts CSS API, most recently on
2026-08-25. Only the Latin and Latin Extended subsets are included. Every selected
family is distributed under the SIL Open Font License 1.1; verbatim licence files
are in `licenses/`.

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
