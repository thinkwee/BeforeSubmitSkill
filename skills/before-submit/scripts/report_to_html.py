#!/usr/bin/env python3
"""
report_to_html.py — render the running report markdown into ONE minimal,
self-contained HTML file. Faithful by construction: every line of the md is
converted (unknown lines become paragraphs), so no finding is ever dropped.

Stdlib only. Supports the subset the report uses: # / ## / ### headings,
- / * bullet lists, **bold**, _italic_, `code`, ```fenced code```, [links](url),
--- rules, > blockquotes, and simple | pipe | tables. Severity headings
(## 🔴 / 🟠 / 🔵 …) are color-accented.

Usage:
    python3 report_to_html.py before-submit-report.md [-o before-submit-report.html]
    python3 report_to_html.py report.md            # writes report.html next to it
    python3 report_to_html.py report.md -o -        # write HTML to stdout
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys

CSS = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { max-width: 820px; margin: 2.2rem auto; padding: 0 1.1rem;
  font: 15px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #1c1d1f; background: #fff; }
h1 { font-size: 1.7rem; margin: 0 0 .3rem; padding-bottom: .4rem; border-bottom: 2px solid #eaecef; }
h2 { font-size: 1.25rem; margin: 1.9rem 0 .6rem; padding-left: .6rem; border-left: 4px solid #d0d7de; }
h2.sev-red   { border-color: #e5484d; color: #c62a2f; }
h2.sev-amber { border-color: #f1a10a; color: #b5790a; }
h2.sev-blue  { border-color: #3b82f6; color: #2563c9; }
h3 { font-size: 1.02rem; margin: 1.1rem 0 .35rem; color: #3a3d41; }
p { margin: .5rem 0; }
ul { margin: .4rem 0 .8rem; padding-left: 1.3rem; }
li { margin: .22rem 0; }
code { font: 13px/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: #f2f3f5; padding: .08em .35em; border-radius: 4px; }
pre { background: #f6f8fa; padding: .8rem 1rem; border-radius: 6px; overflow:auto; }
pre code { background: none; padding: 0; }
a { color: #2563c9; text-decoration: none; } a:hover { text-decoration: underline; }
blockquote { margin: .6rem 0; padding: .1rem .9rem; border-left: 3px solid #d0d7de; color: #57606a; }
table { border-collapse: collapse; margin: .7rem 0; width: 100%; font-size: 14px; }
th, td { border: 1px solid #d8dce0; padding: .35rem .6rem; text-align: left; }
th { background: #f6f8fa; }
hr { border: none; border-top: 1px solid #eaecef; margin: 1.4rem 0; }
.meta { color: #57606a; font-size: .92rem; }
footer { margin-top: 2.5rem; padding-top: .7rem; border-top: 1px solid #eaecef;
  color: #8b949e; font-size: .82rem; }
@media (prefers-color-scheme: dark) {
  body { color: #e6e6e6; background: #0f1115; }
  h1 { border-color: #262a31; } h2 { border-color: #30363d; } h3 { color: #c9d1d9; }
  code { background: #1b1f24; } pre { background: #161a1f; }
  th { background: #161a1f; } th, td { border-color: #2a2f36; }
  blockquote { color: #9aa4af; border-color: #30363d; }
  hr, footer { border-color: #262a31; } .meta, footer { color: #8b949e; }
  h2.sev-red { color: #ff6b6f; } h2.sev-amber { color: #f1b53d; } h2.sev-blue { color: #6ea8fe; }
}
"""


def inline(text: str) -> str:
    """Render inline markdown to HTML (code-span safe)."""
    codes: list[str] = []

    def stash(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)          # protect code spans
    text = html.escape(text, quote=False)             # escape the rest
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                  lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w\\])_([^_]+)_(?![\w])", r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00",
                  lambda m: f"<code>{html.escape(codes[int(m.group(1))], quote=False)}</code>", text)
    return text


def sev_class(heading_text: str) -> str:
    if "🔴" in heading_text:
        return " class=\"sev-red\""
    if "🟠" in heading_text:
        return " class=\"sev-amber\""
    if "🔵" in heading_text:
        return " class=\"sev-blue\""
    return ""


def is_table_sep(line: str) -> bool:
    return bool(re.match(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)+\|?\s*$", line))


def split_row(line: str):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def convert(md: str) -> tuple[str, str]:
    lines = md.split("\n")
    out: list[str] = []
    title = ""
    i, n = 0, len(lines)

    while i < n:
        line = lines[i]

        # fenced code block
        if line.lstrip().startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].lstrip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            out.append("<pre><code>" + html.escape("\n".join(buf), quote=False) + "</code></pre>")
            continue

        # blank
        if not line.strip():
            i += 1
            continue

        # horizontal rule
        if re.match(r"^\s*([-*_])(\s*\1){2,}\s*$", line):
            out.append("<hr>")
            i += 1
            continue

        # headings
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            text = m.group(2).rstrip()
            if level == 1 and not title:
                title = re.sub(r"<[^>]+>", "", inline(text))
            cls = sev_class(text) if level == 2 else ""
            out.append(f"<h{level}{cls}>{inline(text)}</h{level}>")
            i += 1
            continue

        # table (header row + separator)
        if "|" in line and i + 1 < n and is_table_sep(lines[i + 1]):
            header = split_row(line)
            i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append(split_row(lines[i]))
                i += 1
            thead = "".join(f"<th>{inline(c)}</th>" for c in header)
            body = ""
            for r in rows:
                body += "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
            out.append(f"<table><thead><tr>{thead}</tr></thead><tbody>{body}</tbody></table>")
            continue

        # blockquote (consecutive >)
        if line.lstrip().startswith(">"):
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>" + inline(" ".join(buf)) + "</blockquote>")
            continue

        # list (consecutive - or * bullets)
        if re.match(r"^\s*[-*]\s+", line):
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i]))
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline(it)}</li>" for it in items) + "</ul>")
            continue

        # paragraph (gather consecutive plain lines)
        buf = [line]
        i += 1
        while i < n and lines[i].strip() and not re.match(
                r"^\s*(#{1,6}\s|[-*]\s|>|```)", lines[i]) and not (
                "|" in lines[i] and i + 1 < n and is_table_sep(lines[i + 1])):
            buf.append(lines[i])
            i += 1
        para = " ".join(s.strip() for s in buf)
        # the italic "_Generated ..._" meta line gets a subtle class
        cls = ' class="meta"' if para.startswith("_") and para.rstrip().endswith("_") else ""
        out.append(f"<p{cls}>{inline(para)}</p>")

    return title or "Before-Submit Report", "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Render report markdown to minimal self-contained HTML")
    ap.add_argument("md")
    ap.add_argument("-o", "--out", default=None, help="output .html (default: alongside input; '-' = stdout)")
    args = ap.parse_args()

    try:
        with open(args.md, "r", encoding="utf-8", errors="replace") as f:
            md = f.read()
    except OSError as e:
        print(f"error: cannot read {args.md}: {e}", file=sys.stderr)
        sys.exit(1)

    title, body = convert(md)
    doc = (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{html.escape(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
        f"{body}\n"
        "<footer>Generated by before-submit · open this file offline; no network or server needed.</footer>\n"
        "</body>\n</html>\n"
    )

    if args.out == "-":
        sys.stdout.write(doc)
        return
    out = args.out or (os.path.splitext(args.md)[0] + ".html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"[report] wrote {out} ({len(doc)} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
