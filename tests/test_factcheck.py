"""Tests for factcheck Level 1 (ref integrity)."""

from wiki_translate.factcheck import Ref, check_ref_integrity, extract_refs


class TestExtractRefs:
    def test_simple_ref(self):
        refs = extract_refs("body <ref>{{cite book|title=X}}</ref> more")
        assert refs == [Ref(name=None, content="{{cite book|title=X}}")]

    def test_named_ref(self):
        refs = extract_refs('body <ref name="foo">cite</ref>')
        assert refs == [Ref(name="foo", content="cite")]

    def test_self_closing(self):
        refs = extract_refs('see <ref name="foo" />')
        assert refs == [Ref(name="foo", content="")]

    def test_multiple_refs(self):
        text = (
            'first <ref>A</ref> middle <ref name="b">B</ref> end <ref name="c" />'
        )
        refs = extract_refs(text)
        assert refs == [
            Ref(name=None, content="A"),
            Ref(name="b", content="B"),
            Ref(name="c", content=""),
        ]

    def test_unquoted_name(self):
        # MediaWiki allows unquoted ref names for simple identifiers.
        refs = extract_refs("<ref name=foo>X</ref>")
        assert refs == [Ref(name="foo", content="X")]

    def test_multiline_ref(self):
        refs = extract_refs("<ref>line1\nline2</ref>")
        assert refs == [Ref(name=None, content="line1\nline2")]


class TestCheckRefIntegrity:
    def test_identical_passes(self):
        src = "Text <ref>A</ref> more."
        tgt = "文字 <ref>A</ref> 更多。"
        issues = check_ref_integrity("id", "h", src, tgt)
        assert issues == []

    def test_missing_ref_flagged(self):
        src = 'Two cites <ref>A</ref> here <ref name="b">B</ref>.'
        tgt = "兩個引用 <ref>A</ref> 在這裡。"  # dropped <ref name="b">
        issues = check_ref_integrity("s1", "h", src, tgt)
        assert len(issues) == 1
        assert issues[0].kind == "missing"
        assert "name=\"b\"" in issues[0].detail

    def test_extra_ref_flagged_as_likely_hallucination(self):
        src = "One cite <ref>A</ref>."
        tgt = "一個引用 <ref>A</ref> 加上額外的 <ref>FAKE</ref>。"
        issues = check_ref_integrity("s1", "h", src, tgt)
        assert len(issues) == 1
        assert issues[0].kind == "extra"
        assert "hallucination" in issues[0].detail.lower()

    def test_named_ref_content_changed(self):
        src = '<ref name="x">original content</ref>'
        tgt = '<ref name="x">altered content</ref>'
        issues = check_ref_integrity("s", "h", src, tgt)
        assert len(issues) == 1
        assert issues[0].kind == "content_changed"

    def test_name_drop_with_same_content_is_ok(self):
        # If the LLM dropped only the name attribute but kept the content
        # verbatim, that's a preservation; no issue.
        src = '<ref name="foo">cite content</ref>'
        tgt = "<ref>cite content</ref>"
        issues = check_ref_integrity("s", "h", src, tgt)
        assert issues == []
