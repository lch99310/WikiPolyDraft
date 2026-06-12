"""Tests for formatter (attribution + review notes; no network)."""

from pathlib import Path

from wiki_translate.formatter import (
    DRAFT_BANNER,
    assemble_wikitext,
    build_review_notes,
    edit_summary,
    talk_template,
    write_output,
)
from wiki_translate.llm.base import TranslationResult
from wiki_translate.translator import PreparedJob, SectionUnit


def _make_job(target_existing: str | None = None) -> PreparedJob:
    return PreparedJob(
        source_lang="en",
        target_lang="zh",
        article_title="Brett Whiteley",
        article_url="https://en.wikipedia.org/wiki/Brett_Whiteley",
        revision_id=123456789,
        permalink="https://en.wikipedia.org/w/index.php?oldid=123456789",
        target_existing_title=target_existing,
        sections=[
            SectionUnit(section_id="000-lead", heading="", source_text="Lead text."),
            SectionUnit(section_id="001-early-life", heading="== Early life ==",
                        source_text="Born in 1939.<ref>Source A</ref>"),
        ],
    )


def test_assemble_wikitext_contains_safeguards():
    job = _make_job()
    translations = [
        (job.sections[0], TranslationResult("前言文字。")),
        # The LLM is responsible for translating the heading too; the
        # formatter no longer prepends the original English heading.
        (job.sections[1], TranslationResult("== 早年生涯 ==\n生於1939年。<ref>Source A</ref>")),
    ]
    wt = assemble_wikitext(job, translations)
    assert DRAFT_BANNER in wt
    assert "{{LLM-assisted translation" in wt
    assert "|reviewed=no" in wt
    assert "|from=en" in wt
    assert "|oldid=123456789" in wt
    assert "== 早年生涯 ==" in wt
    assert "== Early life ==" not in wt
    assert "前言文字。" in wt
    assert "<ref>Source A</ref>" in wt


def test_edit_summary_has_permalink_and_source_link():
    job = _make_job()
    summary = edit_summary(job)
    assert "[[:en:Brett Whiteley]]" in summary
    assert "oldid=123456789" in summary
    assert "human review" in summary.lower()


def test_talk_template_format():
    job = _make_job()
    template = talk_template(job)
    assert template.startswith("{{Translated page")
    assert "|en|" in template
    assert "|Brett Whiteley|" in template
    assert "|oldid=123456789" in template


def test_review_notes_flag_citation_count_mismatch():
    job = _make_job()
    translations = [
        (job.sections[0], TranslationResult("前言文字。")),
        # Translation dropped the citation
        (job.sections[1], TranslationResult("生於1939年。")),
    ]
    md, items = build_review_notes(job, translations)
    assert any("Citation count mismatch" in i.note for i in items)
    assert "Citation count mismatch" in md


def test_review_notes_flag_llm_meta_text():
    job = _make_job()
    translations = [
        (job.sections[0], TranslationResult("前言文字。")),
        (job.sections[1], TranslationResult(
            "As an AI assistant, I cannot translate this section properly."
        )),
    ]
    md, items = build_review_notes(job, translations)
    assert any("LLM meta-text detected" in i.note for i in items)


def test_review_notes_include_translator_notes():
    job = _make_job()
    translations = [
        (job.sections[0], TranslationResult("前言文字。", notes="不確定『Brett』的中譯。")),
        (job.sections[1], TranslationResult("生於1939年。<ref>Source A</ref>")),
    ]
    md, items = build_review_notes(job, translations)
    assert any("不確定" in i.note for i in items)


def test_review_notes_target_existing_warning():
    job = _make_job(target_existing="布雷特·惠特利")
    translations = [
        (job.sections[0], TranslationResult("前言文字。")),
        (job.sections[1], TranslationResult("生於1939年。<ref>Source A</ref>")),
    ]
    md, _ = build_review_notes(job, translations)
    assert "布雷特·惠特利" in md
    assert "manually compare and merge" in md.lower()


def test_review_notes_always_has_mandatory_checklist():
    job = _make_job()
    translations = [
        (job.sections[0], TranslationResult("前言文字。")),
        (job.sections[1], TranslationResult("生於1939年。<ref>Source A</ref>")),
    ]
    md, _ = build_review_notes(job, translations)
    assert "Mandatory review checklist" in md
    assert "fluent in both" in md.lower()
    assert "hallucination" in md.lower()


def test_write_output_creates_all_files(tmp_path: Path):
    job = _make_job()
    translations = [
        (job.sections[0], TranslationResult("前言文字。")),
        (job.sections[1], TranslationResult("生於1939年。<ref>Source A</ref>")),
    ]
    paths = write_output(job, translations, tmp_path)
    for key in ("wikitext", "edit_summary", "talk_template", "review_notes"):
        assert paths[key].exists()
        assert paths[key].read_text(encoding="utf-8").strip()
    # Ensure draft banner is at top of wikitext
    wt_content = paths["wikitext"].read_text(encoding="utf-8")
    assert wt_content.startswith(DRAFT_BANNER[:30])
