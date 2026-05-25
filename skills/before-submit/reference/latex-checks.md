# LaTeX Quality Checks (Phase 4)

Run these over the **assembled** document (Phase 1), skipping **all commented-out
LaTeX** — text after an unescaped `%` (respecting `\%`), fully `%`-commented lines,
and commented-out blocks (`\begin{comment}…\end{comment}`, `\iffalse…\fi`) — plus
verbatim/listing environments. Commented-out content is invisible to the reader,
so it is never an error here. (**Exception:** §D1 anonymization deliberately
inspects comments for identity leaks; that is the only check that looks inside
them.) Each check lists: what it flags, how to detect it, severity, the fix, and
whether the fix is **safe-auto** (mechanical, apply after the Phase-0 consent) or
**ask-first** (stylistic/subjective — always propose, never impose).

**Apply venue overrides from Phase 2 before reporting** — a fetched venue rule
beats any default here (especially caption placement and `\section*` usage).

## How to run these — two tiers, don't grep the semantic ones

The checks split into two kinds and the difference is the whole game:

- **Mechanical** — a regex can *locate* the candidate; you just confirm the
  context. Citation `~`, `et al`→`et al.`, `50 %`→`50%`, number ranges, unescaped
  `&`, mojibake/smart-quotes, `\label`/`\ref` bookkeeping. Pattern-match to find,
  then rule out false positives (math/tabular/verbatim/`%`-comment) before
  reporting.
- **Semantic** — a regex *cannot* judge it; you must **read the assembled prose
  like a reviewer** and decide. Grammar & mechanics (§B0), sentence quality
  (§B2), terminology consistency and whether two spellings are really the same
  term (§B3), whether an acronym is genuinely used-before-defined / defined
  inconsistently (§C1), whether a citation actually fits the claim (§C3), and the
  reference-noun sense in §A5. For these, **grep will both miss real issues and
  invent false ones** — regex is at most a hint for *where* to look, never the
  verdict.

So when a check below says "Detect … pattern", that's the cheap first pass for a
mechanical check; for a semantic one the real work is your reading.

**Two rules for every check below.** (1) **Re-confirm before you report** — a
regex hit or a first impression is a lead, not a verdict; re-open the flagged span
and verify the issue is real *in its context* (not math / tabular / verbatim /
comment, not a `\%` or a macro argument, not a valid stylistic choice). Nothing
ships on a single detection. (2) **Quote the source** — every line-specific finding
pairs its `file:line` with a verbatim quote of the offending `.tex` in a fenced
`latex` block (per `reference/report-format.md`), so the author sees exactly what
you mean.

---

## A. Format

### A1. Caption placement  — severity: ERROR (misplaced) / WARNING (missing)
- Default rule: **table** caption ABOVE the tabular; **figure** caption BELOW the
  graphic. Detect `\caption` position relative to `\begin{tabular}` /
  `\includegraphics` / `\begin{tikzpicture}` inside each `table`/`figure` env.
- **Venue override**: some venues want figure *and* table captions below (the
  user flagged EMNLP). Use the Phase-2 `caption_convention`; only fall back to
  the default if the venue didn't specify.
- Fix: move `\caption{}`. **ask-first** (reordering content).

### A2. Cross-references — severity: ERROR (undefined ref) / WARNING (unref'd float)
- Collect `\label{}`; collect refs (`\ref \autoref \cref \Cref \eqref \pageref
  \nameref`). Report: labels never referenced (figures/tables = WARNING,
  equations = INFO); refs to non-existent labels = ERROR.
- Appendix sections (`\appendix`) not referenced from the main text = WARNING.
- Skip `#1`-style macro params and `\newcommand`/`\renewcommand` bodies.
- The compile pass (Phase 5) is the authoritative source for undefined refs —
  reconcile with `.log` if you compiled.
- Fix: add the missing `\label`/`\ref`. **ask-first**.

### A3. Formatting — severity: WARNING (unescaped &) / INFO (others)
- Citation without non-breaking space: `\w\s+\\cite` → should be `text~\cite{}`.
  Fix `add ~`. **safe-auto**.
- Mixed citation styles (`\citep`/`\citet`/`\cite` together) → INFO. **ask-first**.
- Unescaped special chars outside math/tabular: `&`, `%`, `#`, `_`, `^`. The
  bare `&` outside tabular/array/align is the high-value one (WARNING). Fix:
  escape (`\&`). **safe-auto** for clear cases, but verify it isn't inside a
  math/tabular region first.

### A4. Equations — severity: INFO
- Equation in running text whose next line starts lowercase but the equation
  lacks trailing punctuation → "may need punctuation". **ask-first**.
- Mixed numbered/unnumbered equations (>20% minority of >3 total) → INFO.
- Mixed inline-math delimiters (`$...$` vs `\(...\)`) → INFO. **ask-first**.

### A5. Reference nouns — severity: WARNING (lowercase before a number) / INFO (abbrev style)
Partly **semantic** — read for sense, only flag hand-written nouns; let
`\cref`/`\autoref`/`\Cref` (they auto-generate the noun) off the hook.
- **Capitalize when naming a specific float**: "in Figure 3", "see Section 4",
  "Table 2", "Equation 5" take a capital when followed by a number — lowercase
  "figure 3"/"section 4" naming a numbered float is wrong (WARNING). Skip generic
  uses with no number ("the figure shows…"). **safe-auto** once flagged.
- **Consistent abbreviation**: pick one of `Figure`/`Fig.`, `Section`/`Sec.`,
  `Equation`/`Eq.`, `Appendix`/`App.` (Table is rarely abbreviated) and use it
  throughout the doc; mixing reads as careless (INFO). Respect any venue style
  (some require spelled-out at a sentence start). **ask-first** (abbrev style is a
  preference).

---

## B. Writing quality (all INFO unless noted — these are suggestions)

### B0. Grammar & mechanics — severity: WARNING
Real grammar mistakes (not style) make reviewers frown, so flag them at WARNING.
Regex won't catch most grammar — **read the prose** (the assembled body text,
skipping math/tabular/verbatim/`%`-comments) and flag concrete errors with the
`file:line` and a corrected rewrite. Look for:
- Subject–verb agreement ("the results shows", "these method").
- Article errors (missing/extra/`a` vs `an`: "a important", "the most of").
- Verb tense/form (inconsistent tense in a paragraph; "we have showed"; dangling
  participles; "allows to" → "allows us to").
- Run-on sentences and comma splices; sentence fragments.
- Wrong/confusable words: its/it's, affect/effect, fewer/less, that/which,
  compliment/complement, "comprised of", "the data is" (venue-dependent).
- Duplicated words ("the the", "is is" across a line break), missing words.
- Preposition/idiom errors common in non-native writing ("discuss about",
  "research on the field", "in the literature is shown").
- Punctuation: missing Oxford comma if the venue/house style wants it; stray
  spaces before punctuation; `,` vs `.` in equations (defer to A4).
Don't drown the report — group similar issues and prioritize ones that change
meaning or read as errors. Fix: **ask-first** (it rewrites prose). A LanguageTool
pass is *not* assumed available; do this by reading. Note non-native-fluency
patterns kindly and concretely.

### B1. AI-generated text artifacts — severity: ERROR
- Conversational AI residue: "Sure, here is…", "I'd be happy to", "As an AI
  (language) model", "my knowledge cutoff", "Here's the revised…", "Hope this
  helps", "Let me know if…", "great question", "It's important to note that",
  "Please note that". These must NOT ship → ERROR.
- Placeholders (WARNING): `[insert … here]`, `[add …]`, `[TODO…]`, `TODO:`,
  `FIXME:`, `XXX`, `your.email@example.com`, `[citation needed]`, "author name".
- Markdown remnants (INFO): `**bold**`, `# heading`, `` `code` ``, ``` ```block``` ```,
  `- bullet`, `[text](url)` — skip lines starting with `\` and math lines.
- Fix: remove/replace. **ask-first** (you must not silently delete content), but
  flag ERROR-level AI residue prominently.

### B2. Sentence quality — severity: INFO
- Weak starters: "There is/are…", "It is…", vague "This is…", "As
  mentioned/discussed above".
- Hedging / weasel: "many studies show", "obviously/clearly/it is well known",
  "very/really/highly important", "it is important to note that".
- Redundant phrases: "in order to"→"to", "due to the fact that"→"because", "a
  large number of"→"many", "the vast majority of"→"most", etc.
- Fix: **ask-first** (rewrites are subjective).

### B3. Terminology consistency — severity: WARNING (spelling) / INFO (rest)
- US/UK spelling mixed in the same doc (optimize/optimise, color/colour,
  modeling/modelling, …). Pick one, follow venue's expected English.
- Hyphenation inconsistency (fine-tuning vs finetuning vs fine tuning); respect
  always-hyphenated compounds (state-of-the-art, end-to-end, …).
- Capitalization of technical terms (Transformer vs transformer).
- Augment with the user's glossary if they provide preferred terms.
- Fix: normalize to one form. **safe-auto** for pure spelling variants once the
  user picks the target English; **ask-first** for hyphenation/capitalization.

---

## C. Academic standards

### C1. Acronyms — severity: WARNING
- An acronym (3+ caps) used before/without its definition, **only** when a
  plausible full form appears in the document. Skip a large set of common
  acronyms (GPU, NLP, LLM, API, …) and the user's glossary.
- Detect "Full Name (ACRONYM)" / "(ACRONYM; Full Name)" definitions (allow
  `~` and `\textbf{}`); flag used-before-defined.
- **Defined but never reused** — a "Full Name (ACRONYM)" introduced and then the
  acronym never appears again → INFO (the parenthetical was pointless; use it or
  drop it).
- **Redefined** — the full form spelled out with the acronym a second time later
  → INFO (define once, on first use).
- **Defined inconsistently** — the same acronym mapped to two different full forms
  (or one full form abbreviated two ways) → WARNING.
- These are **read-and-judge**, not pure regex: confirm a parenthetical is a real
  expansion (initials line up) and not a coincidence before flagging.
- Fix: define on first use / unify. **ask-first**.

### C2. Numbers — severity: WARNING / INFO
- Space before percent: `50 %` → `50%` (WARNING). **safe-auto**.
- Mixed `%` and the word "percent" (INFO). **ask-first**.
- **Ranges use an en-dash, not a hyphen**: `10-20`, "pages 3-7", "2019-2021" →
  `10--20`, `3--7`, `2019--2021` (WARNING). Only for clear numeric ranges outside
  math/tabular, and not where the `-` is a minus sign or part of a compound.
  **safe-auto** for unambiguous numeric ranges.
- Skip math/tabular/caption/ref contexts.

### C3. Citation quality — severity: WARNING / INFO
- `et al` without period → `et al.` (WARNING). **safe-auto**.
- Hardcoded `(Smith, 2020)` / `(Smith et al., 2020)` instead of `\cite` when no
  `\cite` on the line (WARNING). **ask-first**.
- Numeric `[1]`-style citations where author-year might be expected (INFO);
  skip `\newcommand`/macro-arg cases.
- Very old references (>30 years) visible in text → INFO ("check for newer work").

---

## D. Review compliance (REVIEW version only — skip for camera-ready)

### D1. Anonymization — severity: ERROR (in body) / WARNING (in comments)
- `\author{}` containing real names (not "Anonymous"/blind macro) → ERROR.
- Identity-revealing URLs (GitHub/GitLab/Twitter/LinkedIn/HuggingFace profiles,
  `*.github.io`, `~user/`, `people.*.edu`) in body → ERROR; in `%` comments →
  WARNING (they can leak on compile). Anonymous-friendly URLs
  (anonymous.4open.science, "anonymous/anon/blind/review/submission") are OK.
- Acknowledgments section present and not commented out → WARNING (omit during
  review; many venues require this).
- Self-revealing phrasing: "our previous work", "as we have shown", `\cite{}` +
  "we propose/show" → WARNING (rephrase to "Prior work shows…").
- Also check PDF metadata leaks: `\hypersetup{pdfauthor=…}`, `\pdfauthor`.
- Fix: anonymize. **ask-first**, but treat ERROR-level leaks as must-fix.

---

## E. Venue-template conformance (uses Phase-2 resolved rules)

- **Mandatory sections** present? (e.g. ACL/EMNLP/NAACL require **Limitations**;
  check it's discussion-only — no floats/sub-sections inside.) Missing = ERROR
  (desk-reject risk).
- **Non-page-counted sections use `\section*`** (unnumbered): Limitations,
  Ethics Statement, Acknowledgments, Reproducibility/Impact statements — per the
  venue. Numbered where it should be `\section*` = WARNING. (Defer to venue.)
- **Camera-ready-only sections** (e.g. ICML Impact Statement) absent → INFO
  reminder, not an error, for the review version.
- **Style file / doc class / paper size** match the venue (e.g. `acl.sty`,
  `neurips_<year>.sty`, `iclr<year>_conference.sty`, `llncs.cls` for ECCV;
  letter vs a4) → WARNING if wrong.
- **Special deliverables**: NeurIPS Paper Checklist present (ERROR / desk-reject
  if missing); ICLR/NeurIPS Reproducibility Statement (INFO); ICML lay summary +
  Type-1 fonts (INFO reminders — Type-1 only verifiable from the compiled PDF,
  see Phase 5).

---

## F. Encoding / mojibake — severity: WARNING

- Non-ASCII punctuation pasted from Word/web that breaks under pdflatex: curly
  quotes `“ ” ‘ ’`, en/em dashes `– —` used as literals, ellipsis `…`,
  non-breaking space U+00A0, zero-width chars.
- Detect literal smart-quote / nbsp bytes outside verbatim. Fix: replace with
  LaTeX equivalents (`` `` '' ``, `--`/`---`, `~`, normal space) — **safe-auto**
  for clear mojibake, but show the user the list first.
- **ASCII straight quotes used as text quotes**: `"word"` in the source renders as
  `”word”` (both closing) under pdflatex — it should be `` ``word'' `` (backtick
  opening, apostrophes closing); likewise `'word'` → `` `word' ``. Flag a straight
  `"` or a leading `'` used as a quotation mark outside verbatim/math/code
  (WARNING). **safe-auto** for clear opening/closing pairs; **ask-first** when
  ambiguous (it may be a prime/inch mark, an apostrophe, or part of a code listing).
