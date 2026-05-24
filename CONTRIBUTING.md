# Contributing to before-submit

Thanks for helping! The highest-value contributions are usually **venue rules**
(they go stale every cycle) and **new checks**. You don't need to be a Claude
Code expert — most of this skill is plain Markdown and small stdlib Python.

## Repo layout

```
.claude-plugin/        plugin.json + marketplace.json (distribution metadata)
skills/before-submit/
  SKILL.md             orchestration the agent follows (keep it concise)
  reference/           detailed catalogs + data, loaded on demand
  scripts/             stdlib-only Python helpers
```

## Ground rules

- **Scripts are standard-library only.** No third-party dependencies — users run
  these on arbitrary machines with whatever Python they have. (Python 3.8+.)
- **Keep `SKILL.md` small.** Put detail in `reference/*.md`; `SKILL.md` should
  just point to the right file per phase (progressive disclosure).
- **Cite your source** for any venue rule (the official CfP / author guidelines).
- Be precise about uncertainty — if you can't confirm a field, mark it `unknown`
  rather than guessing.

## Add or update a venue (the most useful PR)

Edit `skills/before-submit/reference/venues.yaml`. Each venue is one block. The
snapshot is a **fallback** — the skill fetches the live CfP first — so the most
important fields are `source_url` (where to fetch) and `snapshot_year` (an expiry
stamp). Minimal example:

```yaml
mykonf:
  name: "MyConf"
  edition: "MyConf 2027"
  snapshot_year: 2027
  source_url: "https://myconf.org/2027/cfp"     # official CfP — REQUIRED
  field: ml                                       # nlp | cv | ml | ...
  page_limit_review: 8                            # number, or {long: 8, short: 4}
  page_limit_camera: 9
  excluded_from_limit: [references, appendix]
  double_blind: true
  mandatory_sections:
    - {name: "Limitations", note: "required; missing => desk reject"}
  style_package: "myconf"
  paper_size: letter                              # letter | a4
  columns: 2
  caption: {figure: below, table: above}          # where \caption must go
  desk_reject_triggers:
    - "Over page limit; not anonymized; wrong template."
```

When you update an existing venue for a new cycle, bump `edition` +
`snapshot_year`, refresh `source_url`, and double-check page limits / mandatory
sections / style-file name against the official CfP.

## Add or change a LaTeX check

Document it in `reference/latex-checks.md`: what it flags, how to detect it, a
**severity** (ERROR / WARNING / INFO), the suggested fix, and whether the fix is
**safe-auto** (mechanical) or **ask-first** (subjective). The agent applies the
catalog, so clear, concrete wording matters more than code.

## Extend the reference verifier

`scripts/verify_refs.py` queries CrossRef / Semantic Scholar / OpenAlex / DBLP /
arXiv in parallel and corroborates across sources. To add a source: write a
`f_<source>_doi` / `f_<source>_title` returning `{source, title, authors, year}`,
register it in `verify_entry()`, and respect the circuit breaker
(`note_failure`/`note_success`) so a flaky source can't stall a run. Identifier
lookups should run before title search.

## Testing

```bash
# scripts must at least compile
python3 -m py_compile skills/before-submit/scripts/*.py

# project assembly on any LaTeX project
python3 skills/before-submit/scripts/assemble_project.py /path/to/paper

# reference verification (needs network) — try a tiny .bib with a known-real
# entry and an obviously-fake one; real => verified, fake => unable
python3 skills/before-submit/scripts/verify_refs.py refs.bib

# report rendering
python3 skills/before-submit/scripts/report_to_html.py before-submit-report.md -o out.html
```

If you change `SKILL.md` or `reference/*.md`, do a quick end-to-end run of the
skill on a sample paper to make sure the instructions still flow.

## Pull requests

Keep PRs focused (one venue update, or one check, per PR is ideal). Describe what
you changed and link the official source for any venue rule. Be kind in review.

## License

By contributing you agree your contributions are licensed under the
[MIT License](LICENSE).
