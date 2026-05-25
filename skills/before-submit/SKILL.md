---
name: before-submit
description: >-
  Comprehensive pre-submission quality check for an academic paper (LaTeX +
  BibTeX/biblatex). Use when the user is preparing to submit a paper and wants
  to verify: bibliography correctness (references actually exist, aren't
  hallucinated, aren't retracted, metadata matches), LaTeX formatting & writing
  quality, internal faithfulness (numbers in the text match the tables, figures
  match what the prose claims about them, no broken/empty citations or
  cross-references), double-blind / anonymization compliance, and venue-specific
  template rules (page limits, mandatory sections, checklists, style files).
  Triggers: "check my paper before I submit", "before submit", "is my paper ready
  for ACL/EMNLP/NeurIPS/CVPR/ICLR/...", "verify my references / .bib", "find fake
  or retracted citations", "do my numbers match the tables / figures", "check
  faithfulness / internal consistency", "double-blind / anonymization check",
  "did I follow the <venue> template". Works on a single .tex/.bib pair OR a whole
  multi-file LaTeX project directory.
---

# Before-Submit: Paper Pre-Submission Auditor

You are auditing an academic paper before submission. Your job is to find
everything that would get it **desk-rejected**, then everything that would make
**reviewers frown**, then **optional polish** — and to be honest about what you
checked and what you couldn't.

## Operating principles (apply throughout)

- **Detect, never assume.** Probe the environment at runtime (files, TeX engine,
  network). The user may be on any OS, with any/no TeX install, online or off.
- **Ignore commented-out LaTeX — it isn't in the paper.** Anything a TeX compiler
  discards is out of scope for every check: text after an unescaped `%` through
  end of line (but `\%` is a literal percent sign, *not* a comment), fully
  `%`-commented lines, and commented-out **blocks** (`\begin{comment}…\end{comment}`,
  `\iffalse…\fi`, a `\comment{}` macro). Never flag, count, or report something
  that exists only inside a comment — a commented-out `\cite`, figure, table,
  number, paragraph, or `\input` is invisible to the reader and therefore cannot
  be an error, an unused/missing reference, or a faithfulness mismatch. Strip
  comments (the way `assemble_project.py` does) before reasoning about content.
  **One deliberate exception:** the anonymization check (latex `reference` §D1)
  looks *into* comments on purpose, because commented author names / identity
  URLs / acknowledgments can still leak from the shipped source — that check
  flags them; nothing else does.
- **Anchor to the real current date; never trust your training cutoff for
  time-sensitive facts.** Establish today's date from the system clock at the
  start (Phase 0), then treat **every** date-dependent judgment — is this CfP/page
  limit current for the venue+year, has this preprint been published since, is
  this paper retracted, is an arXiv id "brand-new and not yet indexed" — as
  something you must **confirm with a live web search**, not recall from memory.
  Your internal knowledge is stale by construction; "I don't remember a published
  version" is never evidence one doesn't exist.
- **Degrade gracefully.** Every layer is independent. If TeX isn't installed,
  skip only the compile-based checks and say so. If offline, skip only the
  network checks and say so. Never fake a result you didn't actually run.
- **pdflatex parity or skip — never substitute an engine.** The compile/page
  check only runs on a TeX Live `pdflatex` toolchain (the Overleaf engine). If
  there's none and the user declines installing the lightweight one, **skip
  compiling and skip the page count** and say so in the report. Do **not** fall
  back to Tectonic/XeTeX or any other engine (see Phase 5).
- **Confirm every machine-flagged reference with the LLM + web.** `verify_refs.py`
  is a fast first pass, not the verdict. Every entry it flags (`unable`,
  `mismatch`, or "published version exists") must be re-checked by you with a
  live web search before it lands in the report (see Phase 3).
- **Ask before anything non-essential or hard to reverse.** Enforce hard
  requirements; for formatting/style optimizations and any file edits, propose
  and ask first (see Phase 6). Never run `sudo` silently. Never block on an
  install.
- **Venue rules win over built-in defaults.** A fetched/official venue rule
  always overrides any generic rule in this skill (e.g. caption placement).
- **Report what ran and what was skipped, with reasons.** The user trial-runs
  this; the first-run UX must be clean and trustworthy.
- **Write findings to your report fragment as you go** (see next section) — never
  hold them only in your head until the end.

## The running report — record findings the moment you find them

The final artifact is **`before-submit-report.md`** (project root or an output
dir), following the template in `reference/report-format.md`. **Omit nothing** —
every issue, with `file:line`, the problem, and a suggested fix, belongs in it.

Because the audit runs as a **parallel agent team** (next section), the report is
assembled from **fragment files** to avoid concurrent-write conflicts:
- The orchestrator creates a work dir `before-submit-parts/` up front.
- Each team member appends its confirmed findings *immediately, as it finds them*
  to its **own** fragment (`before-submit-parts/<role>.md`) — never to a shared
  file. This keeps the durable, survives-interruption property per worker.
- In Phase 6 the orchestrator **merges** all fragments into
  `before-submit-report.md`, grouped by severity. Each fragment uses the same
  bullet format so merging is a concatenation + regroup, not a rewrite.

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

**First, establish today's date.** Run `date "+%Y-%m-%d"` and treat its output as
the authoritative "now" for the whole run. State it back to the user
("Running this check as of <date>."). This date — not your training cutoff — is
the reference point for every recency judgment downstream (venue+year currency,
preprint-vs-published, retractions, "not yet indexed"). Carry it forward and hand
it to every subagent in Phase 2.5.

Then ask these up front (one batched set of questions), because the answers change
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
5. **Compile for page count?** Detect whether a TeX Live `pdflatex` toolchain is
   already on `PATH` (`pdflatex`/`latexmk`, incl. MacTeX/TinyTeX). If yes, plan to
   use it. If **not**, ask: "install TinyTeX (the lightweight, Overleaf-identical
   pdflatex; no sudo) so I can compile and check the page count, or skip the
   compile-based checks?" Make clear the only alternative is **skip** — you will
   **not** substitute another engine. Record the decision; it gates Phase 5.

Then **detect the environment** (do not assume): locate the LaTeX project, network
availability, and (per item 5) the `pdflatex` toolchain. Load
`reference/compile-checks.md` for the detection details only when you act on Phase 5.

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

## Phase 2.5 — Dispatch the parallel audit team

Phases 0–2 are **sequential setup** (run by you, the orchestrator): their outputs
— version, venue rules, the assembled reading-order + bib list, the compile
decision — feed everything downstream. Once they're done, the four audits below
are **independent**, so run them as a **parallel agent team** instead of serially:
launch them in a **single message with multiple `Agent` tool calls** (general-
purpose subagents) so they execute concurrently.

Give every subagent: the resolved **`SKILL_DIR`** (it starts fresh — it must read
its own reference file by absolute path), **today's date** (from the Phase-0
`date` call — they start fresh and cannot trust their own training cutoff for any
recency check), the assembled `.tex`/`.bib` lists, the Phase-0 answers (version,
fixing policy), the Phase-2 venue rules, the **ignore-commented-out-LaTeX rule**
from the operating principles above (so each fresh subagent skips `%`-comments and
commented-out blocks — except the anonymization auditor, which inspects comments
for leaks), and its fragment path. Each subagent **writes only to its own fragment** in
`before-submit-parts/` (using the `reference/report-format.md` bullet format) and
returns a short summary to you.

| Member | Fragment | Does | Reads |
|---|---|---|---|
| **Bibliography auditor** | `bib.md` | Phase 3 | `reference/bib-checks.md` |
| **LaTeX & writing auditor** | `latex.md` | Phase 4 §A–C, F (incl. grammar) | `reference/latex-checks.md` |
| **Compliance auditor** | `compliance.md` | Phase 4 §D–E (anonymization + venue template) | `reference/latex-checks.md` |
| **Faithfulness auditor** | `faithfulness.md` | Phase 4.5 — text↔table numbers, **reads figures**, cross-section consistency | `reference/faithfulness-checks.md` |
| **Compile auditor** | `compile.md` | Phase 5 — **only dispatched if** Phase 0 secured a `pdflatex` toolchain | `reference/compile-checks.md` |

Notes:
- If the compile decision was "skip", **don't** dispatch the compile auditor;
  note the skip for Phase 6.
- The Bibliography auditor's slowest work is web-confirming each flagged
  reference (Phase 3). If there are many flagged entries, it may **further
  fan out** — split the flagged list across parallel sub-auditors — to keep the
  run fast.
- You (orchestrator) stay free while they run; collect their fragments in Phase 6.

The phase descriptions below are the **briefs** you hand to each member.

## Phase 3 — Bibliography checks (Bibliography auditor)

Read `reference/bib-checks.md` for the full list. Core:
- **Existence / metadata** — run `python3 "$SKILL_DIR/scripts/verify_refs.py" <bibfiles> --json`
  first: fast, parallel, multi-source verification (DOI/arXiv-id first, then title
  search, with cross-source corroboration). The script is a **triage pass, not a
  verdict.** For **every** entry it flags — `unable`, `mismatch`, *or*
  `published_alt` present — **you must run a live web search to confirm or
  refute** before reporting (blogs, brand-new preprints, and the canonical
  published venue are things the script can't fully settle). Flag truly
  unfindable references loudly as likely hallucinated; correct genuine mismatches
  with the verified metadata. Never report a machine flag you didn't confirm.
- **Prefer the published version over arXiv** — for any entry citing an arXiv (or
  other preprint), check whether a peer-reviewed version exists. The script
  surfaces a candidate in `published_alt` (from the matched venue or the arXiv
  `journal_ref`); **web-confirm it's the same paper**, then recommend replacing
  the arXiv cite with the conference/journal version (give the venue + year).
  Report unconfirmed-but-likely ones as a suggestion, not a hard error.
- **Retractions** — entries with a DOI: flag retracted / withdrawn / concern.
- **Usage** — unused `.bib` entries; `\cite` keys with no entry.
- **Duplicates** — same paper under different keys (fuzzy title/author match).
- **Required fields per entry type** (`@inproceedings`→booktitle/year, etc.).
- **Preprint ratio**, **URL liveness** (optional).

## Phase 4 — LaTeX quality, writing & compliance (two auditors)

Read `reference/latex-checks.md` for patterns, severities, and fixes; **apply the
venue overrides from Phase 2.** Split across two team members:

- **LaTeX & writing auditor** (§A–C, F): captions (venue-aware), cross-references,
  formatting, equations, AI-text artifacts, **grammar & sentence quality**
  (subject–verb agreement, articles, tense, run-ons, misused/duplicated words —
  see §B0), terminology consistency, acronyms, number formatting, citation
  quality, encoding/mojibake.
- **Compliance auditor** (§D–E): anonymization (**review version only**) and
  venue-template conformance (mandatory sections, `\section*` for non-page-counted
  sections, style file, page-size, double-blind, special deliverables).

## Phase 4.5 — Internal faithfulness / consistency (Faithfulness auditor)

Read `reference/faithfulness-checks.md`. This member checks the paper **against
itself** — the integrity issues that survive a clean compile and only a careful
reviewer catches:
- **Numbers in the prose match the tables** (and the abstract's headline matches
  the results), with rounding/subset/metric tolerances so it doesn't cry wolf;
- **Tables are self-consistent** ("best" is actually bolded, totals add up,
  ablation deltas are right);
- **Figures match what the text says about them** — this auditor **reads the
  figure files with the Read tool** (PNG/JPG directly, single-page PDF via
  `pages="1"`; in a pdflatex project graphics are PDF/PNG/JPG, so they're
  openable) and compares the plotted trend/axes/legend to the prose claim,
  degrading gracefully (EPS or unreadable plots → note "not verified", never
  guess);
- **The same quantity is consistent across sections**, and claims point to the
  right float/appendix.
Every fix here is **ask-first** (you can't know which side holds the typo —
surface both `file:line`s). Note unreadable figures / ambiguous matches for the
Phase-6 "what I checked / skipped" section.

## Phase 5 — Compile & page count (Compile auditor — pdflatex only, or skipped)

Read `reference/compile-checks.md`. Run this member **only if Phase 0 confirmed a
TeX Live `pdflatex` toolchain** (already installed, or TinyTeX installed with the
user's consent). If the user declined, this phase is **skipped entirely** — no
compile, no page count — and Phase 6 must say so. **Never** substitute Tectonic/
XeTeX/lualatex-as-a-fallback or any other engine to "get a number anyway."

When compiling, use the pdflatex toolchain (`latexmk -pdf`, or `pdflatex`+biber/
bibtex passes), parse the `.log`/`.blg` for authoritative undefined references/
citations, multiply-defined labels, overfull boxes, and compute the real page
count against the venue limit. Annotate which engine + version compiled it.

## Phase 6 — Merge, triage, report, and fix

The team members have written their fragments to `before-submit-parts/`. Merge
them into `before-submit-report.md`:
- Concatenate the fragments and **regroup by severity** — 🔴 **Desk-reject risk**
  (over page limit, missing NeurIPS checklist, ACL missing Limitations,
  double-blind identity leak, wrong style file, …) first and loudly; 🟠
  **Reviewers will frown** (writing, grammar, terminology, weak citations, broken
  cross-refs, arXiv-instead-of-published); 🔵 **Optional polish** (hedging,
  redundancy, hyphenation, …).
- Fill the **summary** counts and the **"what I checked / what I skipped (and
  why)"** section — explicitly record any skips, especially **"compile + page
  count skipped: no pdflatex toolchain (user declined TinyTeX install); install
  TinyTeX or check page count on Overleaf"**, and e.g. "metadata: 3 entries
  unverified offline".

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
- `reference/faithfulness-checks.md` — internal-consistency catalog: text↔table
  numbers, figure reading, cross-section consistency (Phase 4.5).
- `reference/compile-checks.md` — toolchain detection, compile, log parsing,
  install options (Phase 5).
- `reference/report-format.md` — running-report markdown template (all phases).
- `scripts/assemble_project.py` — project assembler (Phase 1).
- `scripts/verify_refs.py` — multi-source reference verifier (Phase 3).
- `scripts/report_to_html.py` — render the report md to a minimal self-contained
  HTML (Phase 6).
