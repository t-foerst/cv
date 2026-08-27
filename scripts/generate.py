#!/usr/bin/env python3
"""One-shot CV build: translate (if stale) -> render .tex -> compile PDFs.

- content.de.json (repo root)   -- the file you edit for CV content
- personal.json (repo root)     -- your real contact/personal details,
                                    gitignored (copy from personal.json.example)
- personal.public.json          -- redacted fallback used when personal.json
                                    isn't present (e.g. in CI, since it's
                                    gitignored) -- committed, safe to publish
- output/content.en.json        -- auto-refreshed via DeepL when content.de.json
                                    is newer (needs DEEPL_API_KEY in .env; skipped,
                                    not fatal, if missing/offline)
- output/cv_de.tex, cv_en.tex, cv_de.pdf, cv_en.pdf -- generated

Usage: scripts/generate.py [de] [en]   (defaults to both)
"""
import json
import os
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
PERSONAL_PATH = ROOT / "personal.json"
PERSONAL_PUBLIC_PATH = ROOT / "personal.public.json"

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
        "phone_label": "Tel.",
        "location_label": "Wohnort",
        "born_label": "Geboren",
        "born_in": "in",
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
        "phone_label": "Phone",
        "location_label": "Location",
        "born_label": "Born",
        "born_in": "in",
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


def info_block(lang, personal):
    """Two-column contact/personal list. Fields left empty in personal.json
    (e.g. in the redacted personal.public.json) are skipped entirely."""
    L = LABELS[lang]
    p = personal
    lines = []
    if p.get("phone"):
        lines.append(f"{L['phone_label']}: {esc(p['phone'])}")
    if p.get("email"):
        lines.append(f"\\href{{mailto:{p['email']}}}{{{p['email']}}}")
    if p.get("linkedin_url"):
        lines.append(f"\\href{{https://{p['linkedin_url']}}}{{{p['linkedin_label']}}}")
    if p.get("github_url"):
        lines.append(f"\\href{{https://{p['github_url']}}}{{{p['github_label']}}}")
    if p.get("location"):
        lines.append(f"{L['location_label']}: {esc(p['location'])}")
    if p.get("birth_date"):
        born = f"{L['born_label']}: {esc(p['birth_date'])}"
        if p.get("birth_place"):
            born += f" {L['born_in']} {esc(p['birth_place'])}"
        lines.append(born)

    half = (len(lines) + 1) // 2
    col_a = "\\\\\n        ".join(lines[:half])
    col_b = "\\\\\n        ".join(lines[half:])
    return (
        f"\\begin{{minipage}}[t]{{0.5\\cvbannertextwidth}}\n"
        f"        {col_a}\n"
        f"      \\end{{minipage}}%\n"
        f"      \\begin{{minipage}}[t]{{0.5\\cvbannertextwidth}}\n"
        f"        {col_b}\n"
        f"      \\end{{minipage}}"
    )


def render(lang, content, personal, is_public):
    L = LABELS[lang]
    c = content
    resume_pkg = "\\usepackage[public]{resume}" if is_public else "\\usepackage{resume}"

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
{resume_pkg}

\\hypersetup{{pdftitle={{{c['name']} - {L['doc_title']}}}, pdfauthor={{{c['name']}}}}}

\\begin{{document}}

\\cvbanner
  {{{esc(c['name'])}}}
  {{{esc(c['tagline'])}}}
  {{{esc(c['initials'])}}}
  {{{info_block(lang, personal)}}}

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
            # -g: force a rebuild even if latexmk's content-hash check thinks
            # nothing changed -- it can't see photo.jpg/png swaps, since the
            # photo path is only resolved inside resume.sty at compile time,
            # not in the (textually unchanged) .tex source.
            ["latexmk", "-pdf", "-g", "-interaction=nonstopmode", "-halt-on-error", tex_name],
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

    is_public = not PERSONAL_PATH.exists()
    if not is_public:
        personal = json.loads(PERSONAL_PATH.read_text(encoding="utf-8"))
    elif PERSONAL_PUBLIC_PATH.exists():
        print(f"{PERSONAL_PATH} not found -- using {PERSONAL_PUBLIC_PATH} "
              "(redacted, public-safe contact info, no photo).", file=sys.stderr)
        personal = json.loads(PERSONAL_PUBLIC_PATH.read_text(encoding="utf-8"))
    else:
        print(f"Neither {PERSONAL_PATH} nor {PERSONAL_PUBLIC_PATH} found -- "
              "copy personal.json.example to personal.json and fill in your "
              "contact details.", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "resume.sty", OUTPUT_DIR / "resume.sty")

    if "en" in langs and translation_is_stale():
        refresh_translation()

    written = []
    for lang in langs:
        path = CONTENT_PATH[lang]
        if not path.exists():
            print(f"skipping {lang}: {path} not found"
                  + ("  (set DEEPL_API_KEY in .env to auto-translate)" if lang == "en" else ""),
                  file=sys.stderr)
            continue
        content = json.loads(path.read_text(encoding="utf-8"))
        tex = render(lang, content, personal, is_public)
        out = OUTPUT_DIR / f"cv_{lang}.tex"
        out.write_text(tex, encoding="utf-8")
        print(f"wrote {out}")
        written.append(lang)

    failed = [lang for lang in written if not compile_pdf(lang)]
    if failed:
        print(f"Aborting: PDF compilation failed for: {', '.join(failed)}",
              file=sys.stderr)
        sys.exit(1)

    if "de" in written and not os.environ.get("CI"):
        open_pdf("de")


if __name__ == "__main__":
    main()
