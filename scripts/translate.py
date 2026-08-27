#!/usr/bin/env python3
"""Refresh output/content.en.json from content.de.json via the DeepL API.

Called automatically by scripts/generate.py whenever content.de.json is
newer than output/content.en.json. Can also be run standalone to force a
refresh or to translate outside of a full build.

Requires a DeepL API key. Put it in a .env file (repo root) as:
  DEEPL_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx:fx
Free tier: https://www.deepl.com/pro-api -- keys ending in ":fx" are routed
to the free API host automatically.
"""
import json
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"

# JSON-pointer-style paths that must NOT be sent to the translator
# (proper nouns, contact details, URLs, identical brand names, ...).
NON_TRANSLATABLE = {
    "name",
    "initials",
    "education.org",
    "certification.title_line1",
    "certification.title_line2",
    "certification.link_url",
}


def load_dotenv(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def deepl_translate(texts, api_key):
    host = "api-free.deepl.com" if api_key.endswith(":fx") else "api.deepl.com"
    url = f"https://{host}/v2/translate"
    data = urllib.parse.urlencode(
        [("text", t) for t in texts]
        + [("source_lang", "DE"), ("target_lang", "EN-GB")]
    ).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Authorization": f"DeepL-Auth-Key {api_key}"}
    )
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read())
    return [t["text"] for t in body["translations"]]


def walk_collect(node, path, out):
    """Collect (path, value) leaves for every translatable string field."""
    if isinstance(node, dict):
        for k, v in node.items():
            walk_collect(v, f"{path}.{k}" if path else k, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk_collect(v, f"{path}[{i}]", out)
    elif isinstance(node, str):
        if path not in NON_TRANSLATABLE:
            out.append((path, node))


def walk_set(node, path, value):
    parts = path.split(".")
    cur = node
    for i, part in enumerate(parts):
        last = i == len(parts) - 1
        if "[" in part:
            key, idx = part[:-1].split("[")
            idx = int(idx)
            cur = cur[key] if not last else cur[key]
            if last:
                cur[idx] = value
            else:
                cur = cur[idx]
        else:
            if last:
                cur[part] = value
            else:
                cur = cur[part]
    return node


def refresh_translation():
    """Translate content.de.json -> output/content.en.json. Returns True on success."""
    load_dotenv(ROOT / ".env")
    api_key = os.environ.get("DEEPL_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        print("DEEPL_API_KEY is not set in .env -- skipping translation, "
              "using existing output/content.en.json if present.", file=sys.stderr)
        return False

    de = json.loads((ROOT / "content.de.json").read_text(encoding="utf-8"))

    leaves = []
    walk_collect(de, "", leaves)
    paths = [p for p, _ in leaves]
    texts = [v for _, v in leaves]

    print(f"Translating {len(texts)} fields via DeepL ...")
    try:
        translated = deepl_translate(texts, api_key)
    except Exception as e:
        print(f"DeepL translation failed ({e}) -- skipping, using existing "
              "output/content.en.json if present.", file=sys.stderr)
        return False

    en = json.loads((ROOT / "content.de.json").read_text(encoding="utf-8"))
    for path, value in zip(paths, translated):
        walk_set(en, path, value)

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / "content.en.json"
    out_path.write_text(json.dumps(en, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    return True


def main():
    ok = refresh_translation()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
