# Example: Brett Whiteley with existing zh stub (V0.3)

The hard real-world case: **both wikis already have an article**, but with
different coverage. The English Wikipedia has a fairly complete entry; the
Chinese Wikipedia (in this synthetic fixture) has a short stub with `早年
生涯` and a section called `影響` ("Influence") that the English source
does not have.

This is what the tool's V0.3 features are for. The reviewer must merge —
not overwrite. The outputs in this directory show what we give them to
work from.

## ⚠️ About this example

Both the source and the "existing target" article here are synthetic
fixtures so the example runs offline. The fixture intentionally constructs:

- Three citation URLs, one of which 404s and one of which is `.invalid`
  (DNS failure) — to exercise the Level 2 URL reachability check.
- A target stub whose section list overlaps with, but doesn't cover, the
  source — to exercise the alignment workflow.

The URL check result is supplied as a fixture (`url-check.json` inside
`wt-work/` after `reproduce.py` runs). On a real network you'd get the
same file by running `wiki-translate prepare --check-urls`.

## What's in this directory

| File | Purpose |
|---|---|
| `Brett_Whiteley.wikitext` | Translated draft, with DRAFT banner and `{{LLM-assisted translation\|reviewed=no}}` |
| `edit-summary.txt` | CC BY-SA edit summary |
| `talk-template.txt` | `{{Translated page}}` for the article talk page |
| `coverage-report.md` | **Upgraded V0.3 output**: alignment table + per-section merge plan. Shows how the en sections map to the zh stub and tells the reviewer what to do row-by-row. |
| `review-notes.md` | Mandatory checklist + translator notes + **Citation URL reachability** section with the dead links flagged. |

## What this example demonstrates beyond V0.1 / V0.2

1. **LLM-driven cross-language section alignment** — the host agent
   reads `_alignment.prompt.txt`, answers `MATCH: Early life | 早年生涯`,
   `ONLY-SOURCE: Reception`, `ONLY-TARGET: 影響`, and the upgraded
   coverage report renders these into an alignment table.

2. **Per-section merge plan** — every alignment row is annotated with a
   concrete suggestion: "compare side-by-side and integrate" for matches,
   "strong candidate to add" for only-source, "keep as-is" for only-target.
   The plan is a suggestion the human reviewer acts on; the tool does NOT
   auto-merge.

3. **Citation URL reachability (Level 2 fact-check)** — review-notes.md
   contains a table of unreachable citation URLs (DNS failures, 4xx, etc.)
   the reviewer should patch with archived copies or a different source
   before publishing. Reachable ≠ accurate — the manual mandatory review
   still applies.

## What V0.3 does NOT do (deferred)

- **Auto-merge / pick-winner**: the tool does not edit the existing target
  article. The reviewer integrates by hand using the merge plan as a guide.
- **Level 3 fact-check (web cross-verification)**: the tool only checks
  whether the cited URL responds, not whether the source actually supports
  the claim it's attached to.
