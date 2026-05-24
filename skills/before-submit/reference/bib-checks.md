# Bibliography Checks (Phase 3)

Operate on the parsed `.bib` entries (there may be several files — Phase 1
resolved them) and the citation keys actually used in the assembled `.tex`.

## 1. Existence & metadata verification (the anti-hallucination check)

**This is the highest-value check.** AI writing tools invent plausible-looking
references; this confirms each one is real and its metadata is correct.

1. Run `scripts/verify_refs.py <bib1> [<bib2> ...] --json` (see its `--help`).
   It does fast, parallel, multi-source lookup and returns, per entry, one of:
   `verified` / `mismatch` / `unable`, plus the matched title/authors/year and
   which sources corroborated.
2. For every entry the script marks **`unable`** (not found in any indexed
   source) or **`mismatch`** (found something, but it disagrees), **use your own
   web search** to adjudicate:
   - Search the exact title (quoted) + first author. Confirm it exists, and
     whether the venue/year/authors in the `.bib` are right.
   - `unable` is common and *legitimate* for: brand-new arXiv preprints not yet
     indexed, blog posts, technical reports, documentation, software, standards.
     Don't cry "fake" — verify, then classify.
   - A genuine **mismatch** (e.g. wrong year by ≥2, wrong title, wrong venue) →
     report as WARNING with the corrected metadata.
   - A reference you **cannot find anywhere** after web search → 🔴 likely
     hallucinated; report loudly with what you searched.
3. **Interpreting mismatches (avoid false positives):**
   - Year off by ≤1 → preprint vs published; treat as match, note it.
   - Author list truncated differently across sources → check first authors only.
   - Venue abbreviation vs full name ("NeurIPS" vs "Neural Information…") → fine.
   - The script already applies these tolerances; mirror them in your judgment.

(The verification strategy/thresholds the script implements are documented in
the project memory `reference-verification-recipe`; you don't need to re-derive
them — just consume the script's output and web-adjudicate the residue.)

## 2. Retractions — severity: ERROR

For entries with a DOI, check retraction status (CrossRef `update-to` relation;
Retraction Watch). Flag **retracted / withdrawn / expression-of-concern** papers
— citing one is a serious problem. `verify_refs.py --retraction` covers entries
with a DOI; for the rest, a quick web search of the title + "retracted" is a
cheap sanity check on key references.

## 3. Usage analysis — severity: WARNING (unused) / ERROR (missing)

- **Unused** `.bib` entries (present but never `\cite`d) → WARNING; offer to emit
  a cleaned `.bib` of only-cited entries.
- **Missing**: `\cite{key}` with no matching `.bib` entry → ERROR (will render as
  `[?]` / break the bibliography). Cross-check against compile `.blg`/`.log` if
  you compiled (Phase 5) — that's authoritative.
- Count `\cite`/`\citep`/`\citet`/`\citeauthor`/`\autocite`/`\parencite`/etc.

## 4. Duplicates — severity: WARNING

Same paper under different keys. Fuzzy-match on normalized title (≥0.85 similar)
or combined title+author (≥0.80). Report the group; recommend merging to one key.

## 5. Required fields per entry type — severity: WARNING

Missing fields make BibTeX render broken/incomplete entries. Check by type:
- `@article` → author, title, journal, year (volume/number/pages recommended)
- `@inproceedings`/`@conference` → author, title, booktitle, year
- `@book` → author/editor, title, publisher, year
- `@incollection` → author, title, booktitle, publisher, year
- `@phdthesis`/`@mastersthesis` → author, title, school, year
- `@techreport` → author, title, institution, year
- `@misc` → at least title + (author or howpublished/url + year)
Also flag entries missing `year` entirely, or with a non-numeric year.

## 6. Preprint ratio — severity: INFO

Detect arXiv/bioRxiv/SSRN/preprint entries. If they exceed ~50% of *cited*
references, note it (reviewers may read it as thin grounding) and, where a
published version exists (arXiv `journal-ref`/DOI), suggest citing that instead.

## 7. URL liveness (optional, network) — severity: WARNING

For entries with a `url=`, HEAD-then-GET to find dead links (4xx/5xx/unreachable).
Slow on large bibs; run only if the user wants it. Route `arxiv.org` URLs through
the arXiv API rather than HEAD'ing the HTML endpoint.

## 8. LLM citation-relevance + role (Phase 0 opt-in, default ON)

For each citation that is actually used, give the LLM the **surrounding sentence/
paragraph** plus the cited paper's **abstract/title**, and ask:
- `relevance` 1–5 and `is_relevant` (does the cited work actually support the
  claim made at this location?),
- a one-sentence justification,
- a **role**: baseline / method / dataset / counterexample / survey / motivation
  / other.
Report low-relevance (≤2) citations as 🟠 "citation may not support the claim
here", with the location and a short reason. Batch/dedupe contexts to control
cost; cache results so re-runs are cheap.
