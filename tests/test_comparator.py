"""Tests for comparator (section coverage between source and existing target)."""

from wiki_translate.comparator import (
    SectionCoverage,
    compare_sections,
    coverage_report_md,
)
from wiki_translate.fetcher import Article, Section


def _article(lang: str, title: str, sections: list[Section]) -> Article:
    return Article(
        lang=lang,
        title=title,
        wikitext="(omitted)",
        sections=sections,
        langlinks=[],
        revision_id=1,
    )


def test_compare_only_level_2():
    source = _article("en", "X", [
        Section(level=2, title="Early life", anchor="", index="1"),
        Section(level=3, title="Childhood", anchor="", index="1.1"),
        Section(level=2, title="Career", anchor="", index="2"),
    ])
    target = _article("zh", "X", [
        Section(level=2, title="生平", anchor="", index="1"),
    ])
    coverage = compare_sections(source, target)
    assert coverage.source_headings == ["Early life", "Career"]
    assert coverage.target_headings == ["生平"]


def test_coverage_report_contents():
    source = _article("en", "Brett Whiteley", [
        Section(level=2, title="Early life", anchor="", index="1"),
        Section(level=2, title="Career", anchor="", index="2"),
    ])
    target = _article("zh", "布雷特·懷特利", [
        Section(level=2, title="生平", anchor="", index="1"),
    ])
    coverage = SectionCoverage(
        source_headings=["Early life", "Career"],
        target_headings=["生平"],
    )
    md = coverage_report_md(source, target, coverage)
    assert "Brett Whiteley" in md
    assert "布雷特·懷特利" in md
    assert "Early life" in md
    assert "生平" in md
    assert "Do NOT overwrite" in md
    # V0.2 explicitly does not attempt cross-lang alignment.
    assert "not** attempted" in md.lower()


def test_coverage_report_empty_sections():
    source = _article("en", "Stub", [])
    target = _article("zh", "簡介", [])
    coverage = compare_sections(source, target)
    md = coverage_report_md(source, target, coverage)
    # Should not crash, should explain the absence.
    assert "no level-2 sections" in md.lower()
