# Compile-based Checks (Phase 5) — optional, best-effort

Compiling the paper turns many fuzzy regex checks into **authoritative** ones:
LaTeX/biber themselves report undefined references, undefined citations,
multiply-defined labels, overfull boxes, and the real page count. This phase is
**optional** and must **degrade gracefully** — if there's no usable TeX and the
user doesn't want to install one, skip it and say so.

## 1. Detect the toolchain (never assume)

Probe `PATH` and known locations, in this preference order:

1. `latexmk` (best — handles the multi-pass + bibtex/biber dance automatically)
2. `pdflatex` / `xelatex` / `lualatex` (TeX Live = the Overleaf engine)
3. `tectonic` (self-contained; auto multi-pass + biber + on-demand packages)

```bash
for t in latexmk pdflatex xelatex lualatex tectonic biber bibtex; do
  command -v "$t" >/dev/null 2>&1 && echo "found: $t -> $(command -v $t)"
done
# macOS: also check the MacTeX symlink dir
ls -l /Library/TeX/texbin/pdflatex 2>/dev/null
```

- **TeX Live present** → use it (closest to Overleaf). Prefer `latexmk -pdf`
  (or `-xelatex`/`-lualatex` to match the template).
- **Only Tectonic present** → use it. Note in the report that it's **XeTeX-based,
  not pdflatex**, so page-count and Type-1-font results are *approximate* vs
  Overleaf, and a few pdflatex-only templates may not build.
- **Nothing present** → ASK the user whether to install (see §4) or skip. If they
  skip, mark all compile-derived checks as "skipped (no TeX toolchain)".

## 2. Compile

```bash
# Tectonic (zero-config; fetches missing packages on first run; needs network once):
tectonic --keep-logs --keep-intermediate-files -o <outdir> <main.tex>

# latexmk (TeX Live) — runs the right number of passes + biber/bibtex:
latexmk -pdf -interaction=nonstopmode -outdir=<outdir> <main.tex>
# (use -xelatex or -lualatex if the template requires it)
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

## 4. Missing packages & optional install

- **Tectonic** auto-downloads missing packages (needs network on first build).
- **TeX Live / TinyTeX**: parse the log for `File 'X.sty' not found` → install
  with `tlmgr install X` (TinyTeX's `tlmgr` is **sudo-free**) → recompile. Loop
  until it builds or a package genuinely doesn't exist.

If no toolchain exists and the user opts in, offer (OS-aware, **never sudo
silently, never block**):

| Option | Size | Engine | Install |
|---|---|---|---|
| **Tectonic** (recommended default) | ~15–30 MB binary + on-demand cache | XeTeX (≠ pdflatex) | `brew install tectonic` · `conda install -c conda-forge tectonic` · `cargo install tectonic` · scoop/winget · prebuilt binary |
| **TinyTeX** (recommended for pdflatex parity) | ~100 MB dl / ~300 MB | real pdflatex+xelatex+lualatex+biber (TeX Live) | `curl -sL https://yihui.org/tinytex/install-bin-unix.sh | sh` (mac/Linux); PowerShell installer on Windows; no sudo |
| System TeX Live / BasicTeX | 200 MB–few GB | pdflatex | `apt/dnf/pacman install texlive-*`, `brew install --cask basictex` (needs sudo) — suggest, don't auto-run |

Avoid full MacTeX/TeX Live-full (~5 GB) unless the user explicitly wants it.

## 5. Page count vs the venue limit

Get the page count from the compiled PDF (e.g. `pdfinfo`, a tiny `pypdf`
snippet, or the last shipout in the `.log`). Compare against the Phase-2
**main-text** limit, remembering what's excluded (references, appendix, and for
the ACL family Limitations/Ethics; the NeurIPS checklist; ICML impact statement).
Because excluded material is interleaved, treat the count as an **estimate** and
say so — flag "likely over by ~N pages", not a false-precise verdict. Over the
limit is a 🔴 desk-reject risk at most venues (ICML/ICLR enforce it strictly).

## 6. Always annotate

State in the report: which engine compiled it (and version), that Tectonic/XeTeX
page/font numbers are approximate, and — if you couldn't compile — exactly which
checks were skipped and why.
