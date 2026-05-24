---
name: before-submit
description: >-
  Comprehensive pre-submission quality check for an academic paper (LaTeX +
  BibTeX/biblatex). Use when the user is preparing to submit a paper and wants
  to verify: bibliography correctness (references actually exist, aren't
  hallucinated, aren't retracted, metadata matches), LaTeX formatting & writing
  quality, double-blind / anonymization compliance, and venue-specific template
  rules (page limits, mandatory sections, checklists, style files). Triggers:
  "check my paper before I submit", "before submit", "is my paper ready for
  ACL/EMNLP/NeurIPS/CVPR/ICLR/...", "verify my references / .bib", "find fake
  or retracted citations", "double-blind / anonymization check", "did I follow
  the <venue> template". Works on a single .tex/.bib pair OR a whole multi-file
  LaTeX project directory.
---

# Before-Submit: Paper Pre-Submission Auditor

You are auditing an academic paper before submission. Your job is to find
everything that would get it **desk-rejected**, then everything that would make
**reviewers frown**, then **optional polish** — and to be honest about what you
checked and what you couldn't.

## Operating principles (apply throughout)

- **Detect, never assume.** Probe the environment at runtime (files, TeX engine,
  network). The user may be on any OS, with any/no TeX install, online or off.
- **Degrade gracefully.** Every layer is independent. If TeX isn't installed,
  skip only the compile-based checks and say so. If offline, skip only the
  network checks and say so. Never fake a result you didn't actually run.
- **Ask before anything non-essential or hard to reverse.** Enforce hard
  requirements; for formatting/style optimizations and any file edits, propose
  and ask first (see Phase 6). Never run `sudo` silently. Never block on an
  install.
- **Venue rules win over built-in defaults.** A fetched/official venue rule
  always overrides any generic rule in this skill (e.g. caption placement).
- **Report what ran and what was skipped, with reasons.** The user trial-runs
  this; the first-run UX must be clean and trustworthy.
- **Write findings to the report file as you go** (see next section) — never
  hold them only in your head until the end.

## The running report — record findings the moment you find them

Create **`before-submit-report.md`** (in the project root, or an output dir) at
the very start of the run, and **append every confirmed finding immediately**,
phase by phase — *not* only at the end. Rationale: a durable, ordered artifact
that survives interruption and is the single source of truth for the Phase 6
summary. Follow the template in `reference/report-format.md`. **Omit nothing** —
every issue, with `file:line`, the problem, and a suggested fix, goes into the md.

## Bundled files & paths (IMPORTANT)

All `reference/…` and `scripts/…` paths below are relative to **this skill's own
directory**, NOT the user's working directory (which is their paper). Resolve them:
- If `$CLAUDE_PLUGIN_ROOT` is set (installed as a plugin), the skill dir is
  `$CLAUDE_PLUGIN_ROOT/skills/before-submit`.
- Otherwise (personal/project skill) it's the directory this SKILL.md was loaded
  from (e.g. `~/.claude/skills/before-submit`).

Set `SKILL_DIR` to that path once, then invoke bundled scripts by absolute path —
`python3 "$SKILL_DIR/scripts/verify_refs.py" …` — and read reference files from
`"$SKILL_DIR/reference/…"`. Never assume the current directory is the skill dir.

## Phase 0 — Scope & setup (ASK the user, then detect)

Ask these up front (one batched set of questions), because the answers change
which checks apply:

1. **Review or camera-ready?** (double-blind anonymization checks only apply to
   the review/submission version.)
2. **Target venue + year + track?** (e.g. "EMNLP 2025, long paper".) Needed for
   page limits, mandatory sections, style file, caption convention.
3. **Run the LLM citation-relevance check?** Default **yes** — it reads each
   citation's context and the cited paper to judge whether the citation actually
   supports the claim. It costs tokens/time, so confirm.
4. **Fixing policy:** may I auto-apply *safe mechanical* fixes (e.g. `et al`→
   `et al.`, `50 %`→`50%`, add `~` before `\cite`), or propose every change as a
   diff for approval? Default: **propose diffs**, never edit without consent.

Then **detect the environment** (do not assume): locate the LaTeX project, and
detect the TeX toolchain (see `reference/compile-checks.md` only when you reach
Phase 5 — don't load it yet).

## Phase 1 — Assemble the project

Papers are rarely one file. Run `python3 "$SKILL_DIR/scripts/assemble_project.py" <dir-or-file>` to:
- find the **main** `.tex` (has `\documentclass` and `\begin{document}`),
- follow `\input{}` / `\include{}` / `\subfile{}` in order to build the document
  in **real reading order**,
- collect every bibliography: `\bibliography{}`, `\addbibresource{}` (biblatex),
  or a `thebibliography` block, and resolve all `.bib` files (there may be
  several),
- report what it assembled so you operate on the whole paper, not a fragment.

If the script is unavailable or errors, fall back to doing this manually with
Glob/Grep. Support **multiple `.tex` and multiple `.bib`**.

## Phase 2 — Resolve venue rules (online-first, snapshot fallback)

Read `reference/venue-rules.md` for the procedure. In short:
1. Try to fetch the **live CfP / author guidelines** for the exact venue+year
   (use the `source_url` in `reference/venues.yaml`, or web-search
   "<venue> <year> call for papers"). Live rules win.
2. If offline or not found, fall back to the bundled snapshot
   `reference/venues.yaml`, and **state clearly** in the report: "used built-in
   snapshot (as of <snapshot_year>), verify against the official CfP: <url>".
3. Record the resolved rules (page limit, double-blind, mandatory sections,
   style file, caption convention, special deliverables) for later phases.

## Phase 3 — Bibliography checks

Read `reference/bib-checks.md` for the full list. Core:
- **Existence / metadata** — run `python3 "$SKILL_DIR/scripts/verify_refs.py" <bibfiles>` first: it
  does fast, parallel, multi-source verification (DOI/arXiv-id first, then title
  search, with cross-source corroboration). For any entry it returns as
  `unable`/unverified, **use your own web search** to confirm or refute it
  (blogs, brand-new preprints, non-academic sources the script can't index).
  Flag hallucinated / non-existent references loudly.
- **Retractions** — entries with a DOI: flag retracted / withdrawn / concern.
- **Usage** — unused `.bib` entries; `\cite` keys with no entry.
- **Duplicates** — same paper under different keys (fuzzy title/author match).
- **Required fields per entry type** (`@inproceedings`→booktitle/year, etc.).
- **Preprint ratio**, **URL liveness** (optional).

## Phase 4 — LaTeX quality checks

Read `reference/latex-checks.md` for patterns, severities, and fixes. Run the
structural/regex checks over the assembled document: captions (venue-aware),
cross-references, formatting, equations, AI-text artifacts, sentence quality,
terminology consistency, acronyms, number formatting, citation quality,
anonymization (review version only), encoding/mojibake, and venue-template
conformance (mandatory sections, `\section*` for non-page-counted sections,
style file, page-size, double-blind). **Apply the venue overrides from Phase 2.**

## Phase 5 — Optional compile (only if useful and possible)

Read `reference/compile-checks.md`. Detect the TeX engine; if none and the user
opts in, offer a lightweight install (Tectonic by default; TinyTeX for exact
pdflatex parity) — otherwise **skip this phase and note it**. When you can
compile, parse the `.log`/`.blg` for authoritative undefined references/
citations, multiply-defined labels, overfull boxes, and estimate page count
against the venue limit. Always annotate which engine compiled it and that
XeTeX-based (Tectonic) page/font results are approximate vs Overleaf's pdflatex.

## Phase 6 — Triage, report, and fix

By now `before-submit-report.md` already holds every finding (you appended them
as you went). Finalize it:
- Confirm findings are grouped by severity — 🔴 **Desk-reject risk** (over page
  limit, missing NeurIPS checklist, ACL missing Limitations, double-blind
  identity leak, wrong style file, …) first and loudly; 🟠 **Reviewers will
  frown** (writing, terminology, weak citations, broken cross-refs); 🔵
  **Optional polish** (hedging, redundancy, hyphenation, …).
- Fill the **summary** counts and the **"what I checked / what I skipped (and
  why)"** section (e.g. "page count skipped: no TeX installed", "metadata: 3
  entries unverified offline").

Then **offer the HTML view**: ask whether to render a minimal, self-contained
HTML of the report. If yes, run
`python3 "$SKILL_DIR/scripts/report_to_html.py" before-submit-report.md -o before-submit-report.html`
— it faithfully renders the *whole* md into one offline file (clean minimal
styling, **no issue dropped**).

For fixes: per the Phase 0 policy, either apply only safe mechanical fixes after
confirmation, or present each change as a diff. **Anything non-mandatory or
stylistic: ask first.** Never modify files the user didn't agree to.

## Reference files (load on demand — progressive disclosure)

- `reference/venue-rules.md` — how to fetch live CfP + use the snapshot.
- `reference/venues.yaml` — offline snapshot of per-venue rules (Phase 2).
- `reference/bib-checks.md` — bibliography check catalog (Phase 3).
- `reference/latex-checks.md` — LaTeX check catalog with patterns + fixes (Phase 4).
- `reference/compile-checks.md` — toolchain detection, compile, log parsing,
  install options (Phase 5).
- `reference/report-format.md` — running-report markdown template (all phases).
- `scripts/assemble_project.py` — project assembler (Phase 1).
- `scripts/verify_refs.py` — multi-source reference verifier (Phase 3).
- `scripts/report_to_html.py` — render the report md to a minimal self-contained
  HTML (Phase 6).
