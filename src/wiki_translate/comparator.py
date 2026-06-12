"""Compare a source article with the existing target-language article (if any).

V0.2 scope: structural coverage at the section-heading level. We deliberately
do NOT pick winners or merge sections — that requires cross-language section
alignment (an LLM task, deferred to V0.3). The human reviewer must do the
integration; this module gives them a coverage report to work from.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .fetcher import Article


@dataclass
class SectionCoverage:
    source_headings: list[str] = field(default_factory=list)
    target_headings: list[str] = field(default_factory=list)


def compare_sections(source: Article, target_existing: Article) -> SectionCoverage:
    """List the level-2 section headings on each side.

    We do not attempt cross-language alignment (e.g. matching "Early life"
    to "早年生涯"); that requires an LLM and is V0.3 territory. The human
    reviewer aligns them using the side-by-side coverage report.
    """
    src_headings = [s.title for s in source.sections if s.level == 2 and s.title]
    tgt_headings = [s.title for s in target_existing.sections if s.level == 2 and s.title]
    return SectionCoverage(
        source_headings=src_headings,
        target_headings=tgt_headings,
    )


def coverage_report_md(
    source: Article,
    target_existing: Article,
    coverage: SectionCoverage,
) -> str:
    """Render the coverage report a human reviewer reads before merging."""
    lines = [
        f"# Coverage report: {source.title}",
        "",
        f"Source ({source.lang}): [{source.title}]({source.article_url}) "
        f"(revision {source.revision_id})",
        "",
        f"Existing target ({target_existing.lang}): "
        f"[{target_existing.title}]({target_existing.article_url}) "
        f"(revision {target_existing.revision_id})",
        "",
        "## ⚠️ The target language already has an article",
        "",
        "**Do NOT overwrite the existing target article with the translated draft.** "
        "Instead:",
        "",
        "1. Compare the two section lists below.",
        "2. Identify which information in the draft is genuinely missing from the "
        "existing target article.",
        "3. Integrate (do not replace) into the existing target article, preserving "
        "its existing structure, citations, and stylistic conventions.",
        "4. The CC BY-SA attribution still applies for any content you add: see "
        "`edit-summary.txt` and `talk-template.txt`.",
        "",
        f"## Source article sections ({source.lang})",
        "",
    ]
    if coverage.source_headings:
        for h in coverage.source_headings:
            lines.append(f"- {h}")
    else:
        lines.append("_(no level-2 sections detected; article may be short or "
                     "consist of a single lead paragraph.)_")

    lines += [
        "",
        f"## Existing target article sections ({target_existing.lang})",
        "",
    ]
    if coverage.target_headings:
        for h in coverage.target_headings:
            lines.append(f"- {h}")
    else:
        lines.append("_(no level-2 sections detected.)_")

    lines += [
        "",
        "## Cross-language section alignment",
        "",
        "Automated section alignment across languages (e.g. mapping `Early life` ⇔ "
        "`早年生涯`) requires an LLM and is **not** attempted in this version. "
        "You will need to map the two lists above by hand when deciding what to merge.",
        "",
    ]
    return "\n".join(lines) + "\n"
