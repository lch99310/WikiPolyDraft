"""Tests for fetcher (URL parsing and wikitext splitting; no network)."""

import pytest

from wiki_translate.fetcher import parse_wikipedia_url, split_wikitext_by_sections


class TestParseUrl:
    def test_english(self):
        assert parse_wikipedia_url("https://en.wikipedia.org/wiki/Brett_Whiteley") == (
            "en",
            "Brett Whiteley",
        )

    def test_chinese_percent_encoded(self):
        # This URL encodes the simplified-character form; zh.wikipedia routes
        # between simplified and traditional variants on its own.
        url = "https://zh.wikipedia.org/wiki/%E4%B9%9D%E5%AD%90%E5%A4%BA%E5%AB%A1"
        assert parse_wikipedia_url(url) == ("zh", "九子夺嫡")

    def test_mobile_subdomain(self):
        assert parse_wikipedia_url("https://en.m.wikipedia.org/wiki/Sidney_Nolan") == (
            "en",
            "Sidney Nolan",
        )

    def test_dashed_lang(self):
        assert parse_wikipedia_url(
            "https://zh-yue.wikipedia.org/wiki/Foo"
        ) == ("zh-yue", "Foo")

    def test_not_wikipedia_url(self):
        with pytest.raises(ValueError):
            parse_wikipedia_url("https://example.com/wiki/Foo")

    def test_empty_title(self):
        with pytest.raises(ValueError):
            parse_wikipedia_url("https://en.wikipedia.org/wiki/")


class TestSplitWikitext:
    def test_no_sections(self):
        wt = "Just a lead paragraph with no headings."
        assert split_wikitext_by_sections(wt) == [("", wt)]

    def test_basic_split(self):
        wt = """Lead text.

== Early life ==
He was born in 1939.

== Career ==
He painted things.

=== Sub ===
Subsection body."""
        result = split_wikitext_by_sections(wt)
        assert len(result) == 4
        assert result[0] == ("", "Lead text.")
        assert result[1][0] == "== Early life =="
        assert "He was born in 1939." in result[1][1]
        assert result[2][0] == "== Career =="
        assert "He painted things." in result[2][1]
        assert result[3][0] == "=== Sub ==="
        assert result[3][1] == "Subsection body."

    def test_preserves_inner_markup(self):
        wt = """== Section ==
Some text with [[link]] and <ref>cite</ref>.

{| class="wikitable"
|-
| cell
|}"""
        result = split_wikitext_by_sections(wt)
        assert len(result) == 2
        body = result[1][1]
        assert "[[link]]" in body
        assert "<ref>cite</ref>" in body
        assert '{| class="wikitable"' in body
