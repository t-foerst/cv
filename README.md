# cv

My CV, version-controlled — English and German.

<p align="center">
  <img src="preview/cv_de.png" width="49%" alt="CV preview (German)">
  <img src="preview/cv_en.png" width="49%" alt="CV preview (English)">
</p>

`preview/*.png` is auto-updated on every push to `main` by
[`.github/workflows/cv-preview.yml`](.github/workflows/cv-preview.yml),
built from a redacted contact-info fallback (see `personal.public.json`
below) since the real `personal.json` is gitignored and unavailable in CI.

- `content.de.json` — **the file you edit** for CV content (summary,
  education, experience, projects, skills, ...). German.
- `personal.json` — your real contact/personal details shown in the header
  (phone, email, LinkedIn, GitHub, location, birth date & place). Copy from
  `personal.json.example` and fill in; gitignored, never committed.
- `personal.public.json` — redacted fallback (just email/LinkedIn/GitHub,
  everything else blank) used automatically when `personal.json` isn't
  present. Committed — this is what CI and anyone cloning the repo sees.
  Edit it if you want more/less shown in the public preview.
- `photo.jpg` / `.jpeg` / `.png` — optional, square-ish photo (see below).
- `resume.sty` — shared layout.
- `.env` — `DEEPL_API_KEY=...` (create it yourself; gitignored, never committed).
- `scripts/generate.py` — **the only command you run.** Translates (if
  `content.de.json` changed since the last translation), renders the `.tex`
  files, and compiles both PDFs.
- `output/` — everything generated: `content.en.json`, both `.tex` files,
  both `.pdf` files. Gitignored, safe to delete anytime.
- `preview/` — PNG snapshots of both PDFs, committed, shown at the top of
  this README. Refreshed by CI on every push to `main`.

## Setup

```sh
cp personal.json.example personal.json   # then fill in your details
```

## Edit

Change `content.de.json` for CV content. English is kept in sync
automatically on the next build. `personal.json` doesn't need touching once
set up, unless your contact details change.

## Build

```sh
python3 scripts/generate.py
```

Translates (if `content.de.json` changed since the last translation, via
DeepL — needs `DEEPL_API_KEY` in `.env`; skipped, not fatal, if missing or
offline, reusing the previous `output/content.en.json`), renders both
`.tex` files, and compiles `output/cv_de.pdf` / `output/cv_en.pdf`.

Free DeepL key: https://www.deepl.com/pro-api (keys ending in `:fx` are
free-tier and handled automatically).

To review the machine translation before trusting it, check
`output/content.en.json` after building — or run
`python3 scripts/translate.py` on its own to refresh it without compiling.

## Photo

Drop a roughly square `photo.jpg` (or `.jpeg` / `.png`) next to
`content.de.json` — it's automatically cropped into the circular photo slot
on next build. Without a file present, a placeholder with your initials is
drawn instead. Photo files are gitignored, never published — the CI preview
always shows the initials placeholder, never a real photo.

## CI preview

On every push to `main`, `.github/workflows/cv-preview.yml` builds the CV
using `personal.public.json` (no `personal.json` or photo in that checkout),
renders both PDFs to PNG, and commits them to `preview/`. That's the image
shown at the top of this README. To also get the English preview refreshed,
add a repo secret `DEEPL_API_KEY`; without it, the English build is skipped
in CI and the previous `preview/cv_en.png` is left as-is.
