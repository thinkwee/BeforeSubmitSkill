# Bibliography Checks (Phase 3)

Operate on the parsed `.bib` entries (there may be several files — Phase 1
resolved them) and the citation keys actually used in the assembled `.tex`.

**Ignore commented-out LaTeX when collecting `\cite` usage.** Strip `%`-comments
and commented-out blocks (`\begin{comment}…\end{comment}`, `\iffalse…\fi`) from
the `.tex` first (`\%` is a literal percent, not a comment). A commented-out
`\cite{key}` does **not** count as a use — so it must not keep an otherwise-unused
entry off the "unused" list, and a commented `\cite` to a non-existent key is
**not** a missing-reference error (it never renders).

## 1. Existence & metadata verification (the anti-hallucination check)

**This is the highest-value check.** AI writing tools invent plausible-looking
references; this confirms each one is real and its metadata is correct.

1. Run `scripts/verify_refs.py <bib1> [<bib2> ...] --json` (see its `--help`).
   It does fast, parallel, multi-source lookup and returns, per entry, one of:
   `verified` / `mismatch` / `unable`, the matched title/authors/year, which
   sources corroborated, and (for preprints) a `published_alt` candidate.
   **Treat this as triage, not the verdict** — it is a fast filter that tells you
   *which* entries need your attention, not the final call on them.
2. For **every flagged entry** — `unable` (not found in any indexed source),
   `mismatch` (found something that disagrees), **or** one carrying a
   `published_alt` — **run a live web search yourself to confirm or refute it**
   before writing anything to the report. The machine flag is a lead; your
   web-confirmed judgment is what ships. To adjudicate:
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

**Retraction status is inherently time-sensitive — verify it live, never from
memory.** A paper that was in good standing as of your training cutoff may have
been retracted since; the current date (Phase 0) is what matters, not what you
recall. Run the live check; never assert "not retracted" from internal knowledge.

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

## 6. Cite the published version, not arXiv — severity: WARNING

**Policy: if a paper has a peer-reviewed version (conference/journal), cite that,
not the arXiv preprint.** Reviewers expect the version of record; an arXiv cite
where a published one exists reads as careless and loses the venue signal.

- `verify_refs.py` flags preprint entries (`bib_is_arxiv: true`) and, when it
  finds a matching non-preprint record, fills `published_alt` with the venue +
  year + source (it also reads the arXiv `journal_ref`, which arXiv sets once a
  preprint is formally published). The script already guards against title
  collisions (same/similar title used by a survey or book chapter) via author
  overlap + publication-type filtering — but it can still miss or mis-tag.
- **Always web-confirm** the candidate is the *same paper* (same authors, same
  content) before recommending. For preprints with **no** `published_alt`, still
  do a quick check (DBLP / Google Scholar / the venue's proceedings) for an
  obviously-published key reference — `journal_ref` and indexes lag.
- **A preprint may have been published *after* your training cutoff** — so "I
  don't recall a published version" proves nothing. Decide solely from the live
  search and `journal_ref` as of today's date (Phase 0), never from memory.
  Likewise, whether an arXiv id is "brand-new and not yet indexed" (a legitimate
  reason verify_refs returns `unable`, see §1) is a judgment about *recency* —
  measure it against today's date, not your sense of what's recent.
- Report each as: `cite <Venue Year> instead of arXiv:<id>` with the corrected
  `@inproceedings`/`@article` skeleton when you can produce it. **ask-first** (it
  rewrites a bib entry). For workshop/non-archival venues, leaving the arXiv cite
  is fine — note the choice rather than forcing it.

## 6b. Preprint ratio — severity: INFO

Detect arXiv/bioRxiv/SSRN/preprint entries. If they exceed ~50% of *cited*
references, note it (reviewers may read it as thin grounding); combined with §6,
this usually means several should move to their published versions.

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
