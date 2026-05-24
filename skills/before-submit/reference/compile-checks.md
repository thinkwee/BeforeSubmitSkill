# Compile-based Checks (Phase 5) — pdflatex only, or skip

Compiling the paper turns many fuzzy regex checks into **authoritative** ones:
LaTeX/biber themselves report undefined references, undefined citations,
multiply-defined labels, overfull boxes, and the real page count.

**Hard rule: this phase runs on a TeX Live `pdflatex` toolchain (the Overleaf
engine) or not at all.** Overleaf's default compiler is pdflatex; page count,
line breaking, and Type-1 fonts only match Overleaf when we use the same engine.
A different engine (Tectonic/XeTeX) would give a *misleading* page count, so we
**never** fall back to one. If there's no pdflatex and the user won't install the
lightweight option, **skip compiling and skip the page count entirely** and say
so in the report — a stated "skipped" is honest; a wrong number is not.

## 1. Detect the toolchain (never assume)

Probe `PATH` and known locations for a **pdflatex/TeX Live** install only:

```bash
for t in latexmk pdflatex biber bibtex; do
  command -v "$t" >/dev/null 2>&1 && echo "found: $t -> $(command -v $t)"
done
# macOS: also check the MacTeX/BasicTeX symlink dir
ls -l /Library/TeX/texbin/pdflatex 2>/dev/null
```

- **`pdflatex` present** (system TeX Live, MacTeX, BasicTeX, or TinyTeX) → use it.
  Prefer `latexmk -pdf` (drives the right passes + biber/bibtex). This is closest
  to Overleaf.
- **No `pdflatex`** → ASK once (this was raised in Phase 0): install **TinyTeX**
  (the lightest Overleaf-identical pdflatex; see §4), or **skip**. There is no
  third choice — do **not** reach for `tectonic`, `xelatex`, or `lualatex` just to
  produce a number.
- **User skips / install fails** → mark every compile-derived check, *including
  the page-count vs limit*, as **"skipped — no pdflatex toolchain"** in the report,
  and suggest checking the page count on Overleaf instead. Do not estimate it from
  another engine.

(If a template genuinely *requires* xelatex/lualatex, TinyTeX ships those too —
use the engine the template's docs specify, still within the TeX Live install.
The ban is on substituting a *different* TeX distribution like Tectonic, and on
swapping engines merely to dodge a missing pdflatex.)

## 2. Compile

```bash
# latexmk (TeX Live / TinyTeX) — runs the right number of passes + biber/bibtex:
latexmk -pdf -interaction=nonstopmode -outdir=<outdir> <main.tex>
# (only use -xelatex / -lualatex if the template's own docs require that engine)
```

Compile from the project's main-file directory so `\input`/graphics paths
resolve. Use a throwaway output dir; **never overwrite the user's own build**.

## 3. Parse the logs (authoritative findings)

From `<main>.log` (and `.blg` for the bibliography tool):

- **Undefined references** — `LaTeX Warning: Reference `X' on page ... undefined`
- **Undefined citations** — `LaTeX Warning: Citation `X' ... undefined`  (and
  `.blg`: `I didn't find a database entry for ...`)
- **Multiply-defined labels** — `LaTeX Warning: Label `X' multiply defined`
- **Overfull/Underfull boxes** — `Overfull \hbox (NNpt too wide) ...` (large
  overfulls = content spilling into margins; report the worst offenders)
- **Missing packages/files** — `! LaTeX Error: File `X.sty' not found` (see §4
  for on-demand install)
- **Font issues** — Type-3 font warnings (relevant for ICML's Type-1 requirement)

Reconcile these with the Phase-3/4 regex results: the log is ground truth for
undefined refs/citations and missing `.bib` entries.

## 4. Missing packages & install (pdflatex only)

- Once a TeX Live/TinyTeX install exists, parse the log for `File 'X.sty' not
  found` → install with `tlmgr install X` (TinyTeX's `tlmgr` is **sudo-free**) →
  recompile. Loop until it builds or a package genuinely doesn't exist.

If no `pdflatex` exists and the user opts in, install **TinyTeX** — the lightest
option that is *byte-for-byte the same pdflatex as Overleaf* (both are TeX Live).
**Do not offer Tectonic or any non-TeX-Live engine** here; the only choices are
"install a real pdflatex" or "skip". OS-aware, **never sudo silently, never
block**:

| Option | Size | Engine | Install |
|---|---|---|---|
| **TinyTeX** (recommended — lightest pdflatex parity) | ~100 MB dl / ~300 MB | real pdflatex (+xelatex/lualatex/biber), TeX Live | `curl -sL https://yihui.org/tinytex/install-bin-unix.sh | sh` (mac/Linux); PowerShell installer on Windows; no sudo |
| System TeX Live / BasicTeX | 200 MB–few GB | pdflatex (TeX Live) | `apt/dnf/pacman install texlive-*`, `brew install --cask basictex` (needs sudo) — suggest, don't auto-run |

Avoid full MacTeX/TeX Live-full (~5 GB) unless the user explicitly wants it. If
the user declines all of these, **skip Phase 5** — do not install or invoke a
different engine.

## 5. Page count vs the venue limit

Get the page count from the compiled PDF (e.g. `pdfinfo`, a tiny `pypdf`
snippet, or the last shipout in the `.log`). Because we compiled with **pdflatex
(Overleaf's engine)**, this count matches what the user will see on Overleaf.
Compare against the Phase-2 **main-text** limit, remembering what's excluded
(references, appendix, and for the ACL family Limitations/Ethics; the NeurIPS
checklist; ICML impact statement). Because excluded material is interleaved,
state which pages you counted as main text rather than a false-precise verdict.
Over the limit is a 🔴 desk-reject risk at most venues (ICML/ICLR enforce it
strictly).

**If Phase 5 was skipped, do not produce a page count at all** — report
"page count: not checked (no pdflatex)", never an estimate from another engine.

## 6. Always annotate

State in the report: which pdflatex toolchain compiled it (and version) — or, if
you couldn't/didn't compile, exactly which checks (including the page-count
check) were skipped and why, with the suggestion to verify on Overleaf or install
TinyTeX.
