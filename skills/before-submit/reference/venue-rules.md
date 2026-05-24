# Venue Rules — online-first, snapshot fallback (Phase 2)

Goal: get the **authoritative** submission rules for the user's exact venue +
year + track, because these change yearly and a wrong page limit or missing
required section can mean desk rejection.

## Procedure

1. **Identify** the venue key (e.g. `acl`, `emnlp`, `neurips`, `cvpr`, `iclr`).
   Look it up in `reference/venues.yaml` to get its `source_url` and the last
   known `snapshot_year`.

2. **Try live first.** Fetch the official CfP / author guidelines:
   - Use the `source_url` from the snapshot, and/or web-search
     `"<venue> <year> call for papers"` and `"<venue> <year> author guidelines
     LaTeX"`. Prefer the official conference domain (e.g. `*.neurips.cc`,
     `aclrollingreview.org`, `thecvf.com`, OpenReview author guides).
   - Extract: page limit (review & camera; long/short), double-blind?, mandatory
     sections, special deliverables (checklist/repro/impact/lay-summary), style
     file + version, paper size/columns/font, caption convention, what's excluded
     from the page count, and any explicit desk-reject triggers.
   - If the live rules differ from the snapshot, **the live rules win** and you
     should mention the discrepancy.

3. **Fall back to the snapshot** only if you're offline or can't find/confirm the
   live CfP. Then **state it plainly** in the report:
   > ⚠️ Used built-in venue snapshot (as of `<snapshot_year>`). Verify against the
   > official CfP before submitting: `<source_url>`

4. **If the venue isn't in the snapshot at all**, do step 2 from web search only;
   if offline, tell the user you can't resolve venue rules and run only the
   venue-independent checks (Phases 3, 4-except-template, 5).

5. **Record the resolved rules** and pass them to Phase 4 (template conformance,
   caption convention, `\section*` expectations) and Phase 5 (page-limit check).

## Notes

- Always capture the **track** (long vs short, main vs findings/workshop) — page
  limits and required sections differ by track.
- Distinguish **review** vs **camera-ready** limits and required sections (e.g.
  Impact Statement / Acknowledgments are often camera-ready-only).
- The snapshot is a *fallback and a directory of where to look*, never the final
  word. Treat its `snapshot_year` as an expiry stamp.
