# Running report format (`before-submit-report.md`)

The audit runs as a parallel team, so findings land in **fragment files** first,
then get merged:
- Each team member appends findings to its **own** fragment as it confirms them —
  `before-submit-parts/{bib,latex,compliance,faithfulness,compile}.md` — using the
  one-finding-per-bullet format below (with severity tags). Appending as-you-go
  keeps each worker's progress durable.
- The orchestrator **merges** the fragments into the single
  `before-submit-report.md` in Phase 6: concatenate, regroup every bullet under
  the correct severity heading, then add the summary + "what I checked / skipped"
  + venue sections.

The HTML step (`scripts/report_to_html.py`) renders exactly the merged
`before-submit-report.md`, so anything not in it won't be shown — **put every
issue here**. So fragments don't need to be pre-grouped; the merge regroups them,
but each bullet should carry enough context (which severity it belongs to) to
sort. A simple convention: prefix each fragment bullet with `🔴`/`🟠`/`🔵`.

## Conventions

- One finding = one bullet, immediately followed by a verbatim quote of the
  offending source. The shape:

  ````
  - **<file>:<line>** — <problem>. _Fix:_ <suggestion>
    ```latex
    <the exact .tex source line(s), copied verbatim — formatting preserved>
    ```
  ````

  - **Always quote the raw `.tex`** for a line-specific finding, in a fenced
    `latex` code block directly under the bullet. Copy it **verbatim** (backslashes,
    braces, `%`, `&`, `$`, and all) — never paraphrase, re-indent, or "tidy it up";
    the author has to recognize and locate the exact text. Quote only the relevant
    line(s): a row or two of a long table, the one offending sentence — not a whole
    page.
  - **Omit** the `:line` *and* the quote only when a finding isn't line-specific (a
    whole-bib summary, the page-count verdict, a missing mandatory section).
  - For a **two-sided** finding (text ↔ table, abstract ↔ results), cite both
    `file:line`s and quote **each** side in its own `latex` block (label each with a
    `% <file>:<line>` comment) so the author sees both without hunting.
- Group by severity using these exact headings (emoji included) so the HTML can
  style them: `## 🔴 Desk-reject risk`, `## 🟠 Reviewers will frown`,
  `## 🔵 Optional polish`.
- Within a severity section, use `### <check name>` subheadings (e.g.
  `### Anonymization`, `### Bibliography — existence`).
- Keep each finding self-contained and concrete; quote the offending text when
  short. Don't summarize away duplicates — list each occurrence (the user asked
  for no omission), but you may collapse "and N more like this" after ~10 of the
  same kind, keeping the count exact.

## Skeleton

````markdown
# Before-Submit Report — <main.tex / paper title>

_Generated: <YYYY-MM-DD HH:MM> · Venue: <venue year, track> (rules: <live CfP | snapshot YYYY>) · Version: <review | camera-ready>_

## Summary
- 🔴 Desk-reject risks: <N>
- 🟠 Reviewers will frown: <N>
- 🔵 Optional polish: <N>

## 🔴 Desk-reject risk
### <check>
- **<file>:<line>** — <problem>. _Fix:_ <suggestion>
  ```latex
  <verbatim offending source>
  ```

## 🟠 Reviewers will frown
### <check>
- **<fileA>:<line> ↔ <fileB>:<line>** — <two-sided problem>. _Fix:_ <suggestion>
  ```latex
  % <fileA>:<line>
  <verbatim source, side A>
  % <fileB>:<line>
  <verbatim source, side B>
  ```

## 🔵 Optional polish
### <check>
- **<file>:<line>** — <problem>. _Fix:_ <suggestion>
  ```latex
  <verbatim offending source>
  ```

## What I checked / skipped
- ✅ <check> — ran
- ⏭️ Compile + page count — skipped: no pdflatex toolchain (user declined TinyTeX). Verify the page count on Overleaf, or install TinyTeX to enable it. (No engine substituted.)
- ⏭️ <check> — skipped: <reason (offline / user opted out)>

## Venue rules used
- Source: <live CfP url | built-in snapshot (as of YYYY)>
- Page limit: <…> · Double-blind: <…> · Mandatory: <…>
- ⚠️ <if snapshot> Verify against the official CfP: <url>
````

The converter supports headings (#/##/###), bullet lists, **bold**, _italic_,
`inline code`, **fenced code blocks** (triple-backtick — used for the verbatim
`.tex` quotes; rendered literally as a `<pre>`, so LaTeX backticks / `&` / `%` are
safe inside them), [links](url), `---` rules, blockquotes, and simple pipe tables
— stick to those so the HTML renders cleanly.
