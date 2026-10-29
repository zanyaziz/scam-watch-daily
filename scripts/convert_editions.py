#!/usr/bin/env python3
"""Convert saved Scam Watch Daily edition markdown files to standalone HTML pages.

Reads ~/workspace/goals/daily-scam-news-newsletter/hidden_files/*_edition.md
(skipping *_edition_sources.md and *_edition_correction_note.md), derives the
true edition date from each file's header line
("# Scam Watch Daily — Edition for <Weekday, Month D, YYYY>"), and writes
editions/YYYY-MM-DD.html in this repo.

- Lead headline = first bold span in the "## Lead" section; stored as
  <meta name="headline"> so scripts/build_index.py can use it for cards.
- The edition title line is dropped from the body (the page template renders
  its own header); everything else is converted with python-markdown.
- Also handles the exported artifact HTML for editions with no markdown file:
  copy it to editions/YYYY-MM-DD.html yourself, add a <meta name="headline">
  if missing, and build_index.py will pick it up.
Run from anywhere:  python3 scripts/convert_editions.py
"""
import re
import sys
from datetime import date
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
SRC = Path.home() / "workspace/goals/daily-scam-news-newsletter/hidden_files"
OUT = ROOT / "editions"

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11,
    "December": 12,
}

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="headline" content="{headline_attr}">
<title>Scam Watch Daily &mdash; {pretty}</title>
<meta name="description" content="Scam Watch Daily for {pretty}: {headline_attr}">
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; background: #f8fafc; color: #111827; line-height: 1.6; }}
  @media (prefers-color-scheme: dark) {{ body {{ background: #0b1220; color: #e5e7eb; }} a {{ color: #93c5fd !important; }} hr {{ border-color: #1f2937 !important; }} }}
  .wrap {{ max-width: 760px; margin: 0 auto; padding: 40px 20px 64px; }}
  header h1 {{ font-family: Georgia, "Times New Roman", serif; font-size: 36px; margin: 0 0 4px; }}
  header .date {{ color: #6b7280; font-size: 14px; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; }}
  header p.lede {{ font-family: Georgia, "Times New Roman", serif; font-size: 20px; line-height: 1.4; margin: 20px 0 0; }}
  h2 {{ font-family: Georgia, "Times New Roman", serif; font-size: 26px; margin-top: 36px; border-top: 1px solid #e5e7eb; padding-top: 20px; }}
  h3 {{ font-size: 18px; margin-top: 24px; }}
  a {{ color: #1d4ed8; }}
  hr {{ border: none; border-top: 1px solid #e5e7eb; margin: 28px 0; }}
  ul, ol {{ padding-left: 22px; }}
  li + li {{ margin-top: 6px; }}
  footer {{ margin-top: 48px; color: #6b7280; font-size: 13px; line-height: 1.6; border-top: 1px solid #e5e7eb; padding-top: 20px; }}
  footer a {{ color: #2563eb; }}
</style>
</head>
<body>
<div id="swd-archive-bar" style="position:sticky;top:0;z-index:9999;background:#111827;color:#f9fafb;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:10px 16px;font-size:14px;"><a href="../index.html" style="color:#93c5fd;text-decoration:none;">&larr; All editions &mdash; Scam Watch Daily archive</a></div>
<div class="wrap">
  <header>
    <h1>Scam Watch Daily</h1>
    <div class="date">{pretty}</div>
    <p class="lede">{headline}</p>
  </header>
  <main>
{body}
  </main>
  <footer>
    <p>Published daily by Zain Aziz. Source on <a href="https://github.com/zanyaziz/scam-watch-daily">GitHub</a>.</p>
  </footer>
</div>
</body>
</html>
"""


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def clean_md(text: str) -> str:
    text = re.sub(r"[*_`]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_edition(path: Path):
    text = path.read_text(errors="ignore")
    lines = text.splitlines()
    header = lines[0] if lines else ""
    m = re.search(r"Edition for \w+, (\w+) (\d{1,2}), (\d{4})", header)
    if not m:
        return None
    month, day, year = m.group(1), int(m.group(2)), int(m.group(3))
    d = date(year, MONTHS[month], day)
    # Lead headline: first bold span inside the ## Lead section.
    lead = ""
    lead_sec = re.search(r"## Lead\s*\n(.*?)(?=\n## |\Z)", text, re.S)
    if lead_sec:
        b = re.search(r"\*\*(.+?)\*\*", lead_sec.group(1), re.S)
        if b:
            lead = clean_md(b.group(1))
    # Body: everything after the title line.
    body_md = "\n".join(lines[1:]).strip()
    body = markdown.markdown(body_md, extensions=["extra", "sane_lists"])
    return d, lead, body


def main() -> None:
    OUT.mkdir(exist_ok=True)
    made = []
    for path in sorted(SRC.glob("*_edition.md")):
        if path.name.endswith("_edition_sources.md"):
            continue
        if path.name.endswith("_edition_correction_note.md"):
            continue
        parsed = parse_edition(path)
        if not parsed:
            print(f"SKIP (no date header): {path.name}", file=sys.stderr)
            continue
        d, lead, body = parsed
        pretty = d.strftime("%A, %B %-d, %Y")
        page = PAGE_TEMPLATE.format(
            headline_attr=esc(lead),
            headline=esc(lead),
            pretty=pretty,
            body=body,
        )
        (OUT / f"{d.isoformat()}.html").write_text(page)
        made.append(d.isoformat())
    print(f"Wrote {len(made)} edition pages: {', '.join(made)}")


if __name__ == "__main__":
    main()
