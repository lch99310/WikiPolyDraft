"""Tests for translator (section splitting and prompt/translation round-trip)."""

from pathlib import Path

import pytest

from wiki_translate.fetcher import Article, LangLink
from wiki_translate.translator import (
    PreparedJob,
    article_to_section_units,
    collect_translations,
    prepare_agent_driven,
)


def _make_article() -> Article:
    return Article(
        lang="en",
        title="Brett Whiteley",
        wikitext="""Brett Whiteley was an Australian painter.

== Early life ==
He was born in 1939.

== Career ==
He painted prolifically.""",
        sections=[],
        langlinks=[LangLink(lang="fr", title="Brett Whiteley")],
        revision_id=42,
    )


def test_article_to_section_units():
    article = _make_article()
    units = article_to_section_units(article)
    assert len(units) == 3
    assert units[0].heading == ""
    assert "Australian painter" in units[0].source_text
    assert units[1].heading == "== Early life =="
    # The heading is also embedded in source_text so the LLM translates it.
    assert units[1].source_text.startswith("== Early life ==")
    assert "He was born in 1939." in units[1].source_text
    assert units[2].heading == "== Career =="
    assert units[2].source_text.startswith("== Career ==")
    assert all(u.section_id for u in units)


def test_prepare_emits_prompts_and_manifest(tmp_path: Path):
    article = _make_article()
    job = prepare_agent_driven(article, "zh", tmp_path)
    assert (tmp_path / "job.json").exists()
    assert (tmp_path / "AGENT_README.md").exists()
    prompt_files = list((tmp_path / "prompts").glob("*.prompt.txt"))
    assert len(prompt_files) == len(job.sections) == 3
    sample = prompt_files[0].read_text(encoding="utf-8")
    assert "Wikipedia" in sample
    assert "wiki markup" in sample.lower()


def test_preparedjob_roundtrip(tmp_path: Path):
    article = _make_article()
    job = prepare_agent_driven(article, "zh", tmp_path)
    raw = (tmp_path / "job.json").read_text(encoding="utf-8")
    restored = PreparedJob.from_json(raw)
    assert restored.article_title == "Brett Whiteley"
    assert restored.revision_id == 42
    assert len(restored.sections) == len(job.sections)


def test_collect_translations_missing_raises(tmp_path: Path):
    article = _make_article()
    job = prepare_agent_driven(article, "zh", tmp_path)
    with pytest.raises(RuntimeError) as exc_info:
        collect_translations(tmp_path, job)
    assert "Missing translation" in str(exc_info.value)


def test_collect_translations_happy_path(tmp_path: Path):
    article = _make_article()
    job = prepare_agent_driven(article, "zh", tmp_path)
    for unit in job.sections:
        (tmp_path / "translations" / f"{unit.section_id}.txt").write_text(
            "[translated body]\n---TRANSLATOR-NOTES---\nnote here",
            encoding="utf-8",
        )
    results = collect_translations(tmp_path, job)
    assert len(results) == len(job.sections)
    for unit, result in results:
        assert "[translated body]" in result.translated_text
        assert result.notes == "note here"


def test_lang_collision_handled_at_cli_level():
    """prepare_agent_driven itself doesn't reject same-lang; the CLI does.
    Just confirm langlink_for returns None for missing target."""
    article = _make_article()
    assert article.langlink_for("zh") is None
    assert article.langlink_for("fr") == "Brett Whiteley"
