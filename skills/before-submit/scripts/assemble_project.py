#!/usr/bin/env python3
"""
assemble_project.py — find the main .tex, follow \\input/\\include in reading
order, and resolve every .bib, for a single file OR a whole LaTeX project dir.

Stdlib only (portable across environments). Prints a JSON object:

    {
      "root": "...",
      "main": "path/to/main.tex" | null,
      "main_candidates": [...],          # if detection is ambiguous
      "tex_in_order": [...],             # main + \\input/\\include, depth-first, in order
      "bib_files": [...],                # resolved .bib paths
      "bib_backend": "bibtex"|"biblatex"|"embedded"|null,
      "all_tex": [...],                  # every .tex found (dir mode)
      "warnings": [...]
    }

Usage:
    python3 assemble_project.py <dir-or-file.tex>
    python3 assemble_project.py            # defaults to current directory
"""
from __future__ import annotations

import json
import os
import re
import sys

# --- regexes (operate on comment-stripped text) ------------------------------
_DOCCLASS = re.compile(r'\\documentclass\b')
_BEGINDOC = re.compile(r'\\begin\{document\}')
_INPUT = re.compile(r'\\(?:input|include|subfile|import|subimport)\s*\{([^}]+)\}')
_BIB = re.compile(r'\\bibliography\s*\{([^}]+)\}')
_ADDBIB = re.compile(r'\\(?:addbibresource|bibliographyresource)\s*\{([^}]+)\}')
_THEBIB = re.compile(r'\\begin\{thebibliography\}')


def strip_comments(text: str) -> str:
    """Remove % comments (but keep \\%) line by line."""
    out = []
    for line in text.splitlines():
        out.append(re.sub(r'(?<!\\)%.*$', '', line))
    return "\n".join(out)


def read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def resolve(name: str, base_dir: str, root: str, exts) -> str | None:
    """Resolve a \\input/\\bibliography target to an existing file path."""
    name = name.strip().strip('"')
    cands = []
    for stem in (name,):
        has_ext = any(stem.lower().endswith(e) for e in exts)
        variants = [stem] if has_ext else [stem + e for e in exts]
        for v in variants:
            cands.append(os.path.join(base_dir, v))   # relative to including file
            cands.append(os.path.join(root, v))       # relative to project root
    for c in cands:
        if os.path.isfile(c):
            return os.path.normpath(c)
    return None


def find_tex_files(root: str) -> list[str]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        # skip common build/vendor dirs
        dirnames[:] = [d for d in dirnames if d not in
                       {".git", "node_modules", "_minted", "build", "out", ".texpadtmp"}]
        for fn in filenames:
            if fn.lower().endswith(".tex"):
                found.append(os.path.normpath(os.path.join(dirpath, fn)))
    return sorted(found)


def is_main(text_stripped: str) -> bool:
    return bool(_DOCCLASS.search(text_stripped) and _BEGINDOC.search(text_stripped))


def follow_inputs(main: str, root: str, warnings: list[str]) -> list[str]:
    """Depth-first expansion of \\input/\\include in source order."""
    ordered: list[str] = []
    seen: set[str] = set()

    def walk(path: str):
        np = os.path.normpath(path)
        if np in seen:
            return
        seen.add(np)
        ordered.append(np)
        text = strip_comments(read(np))
        base_dir = os.path.dirname(np) or "."
        for m in _INPUT.finditer(text):
            child = resolve(m.group(1), base_dir, root, (".tex",))
            if child:
                walk(child)
            else:
                warnings.append(f"Unresolved \\input/\\include: {m.group(1)!r} (in {os.path.basename(np)})")

    walk(main)
    return ordered


def find_bibs(tex_files: list[str], root: str, warnings: list[str]):
    bib_files: list[str] = []
    backend = None
    saw_cmd = False
    for tf in tex_files:
        text = strip_comments(read(tf))
        base_dir = os.path.dirname(tf) or "."
        for m in _BIB.finditer(text):
            saw_cmd = True
            backend = backend or "bibtex"
            for name in m.group(1).split(","):
                p = resolve(name, base_dir, root, (".bib",))
                if p:
                    bib_files.append(p)
                else:
                    warnings.append(f"Unresolved \\bibliography entry: {name.strip()!r}")
        for m in _ADDBIB.finditer(text):
            saw_cmd = True
            backend = "biblatex"
            p = resolve(m.group(1), base_dir, root, (".bib",))
            if p:
                bib_files.append(p)
            else:
                warnings.append(f"Unresolved \\addbibresource: {m.group(1).strip()!r}")
        if _THEBIB.search(text) and backend is None:
            backend = "embedded"
    # de-dup, keep order
    seen, uniq = set(), []
    for b in bib_files:
        if b not in seen:
            seen.add(b)
            uniq.append(b)
    # dir-mode safety net: if no \bibliography found, surface any .bib lying around
    if not uniq and os.path.isdir(root):
        loose = []
        for dp, dn, fns in os.walk(root):
            dn[:] = [d for d in dn if d not in {".git", "node_modules"}]
            for fn in fns:
                if fn.lower().endswith(".bib"):
                    loose.append(os.path.normpath(os.path.join(dp, fn)))
        if loose:
            if saw_cmd:
                warnings.append("Found \\bibliography/\\addbibresource but couldn't resolve the "
                                "named .bib file(s); listing loose .bib files as a fallback.")
            else:
                warnings.append("No \\bibliography/\\addbibresource found; listing loose .bib files.")
            uniq = sorted(loose)
    return uniq, backend


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "."
    arg = os.path.abspath(arg)
    warnings: list[str] = []

    if os.path.isfile(arg):
        root = os.path.dirname(arg)
        all_tex = [arg]
        # also scan the dir so \input targets and bibs resolve
        if os.path.isdir(root):
            all_tex = sorted(set(all_tex) | set(find_tex_files(root)))
        main_candidates = [arg] if is_main(strip_comments(read(arg))) else []
        if not main_candidates:
            main_candidates = [t for t in all_tex if is_main(strip_comments(read(t)))]
        main_file = arg if (is_main(strip_comments(read(arg))) or not main_candidates) else main_candidates[0]
    elif os.path.isdir(arg):
        root = arg
        all_tex = find_tex_files(root)
        main_candidates = [t for t in all_tex if is_main(strip_comments(read(t)))]
        # prefer a candidate that is NOT \input by another candidate
        included = set()
        for t in main_candidates:
            for m in _INPUT.finditer(strip_comments(read(t))):
                p = resolve(m.group(1), os.path.dirname(t), root, (".tex",))
                if p:
                    included.add(p)
        top = [t for t in main_candidates if t not in included]
        main_file = top[0] if top else (main_candidates[0] if main_candidates else None)
        if len(top) > 1:
            warnings.append(f"Multiple main-file candidates: {[os.path.relpath(t, root) for t in top]}")
    else:
        print(json.dumps({"error": f"path not found: {arg}"}))
        sys.exit(1)

    if main_file is None:
        warnings.append("No file with \\documentclass + \\begin{document} found; "
                        "treating all .tex as a flat set.")
        tex_in_order = all_tex
    else:
        tex_in_order = follow_inputs(main_file, root, warnings)
        # include any all_tex not reached via \input (orphans worth checking)
        for t in all_tex:
            if t not in tex_in_order:
                pass  # reported separately below if desired

    bib_files, backend = find_bibs(tex_in_order or all_tex, root, warnings)

    out = {
        "root": root,
        "main": main_file,
        "main_candidates": main_candidates,
        "tex_in_order": tex_in_order,
        "bib_files": bib_files,
        "bib_backend": backend,
        "all_tex": all_tex,
        "warnings": warnings,
    }
    print(json.dumps(out, indent=2))
    # human hint on stderr
    if main_file:
        print(f"[assemble] main={os.path.relpath(main_file, root)}  "
              f"tex={len(tex_in_order)}  bib={len(bib_files)}  backend={backend}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
