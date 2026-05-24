# before-submit

**A Claude Code skill that audits your academic paper before you submit it.**

It catches the things that get papers desk-rejected or embarrassed in review:
fake / hallucinated / retracted citations, broken LaTeX, double-blind identity
leaks, and violations of the target venue's rules (page limits, mandatory
sections, required checklists). It produces a single, ordered report — and an
optional clean HTML view — and it **never edits your files without asking**.

> Built for the LLM-agent era: AI writing tools invent plausible-but-nonexistent
> references and leave behind conversational artifacts. `before-submit` verifies
> every reference against real databases (and, for anything it can't index, the
> agent's own web search), and sweeps the source for the rest.

---

## What it checks

**Bibliography**
- ✅ **Existence & metadata** — every entry verified against CrossRef, Semantic
  Scholar, OpenAlex, DBLP, and arXiv in parallel, with cross-source
  corroboration. Anything unverifiable is escalated to the agent's web search,
  so genuinely-fake references get flagged loudly.
- 🚫 **Retractions** — DOIs checked for retracted / withdrawn / concern status.
- 🔁 **Duplicates**, **unused entries**, **missing `\cite` keys**, **required
  fields per entry type**, **preprint ratio**, optional **dead-URL** checks.
- 🎯 **Citation relevance** (optional) — does the cited work actually support the
  claim at that spot in the text? Judged by the agent itself (no extra API key).

**LaTeX quality**
- Caption placement (venue-aware), cross-references, citation formatting,
  equations, **AI-text artifacts**, weak/hedging writing, terminology
  consistency, acronym definitions, number formatting, encoding/mojibake.
- **Anonymization** for double-blind: author leaks, identifying URLs,
  acknowledgments, self-revealing phrasing — checked only for the review version.

**Venue compliance** (ACL · EMNLP · NAACL · CVPR · ICCV · ECCV · NeurIPS · ICML · ICLR)
- Page limits, mandatory sections (e.g. ACL **Limitations**), required
  deliverables (e.g. **NeurIPS Paper Checklist**, ICML Impact Statement /
  Type-1 fonts), style file, paper size, caption convention.
- **Live-first**: fetches the venue's current Call for Papers when online, and
  falls back to a bundled snapshot otherwise — always telling you which it used.

**Optional compile** — if a TeX engine is available (or you let it install a
lightweight one), it compiles and reads the logs for authoritative undefined
references/citations, multiply-defined labels, overfull boxes, and a page-count
estimate vs the venue limit.

Findings are written to **`before-submit-report.md`** as they're found (so nothing
is lost), grouped into 🔴 desk-reject risk · 🟠 reviewers will frown · 🔵 optional
polish — and you can render a minimal, self-contained **HTML** view of it.

---

## Install

### Option A — as a plugin (recommended)

In Claude Code:

```
/plugin marketplace add thinkwee/BeforeSubmitSkill
/plugin install before-submit@thinkwee
```

Start a new session, then just ask Claude to *"run before-submit on my paper"*
(or pick the skill from the `/` menu).

### Option B — as a personal skill (manual)

```bash
git clone https://github.com/thinkwee/BeforeSubmitSkill.git
cp -r BeforeSubmitSkill/skills/before-submit ~/.claude/skills/before-submit
```

Restart Claude Code; the skill is then available in every project.

---

## Usage

Point it at a single `.tex`/`.bib` pair **or a whole project directory**. On the
first run it asks a few quick questions:

1. Review (double-blind) or camera-ready?
2. Target venue + year + track?
3. Run the citation-relevance check? (default yes)
4. May it auto-apply *safe* mechanical fixes, or propose every change as a diff?

Then it assembles the project (following `\input`/`\include`, resolving every
`.bib`), resolves the venue rules, runs the checks while streaming findings into
the report, and finally offers the HTML view. **Your source files are never
modified unless you approve a specific change.**

---

## Requirements

- **Claude Code** (with skills/plugins support).
- **Python 3.8+** for the bundled scripts — **standard library only, nothing to
  `pip install`**.
- *Optional:* a TeX engine for compile-based checks. None installed? The skill
  detects that and offers a lightweight option (Tectonic, or TinyTeX for exact
  pdflatex parity) — and works fine without one, just skipping those checks.
- *Optional:* network for database verification and live CfP fetch (it degrades
  gracefully offline). Set `BEFORE_SUBMIT_CONTACT_EMAIL` and
  `SEMANTIC_SCHOLAR_API_KEY` to lift API rate limits.

---

## How it works

```
skills/before-submit/
├── SKILL.md            # orchestration: 7 phases, progressive disclosure
├── reference/          # loaded on demand, per phase
│   ├── venues.yaml     # offline venue-rules snapshot (live CfP wins when online)
│   ├── venue-rules.md  ·  bib-checks.md  ·  latex-checks.md
│   ├── compile-checks.md  ·  report-format.md
└── scripts/            # stdlib-only, run anywhere with python3
    ├── assemble_project.py   # find main .tex, follow includes, map .bib
    ├── verify_refs.py        # parallel multi-source reference verifier
    └── report_to_html.py     # render the report markdown to one HTML file
```

`SKILL.md` stays small and tells the agent which reference file to read for each
phase, so detailed catalogs and data load only when needed.

---

## Contributing

Contributions are very welcome — especially **keeping `reference/venues.yaml`
current** and **adding new venues**. See [CONTRIBUTING.md](CONTRIBUTING.md) for
the data schema and how to add checks. If `before-submit` saved your submission,
a ⭐ helps others find it.

## License

[MIT](LICENSE) © 2026 thinkwee
