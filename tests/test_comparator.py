"""Tests for comparator (section coverage between source and existing target)."""

from pathlib import Path

from wiki_translate.comparator import (
    SectionAlignment,
    SectionCoverage,
    build_alignment_prompt,
    compare_sections,
    coverage_report_md,
    emit_alignment_prompt,
    parse_alignment_response,
    read_alignment_response,
    read_target_info,
    write_target_info,
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
    # When alignments=None, the report tells the reviewer how to produce one.
    assert "alignment was not produced" in md.lower()
    assert "_alignment.prompt.txt" in md


def test_coverage_report_empty_sections():
    source = _article("en", "Stub", [])
    target = _article("zh", "簡介", [])
    coverage = compare_sections(source, target)
    md = coverage_report_md(source, target, coverage)
    # Should not crash, should explain the absence.
    assert "no level-2 sections" in md.lower()


# --- V0.3: alignment ---------------------------------------------------------


def test_build_alignment_prompt_lists_both_sides():
    source = _article("en", "Brett Whiteley", [
        Section(level=2, title="Early life", anchor="", index="1"),
        Section(level=2, title="Career", anchor="", index="2"),
    ])
    target = _article("zh", "布雷特·懷特利", [
        Section(level=2, title="生平", anchor="", index="1"),
    ])
    prompt = build_alignment_prompt(source, target)
    assert "Early life" in prompt
    assert "Career" in prompt
    assert "生平" in prompt
    assert "MATCH:" in prompt
    assert "ONLY-SOURCE:" in prompt
    assert "ONLY-TARGET:" in prompt
    # Should warn the LLM to be conservative
    assert "conservative" in prompt.lower()


def test_parse_alignment_response():
    raw = """MATCH: Early life | 早年生涯
ONLY-SOURCE: Reception
ONLY-TARGET: 影響
some commentary the LLM added by mistake
MATCH:  Career   |   职业生涯
"""
    aligns = parse_alignment_response(raw)
    assert len(aligns) == 4
    assert aligns[0] == SectionAlignment("matched", "Early life", "早年生涯")
    assert aligns[1] == SectionAlignment("only-source", "Reception", None)
    assert aligns[2] == SectionAlignment("only-target", None, "影響")
    assert aligns[3] == SectionAlignment("matched", "Career", "职业生涯")


def test_parse_alignment_response_accepts_only_source_with_space():
    raw = "ONLY SOURCE: Foo\nONLY TARGET: Bar"
    aligns = parse_alignment_response(raw)
    assert aligns[0].kind == "only-source"
    assert aligns[1].kind == "only-target"


def test_emit_and_read_alignment(tmp_path: Path):
    source = _article("en", "X", [
        Section(level=2, title="A", anchor="", index="1"),
    ])
    target = _article("zh", "X", [
        Section(level=2, title="甲", anchor="", index="1"),
    ])
    path = emit_alignment_prompt(source, target, tmp_path)
    assert path.exists()
    assert path.name == "_alignment.prompt.txt"
    # Simulate the host agent's response
    (tmp_path / "translations").mkdir()
    (tmp_path / "translations" / "_alignment.txt").write_text(
        "MATCH: A | 甲\n", encoding="utf-8",
    )
    aligns = read_alignment_response(tmp_path)
    assert aligns == [SectionAlignment("matched", "A", "甲")]


def test_read_alignment_returns_none_when_missing(tmp_path: Path):
    assert read_alignment_response(tmp_path) is None


def test_target_info_roundtrip(tmp_path: Path):
    target = _article("zh", "布雷特·懷特利", [
        Section(level=2, title="生平", anchor="", index="1"),
        Section(level=2, title="代表作", anchor="", index="2"),
    ])
    target.revision_id = 7777
    write_target_info(target, tmp_path)
    info = read_target_info(tmp_path)
    assert info["lang"] == "zh"
    assert info["title"] == "布雷特·懷特利"
    assert info["revision_id"] == 7777
    assert info["headings"] == ["生平", "代表作"]


def test_coverage_with_alignment_renders_table_and_plan():
    source = _article("en", "Brett Whiteley", [
        Section(level=2, title="Early life", anchor="", index="1"),
        Section(level=2, title="Reception", anchor="", index="2"),
    ])
    target = _article("zh", "布雷特·懷特利", [
        Section(level=2, title="早年生涯", anchor="", index="1"),
        Section(level=2, title="影響", anchor="", index="2"),
    ])
    coverage = compare_sections(source, target)
    aligns = [
        SectionAlignment("matched", "Early life", "早年生涯"),
        SectionAlignment("only-source", "Reception", None),
        SectionAlignment("only-target", None, "影響"),
    ]
    md = coverage_report_md(source, target, coverage, alignments=aligns)
    # Alignment table is present
    assert "| Kind | Source heading | Target heading |" in md
    assert "| matched | Early life | 早年生涯 |" in md
    # Merge plan tells the reviewer what to do with each row
    assert "Per-section merge plan" in md
    assert "Strong candidate to add" in md  # only-source action
    assert "Keep as-is" in md                # only-target action
    assert "side-by-side" in md              # matched action
