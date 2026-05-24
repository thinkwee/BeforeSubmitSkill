# Running report format (`before-submit-report.md`)

The audit runs as a parallel team, so findings land in **fragment files** first,
then get merged:
- Each team member appends findings to its **own** fragment as it confirms them —
  `before-submit-parts/{bib,latex,compliance,compile}.md` — using the
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
- ⏭️ Compile + page count — skipped: no pdflatex toolchain (user declined TinyTeX). Verify the page count on Overleaf, or install TinyTeX to enable it. (No engine substituted.)
- ⏭️ <check> — skipped: <reason (offline / user opted out)>

## Venue rules used
- Source: <live CfP url | built-in snapshot (as of YYYY)>
- Page limit: <…> · Double-blind: <…> · Mandatory: <…>
- ⚠️ <if snapshot> Verify against the official CfP: <url>
```

The converter supports headings (#/##/###), bullet lists, **bold**, _italic_,
`inline code`, [links](url), `---` rules, blockquotes, and simple pipe tables —
stick to those so the HTML renders cleanly.
