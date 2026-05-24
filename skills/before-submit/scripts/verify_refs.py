#!/usr/bin/env python3
"""
verify_refs.py — fast, parallel, multi-source bibliography verification.

Confirms each .bib entry actually exists and its metadata matches, to catch
hallucinated / wrong references. Strategy:

  * Identifier-first: DOI -> CrossRef / Semantic Scholar / OpenAlex; arXiv id ->
    arXiv / S2. Identifiers are unique, so these are high-precision.
  * Title search across sources runs in parallel as corroboration.
  * Cross-source corroboration is the strongest signal: >=2 sources agreeing on
    the title (sim >= 0.95) => verified even at middling single-source score.
  * Early-exit once one high-confidence match has a corroborator; hard 18s/entry.
  * Per-source circuit breaker: 2 consecutive failures -> skip that source.
  * arXiv-shaped DOIs (10.48550/arXiv.*) are NOT queried on CrossRef/OpenAlex.
  * Surgical networking: short timeout, no retries on failure (fail fast -> let a
    parallel source answer / trip the breaker). Optional on-disk cache (24h).

STDLIB ONLY — no pip installs required. Python 3.8+.

The agent should run this, then web-verify any entry it marks `unable`/`mismatch`
(brand-new preprints, blogs, non-academic sources that no index covers).

Usage:
    python3 verify_refs.py paper.bib [more.bib ...] [options]

Options:
    --json              machine-readable JSON to stdout (default: human table)
    --email ADDR        polite-pool contact email (or env BEFORE_SUBMIT_CONTACT_EMAIL)
    --timeout SEC       per-request timeout (default 12)
    --entry-deadline S  hard wall-clock per entry (default 18)
    --max-workers N     thread pool size per entry (default 6)
    --no-cache          disable the on-disk HTTP cache
    --only KEY[,KEY]    verify only these bib keys
Environment:
    SEMANTIC_SCHOLAR_API_KEY   lifts S2 rate limits (100/5min -> 5000/5min)
    BEFORE_SUBMIT_CONTACT_EMAIL  polite-pool email for CrossRef/OpenAlex/arXiv
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import difflib
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

# ----------------------------------------------------------------------------- config
TITLE_MATCH = 0.88        # single-source title-match threshold
TITLE_AGREE = 0.95        # two sources "agree" on title
TITLE_FLOOR = 0.60        # below this a title-search hit is junk -> "unable", not "mismatch"
AUTHOR_MATCH = 0.60
YEAR_TOL = 1
HIGH_CONF = 0.85
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "before-submit")
CACHE_TTL = 24 * 3600

_EMAIL = ""
_TIMEOUT = 12.0
_USE_CACHE = True
_S2_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "").strip()


def _ua() -> str:
    base = "before-submit-verify/1.0 (+https://github.com/; mailto:%s)"
    return base % (_EMAIL or "anonymous@example.org")


# ----------------------------------------------------------------------------- circuit breaker
_breaker_lock = threading.Lock()
_breakers: dict[str, dict] = {}


def breaker_open(src: str) -> bool:
    with _breaker_lock:
        b = _breakers.get(src)
        return bool(b and b["open"])


def note_failure(src: str, threshold: int = 2):
    with _breaker_lock:
        b = _breakers.setdefault(src, {"fails": 0, "open": False})
        b["fails"] += 1
        if b["fails"] >= threshold:
            b["open"] = True


def note_success(src: str):
    with _breaker_lock:
        b = _breakers.get(src)
        if b:
            b["fails"] = 0
            b["open"] = False


# ----------------------------------------------------------------------------- HTTP (+cache)
def _cache_path(url: str) -> str:
    return os.path.join(CACHE_DIR, hashlib.sha256(url.encode()).hexdigest() + ".json")


def http_get(url: str, src: str, headers: dict | None = None):
    """GET -> response text, or None on any failure (records breaker failure)."""
    if breaker_open(src):
        return None
    if _USE_CACHE:
        p = _cache_path(url)
        try:
            if os.path.isfile(p) and (time.time() - os.path.getmtime(p)) < CACHE_TTL:
                with open(p, "r", encoding="utf-8") as f:
                    return f.read()
        except OSError:
            pass
    req = urllib.request.Request(url, headers={"User-Agent": _ua(), **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            body = r.read().decode("utf-8", "replace")
        note_success(src)
        if _USE_CACHE:
            try:
                os.makedirs(CACHE_DIR, exist_ok=True)
                with open(_cache_path(url), "w", encoding="utf-8") as f:
                    f.write(body)
            except OSError:
                pass
        return body
    except Exception:
        note_failure(src)
        return None


def get_json(url: str, src: str, headers: dict | None = None):
    body = http_get(url, src, headers)
    if not body:
        return None
    try:
        return json.loads(body)
    except ValueError:
        return None


# ----------------------------------------------------------------------------- text utils
def clean_tex(s: str) -> str:
    s = re.sub(r"\\[a-zA-Z]+\*?\s*", " ", s)   # drop \commands
    s = s.replace("{", "").replace("}", "").replace("~", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def norm_title(s: str) -> str:
    s = clean_tex(s).lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def title_sim(a: str, b: str) -> float:
    a, b = norm_title(a), norm_title(b)
    if not a or not b:
        return 0.0
    seq = difflib.SequenceMatcher(None, a, b).ratio()
    ta, tb = set(a.split()), set(b.split())
    jac = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    return max(seq, jac)


def last_names(names) -> set:
    out = set()
    for nm in names or []:
        nm = clean_tex(nm).strip()
        if not nm:
            continue
        if "," in nm:
            out.add(nm.split(",")[0].strip().lower())
        else:
            out.add(nm.split()[-1].lower())
    return {x for x in out if x}


def author_sim(bib_authors, fetched_authors) -> float:
    a, b = last_names(bib_authors), last_names(fetched_authors)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a)


def year_close(y1: str, y2: str) -> bool:
    y1, y2 = (y1 or "").strip()[:4], (y2 or "").strip()[:4]
    if not y1 or not y2:
        return True
    try:
        return abs(int(y1) - int(y2)) <= YEAR_TOL
    except ValueError:
        return False


# ----------------------------------------------------------------------------- bib parsing
def parse_bib(text: str):
    entries = []
    for m in re.finditer(r"@(\w+)\s*\{", text):
        etype = m.group(1).lower()
        if etype in ("comment", "string", "preamble"):
            continue
        start = m.end() - 1
        depth, j = 0, start
        while j < len(text):
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        body = text[start + 1:j]
        key, _, fields_str = body.partition(",")
        entries.append({"type": etype, "key": key.strip(), **parse_fields(fields_str)})
    return entries


def parse_fields(s: str) -> dict:
    fields, i, n = {}, 0, len(s)
    name_re = re.compile(r"([A-Za-z][A-Za-z0-9_\-]*)\s*=\s*")
    while i < n:
        m = name_re.search(s, i)
        if not m:
            break
        name = m.group(1).lower()
        i = m.end()
        if i >= n:
            break
        if s[i] == "{":
            depth, j = 0, i
            while j < n:
                if s[j] == "{":
                    depth += 1
                elif s[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            val, i = s[i + 1:j], j + 1
        elif s[i] == '"':
            j = i + 1
            while j < n and s[j] != '"':
                j += 1
            val, i = s[i + 1:j], j + 1
        else:
            j = i
            while j < n and s[j] != ",":
                j += 1
            val, i = s[i:j].strip(), j
        nc = s.find(",", i)
        i = nc + 1 if nc >= 0 else n
        fields[name] = clean_tex(val)
    return fields


def split_authors(s: str):
    return [a.strip() for a in re.split(r"\s+and\s+", s or "") if a.strip()]


def arxiv_id_of(e: dict):
    if e.get("archiveprefix", "").lower() == "arxiv" and e.get("eprint"):
        return e["eprint"].strip()
    for f in ("eprint", "doi", "url", "journal", "note"):
        v = e.get(f, "")
        m = re.search(r"(?:arxiv[:/]|abs/)\s*([0-9]{4}\.[0-9]{4,5}(?:v\d+)?)", v, re.I)
        if m:
            return m.group(1)
        m = re.search(r"10\.48550/arxiv\.([0-9]{4}\.[0-9]{4,5})", v, re.I)
        if m:
            return m.group(1)
    return None


def year_of(e: dict):
    m = re.search(r"(\d{4})", e.get("year", ""))
    return m.group(1) if m else ""


# ----------------------------------------------------------------------------- fetchers -> {source,title,authors,year}
def _cr_email():
    return ("&mailto=" + urllib.parse.quote(_EMAIL)) if _EMAIL else ""


def f_crossref_doi(doi):
    d = get_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}?mailto={urllib.parse.quote(_EMAIL or 'a@b.c')}", "crossref")
    msg = (d or {}).get("message")
    if not msg:
        return None
    return _cr_pack(msg)


def f_crossref_title(title):
    d = get_json("https://api.crossref.org/works?query.bibliographic="
                 + urllib.parse.quote(title) + "&rows=5" + _cr_email(), "crossref")
    items = (((d or {}).get("message") or {}).get("items")) or []
    return [_cr_pack(m) for m in items]


def _cr_pack(m):
    t = (m.get("title") or [""])[0]
    auth = [(a.get("family") or a.get("name") or "") for a in m.get("author", [])]
    y = ""
    for k in ("published-print", "published-online", "issued", "created"):
        dp = (m.get(k) or {}).get("date-parts")
        if dp and dp[0] and dp[0][0]:
            y = str(dp[0][0])
            break
    return {"source": "crossref", "title": t, "authors": auth, "year": y, "raw": m}


def f_openalex_doi(doi):
    d = get_json(f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi)}" + _oa_mail(), "openalex")
    return _oa_pack(d) if d else None


def f_openalex_title(title):
    d = get_json("https://api.openalex.org/works?search=" + urllib.parse.quote(title)
                 + "&per-page=5" + _oa_mail(), "openalex")
    return [_oa_pack(w) for w in (d or {}).get("results", [])]


def _oa_mail():
    return ("&mailto=" + urllib.parse.quote(_EMAIL)) if _EMAIL else ""


def _oa_pack(w):
    auth = [(a.get("author") or {}).get("display_name", "") for a in w.get("authorships", [])]
    return {"source": "openalex", "title": w.get("title") or w.get("display_name") or "",
            "authors": auth, "year": str(w.get("publication_year") or "")}


def _s2_headers():
    return {"x-api-key": _S2_KEY} if _S2_KEY else {}


def f_s2_id(idstr):
    d = get_json(f"https://api.semanticscholar.org/graph/v1/paper/{idstr}?fields=title,authors,year",
                 "s2", _s2_headers())
    return _s2_pack(d) if d else None


def f_s2_title(title):
    d = get_json("https://api.semanticscholar.org/graph/v1/paper/search?query="
                 + urllib.parse.quote(title) + "&fields=title,authors,year&limit=5", "s2", _s2_headers())
    return [_s2_pack(x) for x in (d or {}).get("data", [])]


def _s2_pack(d):
    return {"source": "s2", "title": d.get("title") or "",
            "authors": [a.get("name", "") for a in d.get("authors", [])],
            "year": str(d.get("year") or "")}


def f_dblp_title(title):
    d = get_json("https://dblp.org/search/publ/api?q=" + urllib.parse.quote(title)
                 + "&format=json&h=5", "dblp")
    hits = (((d or {}).get("result") or {}).get("hits") or {}).get("hit") or []
    out = []
    for h in hits:
        info = h.get("info", {})
        a = info.get("authors", {}).get("author", [])
        if isinstance(a, dict):
            a = [a]
        names = [(x.get("text") if isinstance(x, dict) else str(x)) for x in a]
        out.append({"source": "dblp", "title": info.get("title", ""),
                    "authors": names, "year": str(info.get("year") or "")})
    return out


def _arxiv_parse(xml_text):
    out = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for e in root.findall("a:entry", ns):
        t = (e.findtext("a:title", default="", namespaces=ns) or "").strip()
        y = (e.findtext("a:published", default="", namespaces=ns) or "")[:4]
        names = [ (a.findtext("a:name", default="", namespaces=ns) or "")
                  for a in e.findall("a:author", ns)]
        out.append({"source": "arxiv", "title": t, "authors": names, "year": y})
    return out


def f_arxiv_id(aid):
    body = http_get("http://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(aid)
                    + "&max_results=1", "arxiv")
    r = _arxiv_parse(body) if body else []
    return r[0] if r else None


def f_arxiv_title(title):
    q = urllib.parse.quote('ti:"%s"' % title)
    body = http_get("http://export.arxiv.org/api/query?search_query=" + q + "&max_results=5", "arxiv")
    return _arxiv_parse(body) if body else []


# ----------------------------------------------------------------------------- per-entry verify
def best_candidate(bib_title, cands):
    best, bs = None, 0.0
    for c in cands or []:
        if not c:
            continue
        s = title_sim(bib_title, c.get("title", ""))
        if s > bs:
            best, bs = c, s
    return (best, bs) if bs >= TITLE_FLOOR else (None, 0.0)


def score(bib, cand):
    ts = title_sim(bib.get("title", ""), cand.get("title", ""))
    as_ = author_sim(split_authors(bib.get("author", "")), cand.get("authors", []))
    yok = year_close(year_of(bib), cand.get("year", ""))
    conf = ts * 0.5 + as_ * 0.3 + (1.0 if yok else 0.5) * 0.2
    return ts, as_, yok, conf


def verify_entry(e, deadline_s, workers):
    title = e.get("title", "")
    doi = e.get("doi", "").strip()
    aid = arxiv_id_of(e)
    doi_is_arxiv = doi and "10.48550/arxiv" in doi.lower()

    tasks = []  # (callable -> candidate or list)
    if doi and not doi_is_arxiv:
        tasks += [lambda: f_crossref_doi(doi), lambda: f_openalex_doi(doi),
                  lambda: f_s2_id("DOI:" + doi)]
    if aid:
        tasks += [lambda: f_arxiv_id(aid), lambda: f_s2_id("arXiv:" + aid)]
    if title:
        tasks += [lambda: f_s2_title(title), lambda: f_openalex_title(title),
                  lambda: f_dblp_title(title), lambda: f_crossref_title(title),
                  lambda: f_arxiv_title(title)]
    if not tasks:
        return _result(e, "unable", None, [], ["No DOI, arXiv id, or title to look up."])

    results = []
    deadline = time.monotonic() + deadline_s

    def run(fn):
        out = fn()
        if isinstance(out, list):
            c, _ = best_candidate(title, out)
            return c
        return out

    pool = cf.ThreadPoolExecutor(max_workers=min(workers, len(tasks)))
    futs = {pool.submit(run, fn): fn for fn in tasks}
    try:
        pending = set(futs)
        while pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            done, pending = cf.wait(pending, timeout=min(remaining, 2.0),
                                    return_when=cf.FIRST_COMPLETED)
            for fut in done:
                try:
                    c = fut.result(timeout=0)
                except Exception:
                    c = None
                if c and c.get("title"):
                    results.append(c)
            if _corroborated(results):
                break
    finally:
        for fut in futs:
            fut.cancel()
        pool.shutdown(wait=False, cancel_futures=True)

    if not results:
        reason = ("All sources failed/unreachable (offline or rate-limited)."
                  if any(breaker_open(s) for s in ("crossref", "s2", "openalex", "dblp", "arxiv"))
                  else "Not found in any indexed source.")
        return _result(e, "unable", None, [], [reason])

    scored = sorted(((score(e, c), c) for c in results), key=lambda x: x[0][3], reverse=True)
    (ts, as_, yok, conf), primary = scored[0]

    agree = [c for (_, c) in scored[1:] if title_sim(primary["title"], c["title"]) >= TITLE_AGREE]
    agree_srcs = sorted({c["source"] for c in agree})

    issues, notes = [], []
    if agree_srcs:
        notes.append("Corroborated by: " + ", ".join(agree_srcs))
    if not yok and year_of(e) and primary.get("year"):
        if year_close(year_of(e), primary["year"]):
            notes.append(f"Year differs by <=1 ({year_of(e)} vs {primary['year']}) — likely preprint/published.")
        else:
            issues.append(f"Year mismatch: bib={year_of(e)} vs found={primary['year']}.")
    if ts < TITLE_MATCH:
        issues.append(f"Title differs (sim={ts:.2f}): found '{primary['title'][:80]}'.")

    verified = (agree_srcs and ts >= TITLE_MATCH) or (ts >= TITLE_MATCH and as_ >= AUTHOR_MATCH and yok)
    status = "verified" if verified else "mismatch"
    return _result(e, status, primary, agree_srcs, issues, notes, conf)


def _corroborated(results):
    if len(results) < 2:
        return False
    s = sorted(results, key=lambda r: 0, reverse=True)
    # primary = highest title agreement cluster: simple check — any pair agreeing
    for i in range(len(s)):
        for j in range(i + 1, len(s)):
            if title_sim(s[i]["title"], s[j]["title"]) >= TITLE_AGREE:
                return True
    return False


def _result(e, status, primary, agree, issues, notes=None, conf=0.0):
    return {
        "key": e.get("key", ""),
        "type": e.get("type", ""),
        "status": status,
        "bib_title": e.get("title", ""),
        "bib_year": year_of(e),
        "bib_doi": e.get("doi", ""),
        "found_title": (primary or {}).get("title", ""),
        "found_year": (primary or {}).get("year", ""),
        "found_source": (primary or {}).get("source", ""),
        "corroborated_by": agree,
        "confidence": round(conf, 2),
        "issues": issues,
        "notes": notes or [],
    }


# ----------------------------------------------------------------------------- main
def main():
    global _EMAIL, _TIMEOUT, _USE_CACHE
    ap = argparse.ArgumentParser(description="Multi-source .bib verification")
    ap.add_argument("bib", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--email", default=os.environ.get("BEFORE_SUBMIT_CONTACT_EMAIL", ""))
    ap.add_argument("--timeout", type=float, default=12.0)
    ap.add_argument("--entry-deadline", type=float, default=18.0)
    ap.add_argument("--max-workers", type=int, default=6)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    _EMAIL = args.email.strip()
    _TIMEOUT = args.timeout
    _USE_CACHE = not args.no_cache

    entries = []
    for path in args.bib:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                entries += parse_bib(f.read())
        except OSError as ex:
            print(f"warning: cannot read {path}: {ex}", file=sys.stderr)
    if args.only:
        keep = {k.strip() for k in args.only.split(",")}
        entries = [e for e in entries if e.get("key") in keep]
    if not entries:
        print("No entries parsed.", file=sys.stderr)
        sys.exit(1)

    results = []
    for i, e in enumerate(entries, 1):
        if not args.json:
            print(f"\r[{i}/{len(entries)}] {e.get('key','')[:40]:<40}", end="", file=sys.stderr, flush=True)
        results.append(verify_entry(e, args.entry_deadline, args.max_workers))
    if not args.json:
        print("\r" + " " * 60 + "\r", end="", file=sys.stderr)

    if args.json:
        print(json.dumps({"results": results, "summary": _summary(results)}, indent=2))
    else:
        _print_human(results)


def _summary(results):
    s = {"verified": 0, "mismatch": 0, "unable": 0, "total": len(results)}
    for r in results:
        s[r["status"]] = s.get(r["status"], 0) + 1
    return s


def _print_human(results):
    by = {"mismatch": [], "unable": [], "verified": []}
    for r in results:
        by[r["status"]].append(r)
    print("\n=== Bibliography verification ===")
    s = _summary(results)
    print(f"verified={s['verified']}  mismatch={s['mismatch']}  unable={s['unable']}  total={s['total']}\n")
    if by["mismatch"]:
        print("⚠️  MISMATCH (found something that disagrees — check these):")
        for r in by["mismatch"]:
            print(f"  - {r['key']}: {'; '.join(r['issues']) or 'metadata differs'}")
            if r["found_title"]:
                print(f"      found: '{r['found_title'][:90]}' ({r['found_year']}, {r['found_source']})")
    if by["unable"]:
        print("\n❓ UNABLE to verify (web-search these yourself — may be new/blog/non-academic, or fake):")
        for r in by["unable"]:
            print(f"  - {r['key']}: '{r['bib_title'][:80]}' ({r['bib_year']}) — {'; '.join(r['issues'])}")
    print(f"\n✓ {s['verified']} entries verified.", "" if not by["verified"]
          else "(corroboration notes in --json output)")


if __name__ == "__main__":
    main()
