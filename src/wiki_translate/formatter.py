"""Output formatting: assemble final wikitext draft, generate CC BY-SA
attribution files, and produce review notes for the publishing editor.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .factcheck import check_ref_integrity
from .llm.base import TranslationResult
from .translator import PreparedJob, SectionUnit


DRAFT_BANNER = """<!--
==============================================================================
DRAFT - DO NOT PUBLISH WITHOUT HUMAN REVIEW
==============================================================================
This article was prepared by an AI-assisted translation tool (wiki-translate).
Per Wikipedia:LLM-assisted_translation, the editor publishing this MUST:
  1. Be fluent in both source and target languages.
  2. Verify every fact and citation against the original sources.
  3. Remove any AI hallucinations before publishing.
  4. Confirm CC BY-SA attribution is correctly applied (see edit-summary.txt
     and talk-template.txt files generated alongside this wikitext).
See review-notes.md for items flagged for review.
==============================================================================
-->
"""


@dataclass
class ReviewItem:
    section_id: str
    heading: str
    note: str


def assemble_wikitext(
    job: PreparedJob,
    translations: list[tuple[SectionUnit, TranslationResult]],
) -> str:
    """Build the final wikitext draft for the translated article."""
    pieces: list[str] = [DRAFT_BANNER, _llm_assisted_template(job), ""]
    for _unit, result in translations:
        # The translated section already includes its own heading (the LLM was
        # given the heading as part of source_text and was instructed to
        # translate the heading text while preserving the `==` markers).
        pieces.append(result.translated_text.rstrip())
        pieces.append("")
    return "\n".join(pieces).rstrip() + "\n"


def _llm_assisted_template(job: PreparedJob) -> str:
    """The {{LLM-assisted translation}} maintenance template.

    Format reflects what en.wikipedia uses; reviewers on other-language wikis
    may need to adapt to their local equivalent — this is noted in review-notes.
    """
    return (
        "{{LLM-assisted translation"
        f"|from={job.source_lang}"
        f"|article={job.article_title}"
        f"|oldid={job.revision_id}"
        "|reviewed=no"
        "}}"
    )


def edit_summary(job: PreparedJob) -> str:
    """CC BY-SA-compliant edit summary.

    Per Wikipedia:Translation, the edit summary must credit the source by
    linking to the original article and ideally to a stable permalink.
    """
    return (
        f"Translated from [[:{job.source_lang}:{job.article_title}]]; "
        f"see permalink {job.permalink} for attribution. "
        f"Draft prepared with AI assistance (wiki-translate); pending human review."
    )


def talk_template(job: PreparedJob) -> str:
    """{{Translated page}} template for the article's talk page.

    Required by CC BY-SA attribution: see Wikipedia:Copying within Wikipedia
    and Wikipedia:Translation.
    """
    return (
        "{{Translated page"
        f"|{job.source_lang}"
        f"|{job.article_title}"
        f"|oldid={job.revision_id}"
        "|insertversion=wiki-translate-0.1"
        "|small=no"
        "}}"
    )


_REF_RE = re.compile(r"<ref[\s>]", re.IGNORECASE)
_SENTENCE_RE = re.compile(r"[.!?。！？]\s")
_HALLUCINATION_HINTS = re.compile(
    r"(?:as an? (?:ai|assistant)|i (?:cannot|don't|do not)|i'm sorry|i apologize|"
    r"my training data|knowledge cutoff)",
    re.IGNORECASE,
)


def build_review_notes(
    job: PreparedJob,
    translations: list[tuple[SectionUnit, TranslationResult]],
    coverage_md: str | None = None,
) -> tuple[str, list[ReviewItem]]:
    """Produce review-notes.md flagging items the human editor must check."""
    items: list[ReviewItem] = []

    for unit, result in translations:
        ref_issues = check_ref_integrity(
            section_id=unit.section_id,
            heading=unit.heading,
            source_text=unit.source_text,
            translated_text=result.translated_text,
        )
        for issue in ref_issues:
            items.append(ReviewItem(
                section_id=issue.section_id,
                heading=issue.heading or "(lead)",
                note=f"[{issue.kind}] {issue.detail}",
            ))

        if _HALLUCINATION_HINTS.search(result.translated_text):
            items.append(ReviewItem(
                section_id=unit.section_id,
                heading=unit.heading or "(lead)",
                note=(
                    "LLM meta-text detected in translation (e.g. 'as an AI', 'I cannot'). "
                    "This is almost certainly a translation error; review and clean up."
                ),
            ))

        if result.notes:
            items.append(ReviewItem(
                section_id=unit.section_id,
                heading=unit.heading or "(lead)",
                note="Translator notes:\n" + result.notes,
            ))

        source_sentences = len(_SENTENCE_RE.findall(unit.source_text))
        translated_sentences = len(_SENTENCE_RE.findall(result.translated_text))
        if source_sentences >= 5 and translated_sentences < source_sentences * 0.5:
            items.append(ReviewItem(
                section_id=unit.section_id,
                heading=unit.heading or "(lead)",
                note=(
                    f"Translation may be truncated: source has ~{source_sentences} sentences, "
                    f"translation has ~{translated_sentences}. Compare lengths."
                ),
            ))

    target_existing_note = ""
    if job.target_existing_title:
        if coverage_md:
            target_existing_note = (
                f"\n## Existing target-language article\n\n"
                f"The {job.target_lang}.wikipedia.org already has an article titled "
                f"**{job.target_existing_title}**. See `coverage-report.md` in this "
                f"directory for a side-by-side section comparison and integration "
                f"guidance.\n"
            )
        else:
            target_existing_note = (
                f"\n## Existing target-language article\n\n"
                f"The {job.target_lang}.wikipedia.org already has an article titled "
                f"**{job.target_existing_title}**. This draft was generated from the "
                f"{job.source_lang} source ONLY; you must manually compare and merge with "
                f"the existing target version before publishing. Do NOT overwrite the "
                f"existing article — instead, integrate any new information.\n"
            )

    lines: list[str] = [
        f"# Review notes for {job.article_title} ({job.source_lang} -> {job.target_lang})",
        "",
        "**Read this before doing anything with the draft.**",
        "",
        "## Mandatory review checklist (per Wikipedia:LLM-assisted_translation)",
        "",
        "- [ ] You are fluent in both source and target languages.",
        "- [ ] Every factual claim has been verified against the original source.",
        "- [ ] Every `<ref>` citation in the draft matches the original article's citation.",
        "- [ ] No AI hallucinations remain in the text.",
        "- [ ] Proper nouns, dates, and numbers are correct.",
        "- [ ] Internal links `[[X]]` have been resolved to target-language equivalents where they exist.",
        "- [ ] The `{{LLM-assisted translation}}` template at the top is appropriate for the target wiki "
        "(if the target wiki uses a different template name, adapt it).",
        "- [ ] You will use the provided `edit-summary.txt` and `talk-template.txt` "
        "(or local equivalents) to satisfy CC BY-SA attribution.",
        "",
        f"## Source article",
        "",
        f"- Title: {job.article_title}",
        f"- Language: {job.source_lang}",
        f"- Revision: {job.revision_id}",
        f"- Permalink (required for attribution): {job.permalink}",
        target_existing_note,
        "## Flagged items",
        "",
    ]

    if not items:
        lines.append("_No automated flags. This does NOT mean the translation is correct — "
                     "the mandatory review above is still required._")
    else:
        for item in items:
            lines.append(f"### Section `{item.section_id}` — {item.heading}")
            lines.append("")
            lines.append(item.note)
            lines.append("")

    return "\n".join(lines) + "\n", items


def write_output(
    job: PreparedJob,
    translations: list[tuple[SectionUnit, TranslationResult]],
    out_dir: Path,
    coverage_md: str | None = None,
) -> dict[str, Path]:
    """Write all output files. Returns a map of name -> path."""
    out_dir = Path(out_dir) / _safe_dir_name(job.article_title)
    out_dir.mkdir(parents=True, exist_ok=True)

    title_safe = _safe_dir_name(job.article_title)
    wikitext = assemble_wikitext(job, translations)
    review_md, _ = build_review_notes(job, translations, coverage_md=coverage_md)

    paths = {
        "wikitext": out_dir / f"{title_safe}.wikitext",
        "edit_summary": out_dir / "edit-summary.txt",
        "talk_template": out_dir / "talk-template.txt",
        "review_notes": out_dir / "review-notes.md",
    }
    if coverage_md is not None:
        paths["coverage_report"] = out_dir / "coverage-report.md"
        paths["coverage_report"].write_text(coverage_md, encoding="utf-8")
    paths["wikitext"].write_text(wikitext, encoding="utf-8")
    paths["edit_summary"].write_text(edit_summary(job) + "\n", encoding="utf-8")
    paths["talk_template"].write_text(talk_template(job) + "\n", encoding="utf-8")
    paths["review_notes"].write_text(review_md, encoding="utf-8")
    return paths


_UNSAFE_FS_RE = re.compile(r"[^\w\-一-鿿]+")


def _safe_dir_name(title: str) -> str:
    return _UNSAFE_FS_RE.sub("_", title).strip("_") or "article"
