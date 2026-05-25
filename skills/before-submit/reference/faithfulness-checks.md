# Internal Faithfulness / Consistency Checks (Phase 4.5)

These check the paper **against itself** — do the numbers in the prose match the
tables, do the words describing a figure match what the figure actually shows, is
the same metric reported consistently across abstract/results/conclusion. None of
this is about external sources (that's Phase 3's citation work); it's about
internal integrity, the kind of thing a careful reviewer catches and that
silently survives a clean compile.

Operate on the **assembled** document (Phase 1) so body **and appendix** are in
scope — a number in the appendix table must still match the abstract's headline.
**Skip all commented-out LaTeX first** (`%`-comments respecting `\%`, and
commented-out blocks like `\begin{comment}…\end{comment}` / `\iffalse…\fi`): never
extract a numeric claim, table cell, figure, or `\includegraphics` from a
commented-out region — an old/commented number is not the paper's number and must
not be treated as a mismatch or a stale figure.

## Cardinal rule: tolerate, don't cry wolf

Faithfulness checks generate false positives easily. **Before reporting a
mismatch, rule out the innocent explanations:**
- **Rounding / precision** — 92.34 in a table vs "92.3" in text is a *match*. Only
  flag when the values genuinely disagree beyond rounding.
- **Different subset / split / condition** — "on the dev set" vs "on test", "for
  the base model" vs the large one. The same-looking metric may be a different
  cell. Confirm the prose and the cell refer to the *same* setting before flagging.
- **Different metric sharing a name** — "accuracy" macro vs micro, F1 vs exact
  match. Don't assume two 90-ish numbers should be equal.
- **Deltas vs absolutes** — "improves by 2.1 points" is `A − B`; compute it from
  the cells rather than expecting "2.1" to appear verbatim.
- **Aggregates** — "on average 85%" is a mean over rows, not any single cell.

When in genuine doubt, report it as a 🔵 *"please double-check"* with both
locations and your reasoning, not a confident 🟠 error. **Every fix here is
ask-first** — you can never know which side (prose or table) holds the typo, so
surface both `file:line`s and let the author decide. Never auto-edit a number.

---

## G1. Text ↔ table numerical consistency — severity: WARNING

- **Extract numeric claims** from prose, abstract, and captions: accuracy/F1/BLEU/
  scores, "+N points", "N% improvement", "reduces by N%", parameter counts, dataset
  sizes, speedups ("2.3× faster"), counts ("we evaluate on 12 datasets").
- **Parse every `tabular`/`tabularx`/`array`** into a cell grid (note the column
  headers and row labels so you know what each cell *means*). Resolve the table to
  its `\caption` / `\label` so a finding can name "Table 3".
- **Cross-check** each prose claim against the relevant cell(s), applying the
  tolerance rules above. Report disagreements as
  `text says X (file:line) but Table N says Y (file:line)`.
- **Escalate to 🔴** when the contradicted number is a *headline* claim — in the
  **title, abstract, or the main results sentence** ("we achieve a new
  state-of-the-art **92.3**") — because a wrong headline number is an integrity
  problem, not a polish issue.

## G2. Table internal self-consistency — severity: WARNING

- **"Best" markup is actually best.** Where a column/row bolds (`\textbf`,
  `\mathbf`, a `\best{}` macro) or underlines the winner, verify the bolded cell is
  truly the max (or min, for error/loss/latency) in its comparison group. A bolded
  non-winner misleads reviewers and is a common copy-paste casualty. Flag with the
  table + the cell that *should* have been marked.
- **Rows/columns sum or average as claimed.** If a row is labelled "Total"/"All"/
  "Avg" or percentages in a group should sum to ~100%, check the arithmetic
  (allow rounding). Flag totals that don't add up.
- **Ablation deltas are consistent** — if a row says "−1.2" relative to full, it
  should equal full − that-row from the same table.

## G3. Text ↔ figure consistency — severity: WARNING (reads the image)

You **can read the figures** — and in a pdflatex project they're in formats you
can open. For each figure the prose makes a *claim* about ("Figure 3 shows
accuracy rises with model size", "the loss plateaus after epoch 10", "method A
(blue) dominates B"):

1. **Locate the graphic.** From the figure's `\includegraphics[...]{path}` (honor
   `\graphicspath`), resolve the real file — try the given name then extensions
   `.pdf .png .jpg .jpeg`. Note multi-panel figures (several `\includegraphics`
   or subfigures).
2. **Read it with the Read tool.** PNG/JPG open directly; a single-page **PDF**
   opens via Read's `pages="1"`. Look at axes (labels, direction, scale), the
   legend, the trend, and any annotated values.
3. **Compare** the prose claim to what the plot shows — trend *direction*
   (rises/falls/plateaus), which series is on top, rough magnitudes, the claimed
   crossover/peak/epoch. Flag contradictions:
   `text says the curve rises (file:line) but Figure N shows it falling`.
4. **Caption ↔ figure** — the caption's described axes / conditions / takeaway
   match the rendered plot.

**Degrade gracefully and say so:**
- `.eps`/`.ps` graphics can't be opened directly — try `pdftoppm`/`gs`/`convert`
  to a PNG if one is on `PATH`; otherwise **skip that figure and note it** ("Fig 4
  is EPS, not read").
- Tiny/dense/multi-panel plots where you can't reliably read the trend → **say you
  couldn't verify it** rather than guessing. A stated "not verified" beats a
  hallucinated contradiction.
- Photos/diagrams/schematics (no quantitative claim) → nothing to check; skip.

## G4. Cross-section number consistency — severity: WARNING / 🔴 if headline

The *same* quantity should carry the *same* value everywhere it appears. Build a
small table of "metric → value → location" as you read, and flag when:
- The **abstract** reports a result that the **experiments** table/section
  contradicts (🔴 — the abstract is the headline).
- The **intro/conclusion** restates a gain ("+3 points") that the results don't
  support.
- A dataset size, model parameter count, or hyperparameter is stated differently
  in two places ("7B" here, "6.7B" there — note it; may be fine).

## G5. Claim ↔ evidence pointer sanity — severity: WARNING

- A sentence asserts a result and points to the **wrong float** — "as shown in
  **Table 2**" where the described content lives in Table 3 (the `\ref` resolves
  fine, so Phase 4's A2 won't catch it; this is a *semantic* mispointer).
- "See Appendix B for the proof" but Appendix B is about something else (or there
  is no Appendix B — A2 catches the missing label; this catches the *mismatched
  topic*).
- Claims of "all/every/N experiments" vs how many actually appear in the tables.

---

## Reporting

Use the standard fragment bullet format (`reference/report-format.md`), one
finding per bullet, prefixed with its severity emoji, and **always cite both
sides** of a mismatch so the author can adjudicate:

```
- 🟠 **results.tex:212 ↔ tables/main.tex:40 (Table 3)** — text claims "92.3 F1" but the Full-model row shows 91.3. _Fix:_ reconcile — confirm which is correct and update the other.
- 🟠 **tables/abl.tex:18 (Table 5)** — "best" is bolded on BERT (88.1) but RoBERTa (89.4) is higher in that column. _Fix:_ move the bold to the true max, or correct the value.
- 🟠 **analysis.tex:77 ↔ figures/scaling.pdf (Figure 4)** — text says accuracy "increases monotonically with size" but the plotted curve dips at 13B. _Fix:_ soften the claim or check the figure.
- 🔵 **intro.tex:9 ↔ exp.tex:140** — abstract says "3-point gain", results table gives 2.6 (rounds to 3?). _Fix:_ please double-check the rounding/claim.
```

Record what you **couldn't** verify (EPS figures, unreadable plots, ambiguous
metric matches) in the Phase-6 "what I checked / skipped" section — honesty about
coverage is part of the deliverable.
