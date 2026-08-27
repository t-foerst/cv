#!/usr/bin/env python3
"""One-shot CV build: translate (if stale) -> render .tex -> compile PDFs.

- content.de.json (repo root)  -- the only file you edit
- output/content.en.json       -- auto-refreshed via DeepL when content.de.json
                                   is newer (needs DEEPL_API_KEY in .env; skipped,
                                   not fatal, if missing/offline)
- output/cv_de.tex, cv_en.tex, cv_de.pdf, cv_en.pdf -- generated

Usage: scripts/generate.py [de] [en]   (defaults to both)
"""
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from translate import refresh_translation  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"

CONTENT_PATH = {
    "de": ROOT / "content.de.json",
    "en": OUTPUT_DIR / "content.en.json",
}

LABELS = {
    "de": {
        "babel": "ngerman",
        "doc_title": "Lebenslauf",
        "section_skills": "Kenntnisse",
        "section_certifications": "Zertifizierungen",
        "section_languages": "Sprachen",
        "section_summary": "Profil",
        "section_education": "Ausbildung",
        "section_experience": "Berufserfahrung",
        "section_projects": "Projekte",
        "thesis_label": "Bachelorarbeit",
        "quote_open": "„",
        "quote_close": "“",
    },
    "en": {
        "babel": "english",
        "doc_title": "CV",
        "section_skills": "Skills",
        "section_certifications": "Certifications",
        "section_languages": "Languages",
        "section_summary": "Summary",
        "section_education": "Education",
        "section_experience": "Experience",
        "section_projects": "Projects",
        "thesis_label": "Bachelor's thesis",
        "quote_open": '"',
        "quote_close": '"',
    },
}

_ESCAPE_MAP = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}
_ESCAPE_RE = re.compile("|".join(re.escape(c) for c in _ESCAPE_MAP))


def esc(text):
    """Escape LaTeX special characters in plain content text."""
    return _ESCAPE_RE.sub(lambda m: _ESCAPE_MAP[m.group()], text)


def esc_breakable(text):
    """Like esc(), but also lets long slash-separated lists wrap (no overfull hbox)."""
    return esc(text).replace("/", r"\slash ")


def cvitems(bullets):
    lines = ["\\begin{cvitems}"]
    for b in bullets:
        lines.append(f"  \\item {esc(b)}")
    lines.append("\\end{cvitems}")
    return "\n".join(lines)


def cventry(title, org, dates):
    return f"\\cventry{{{esc(title)}}}{{{esc(org)}}}{{{esc(dates)}}}"


def render(lang, content):
    L = LABELS[lang]
    c = content

    skills = "\n".join(
        f"\\cvskill{{{esc(s['category'])}}}{{{esc_breakable(s['items'])}}}"
        for s in c["skills"]
    )

    languages = "\\\\\n".join(f"{{\\small {esc(item)}}}" for item in c["languages"])

    experience = "\n\n".join(
        cventry(e["title"], e["org"], e["dates"]) + "\n" + cvitems(e["bullets"])
        for e in c["experience"]
    )

    projects = "\n\n".join(
        cventry(p["title"], p["org"], p["dates"]) + "\n" + cvitems(p["bullets"])
        for p in c["projects"]
    )

    cert = c["certification"]

    tex = f"""\\documentclass[10pt,a4paper]{{article}}
\\usepackage[{L['babel']}]{{babel}}
\\usepackage{{resume}}

\\hypersetup{{pdftitle={{{c['name']} - {L['doc_title']}}}, pdfauthor={{{c['name']}}}}}

\\begin{{document}}

\\cvbanner
  {{{esc(c['name'])}}}
  {{{esc(c['tagline'])}}}
  {{{esc(c['initials'])}}}
  {{{c['email']}}}
  {{{c['linkedin_label']}}}{{{c['linkedin_url']}}}
  {{{c['github_label']}}}{{{c['github_url']}}}

\\begin{{cvsidebar}}

\\section*{{{L['section_skills']}}}
{skills}

\\section*{{{L['section_certifications']}}}
\\textbf{{\\small {esc(cert['title_line1'])}\\\\{esc(cert['title_line2'])}}}\\\\
{{\\footnotesize\\color{{muted}}{esc(cert['subtitle'])}}}\\\\
{{\\footnotesize\\href{{{cert['link_url']}}}{{{esc(cert['link_label'])}}}}}

\\section*{{{L['section_languages']}}}
{languages}

\\end{{cvsidebar}}%
\\cvcolgap%
\\begin{{cvmain}}

\\section*{{{L['section_summary']}}}
{esc(c['summary'])}

\\section*{{{L['section_education']}}}
{cventry(c['education']['degree'], c['education']['org'], c['education']['dates'])}
\\begin{{cvitems}}
  \\item {L['thesis_label']}: \\textit{{{L['quote_open']}{esc(c['education']['thesis_title'])}{L['quote_close']}}}
\\end{{cvitems}}

\\section*{{{L['section_experience']}}}
{experience}

\\section*{{{L['section_projects']}}}
{projects}

\\end{{cvmain}}

\\end{{document}}
"""
    return tex


def translation_is_stale():
    en_path = CONTENT_PATH["en"]
    de_path = CONTENT_PATH["de"]
    if not en_path.exists():
        return True
    return de_path.stat().st_mtime > en_path.stat().st_mtime


def compile_pdf(lang):
    tex_name = f"cv_{lang}.tex"
    if not (OUTPUT_DIR / tex_name).exists():
        return False
    try:
        result = subprocess.run(
            ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", tex_name],
            cwd=OUTPUT_DIR,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("latexmk not found on PATH -- install TeX Live (e.g. "
              "`sudo dnf install texlive-scheme-basic latexmk texlive-titlesec "
              "texlive-enumitem texlive-microtype texlive-geometry "
              "texlive-babel-german`), or compile output/cv_*.tex yourself.",
              file=sys.stderr)
        return False
    if result.returncode != 0:
        print((result.stdout + result.stderr)[-3000:], file=sys.stderr)
        print(f"latexmk failed for {lang} -- see output/cv_{lang}.log", file=sys.stderr)
        return False
    print(f"compiled output/cv_{lang}.pdf")
    return True


def open_pdf(lang):
    pdf_path = OUTPUT_DIR / f"cv_{lang}.pdf"
    if not pdf_path.exists():
        return
    opener = {"Darwin": "open", "Windows": "start"}.get(platform.system(), "xdg-open")
    try:
        subprocess.Popen(
            [opener, str(pdf_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        print(f"Could not auto-open {pdf_path} (no '{opener}' found) -- open it manually.",
              file=sys.stderr)


def main():
    langs = sys.argv[1:] or ["de", "en"]
    OUTPUT_DIR.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "resume.sty", OUTPUT_DIR / "resume.sty")

    if "en" in langs and translation_is_stale():
        refresh_translation()

    for lang in langs:
        path = CONTENT_PATH[lang]
        if not path.exists():
            print(f"skipping {lang}: {path} not found"
                  + ("  (set DEEPL_API_KEY in .env to auto-translate)" if lang == "en" else ""),
                  file=sys.stderr)
            continue
        content = json.loads(path.read_text(encoding="utf-8"))
        tex = render(lang, content)
        out = OUTPUT_DIR / f"cv_{lang}.tex"
        out.write_text(tex, encoding="utf-8")
        print(f"wrote {out}")

    ok = {lang: compile_pdf(lang) for lang in langs}

    if "de" in langs and ok.get("de"):
        open_pdf("de")


if __name__ == "__main__":
    main()
