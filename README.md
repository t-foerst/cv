# cv

My CV, version-controlled — English and German.

- `content.de.json` — **the only file you edit.** All CV content, German.
- `photo.jpg` / `.jpeg` / `.png` — optional, square-ish photo (see below).
- `resume.sty` — shared layout.
- `.env` — `DEEPL_API_KEY=...` (create it yourself; gitignored, never committed).
- `scripts/generate.py` — **the only command you run.** Translates (if
  `content.de.json` changed since the last translation), renders the `.tex`
  files, and compiles both PDFs.
- `output/` — everything generated: `content.en.json`, both `.tex` files,
  both `.pdf` files. Gitignored, safe to delete anytime.

## Edit

Change `content.de.json` only — it's the single source of truth. English is
kept in sync automatically on the next build.

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
drawn instead. Photo files are gitignored, never published.
