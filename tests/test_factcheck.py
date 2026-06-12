"""Tests for factcheck Levels 1 (ref integrity) and 2 (URL reachability)."""

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
import requests

from wiki_translate.factcheck import (
    Ref,
    UrlCheck,
    check_ref_integrity,
    check_url_reachability,
    extract_ref_urls,
    extract_refs,
)


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


class TestExtractRefUrls:
    def test_one_url_per_ref(self):
        wt = (
            "Body <ref>{{cite web|url=https://example.com/a}}</ref> "
            "more <ref name=\"b\">https://example.org/b page</ref> end"
        )
        assert extract_ref_urls(wt) == ["https://example.com/a", "https://example.org/b"]

    def test_dedup(self):
        wt = (
            "<ref>https://example.com/a</ref> "
            "<ref name=\"dup\">https://example.com/a alt</ref>"
        )
        assert extract_ref_urls(wt) == ["https://example.com/a"]

    def test_trims_trailing_punctuation(self):
        wt = "<ref>see https://example.com/page.</ref>"
        assert extract_ref_urls(wt) == ["https://example.com/page"]

    def test_ignores_urls_outside_refs(self):
        wt = "Body text https://example.com/inline more <ref>https://cite.example.com</ref>"
        assert extract_ref_urls(wt) == ["https://cite.example.com"]


class TestCheckUrlReachability:
    def _session_returning(self, status_code: int):
        sess = MagicMock()
        resp = MagicMock()
        resp.status_code = status_code
        sess.head.return_value = resp
        return sess

    def test_ok_status(self):
        sess = self._session_returning(200)
        results = check_url_reachability(["https://example.com/a"], session=sess)
        assert results == [UrlCheck(url="https://example.com/a", status="ok", detail="HTTP 200")]

    def test_dead_404(self):
        sess = self._session_returning(404)
        results = check_url_reachability(["https://example.com/missing"], session=sess)
        assert results[0].status == "dead"
        assert "404" in results[0].detail

    def test_405_falls_back_to_get(self):
        sess = MagicMock()
        head_resp = MagicMock(status_code=405)
        get_resp = MagicMock(status_code=200)
        sess.head.return_value = head_resp
        sess.get.return_value = get_resp
        results = check_url_reachability(["https://example.com/x"], session=sess)
        assert results[0].status == "ok"
        sess.get.assert_called_once()

    def test_timeout_handled(self):
        sess = MagicMock()
        sess.head.side_effect = requests.exceptions.Timeout()
        results = check_url_reachability(["https://example.com/slow"], session=sess, timeout=1.0)
        assert results[0].status == "timeout"

    def test_generic_request_error_handled(self):
        sess = MagicMock()
        sess.head.side_effect = requests.exceptions.ConnectionError("dns")
        results = check_url_reachability(["https://nope.invalid"], session=sess)
        assert results[0].status == "error"
        assert "dns" in results[0].detail
