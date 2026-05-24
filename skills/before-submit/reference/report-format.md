# Running report format (`before-submit-report.md`)

Create this file at the start of the run and **append findings as you confirm
them**. The HTML step (`scripts/report_to_html.py`) renders exactly this file,
so anything not in the md won't be shown — **put every issue here**.

## Conventions

- One finding = one bullet: `` - **<file>:<line>** — <problem>. _Fix:_ <suggestion> ``
  (omit `:line` when not line-specific, e.g. a whole-bib or page-count issue).
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

```markdown
# Before-Submit Report — <main.tex / paper title>

_Generated: <YYYY-MM-DD HH:MM> · Venue: <venue year, track> (rules: <live CfP | snapshot YYYY>) · Version: <review | camera-ready>_

## Summary
- 🔴 Desk-reject risks: <N>
- 🟠 Reviewers will frown: <N>
- 🔵 Optional polish: <N>

## 🔴 Desk-reject risk
### <check>
- **<file>:<line>** — <problem>. _Fix:_ <suggestion>

## 🟠 Reviewers will frown
### <check>
- **<file>:<line>** — <problem>. _Fix:_ <suggestion>

## 🔵 Optional polish
### <check>
- **<file>:<line>** — <problem>. _Fix:_ <suggestion>

## What I checked / skipped
- ✅ <check> — ran
- ⏭️ <check> — skipped: <reason (no TeX / offline / user opted out)>

## Venue rules used
- Source: <live CfP url | built-in snapshot (as of YYYY)>
- Page limit: <…> · Double-blind: <…> · Mandatory: <…>
- ⚠️ <if snapshot> Verify against the official CfP: <url>
```

The converter supports headings (#/##/###), bullet lists, **bold**, _italic_,
`inline code`, [links](url), `---` rules, blockquotes, and simple pipe tables —
stick to those so the HTML renders cleanly.
