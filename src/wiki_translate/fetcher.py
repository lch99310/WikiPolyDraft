"""Fetch Wikipedia articles via the MediaWiki Action API.

We use the Action API directly rather than only Wikipedia-API because we need:
- wikitext (to preserve formatting in the translation)
- langlinks (to detect existing target-language version)
- the current revision id (for CC BY-SA attribution permalinks)
- section structure
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import unquote, urlparse

import requests

USER_AGENT = (
    "wiki-translate/0.1 (https://github.com/lch99310/wikipedia-translation; "
    "draft-only, human-review required)"
)


@dataclass
class Section:
    level: int
    title: str
    anchor: str
    index: str


@dataclass
class LangLink:
    lang: str
    title: str


@dataclass
class Article:
    lang: str
    title: str
    wikitext: str
    sections: list[Section] = field(default_factory=list)
    langlinks: list[LangLink] = field(default_factory=list)
    revision_id: int = 0

    @property
    def permalink(self) -> str:
        return f"https://{self.lang}.wikipedia.org/w/index.php?oldid={self.revision_id}"

    @property
    def article_url(self) -> str:
        return f"https://{self.lang}.wikipedia.org/wiki/{self.title.replace(' ', '_')}"

    def langlink_for(self, lang: str) -> Optional[str]:
        for ll in self.langlinks:
            if ll.lang == lang:
                return ll.title
        return None


def parse_wikipedia_url(url: str) -> tuple[str, str]:
    """Parse a Wikipedia URL into (lang, title).

    Examples:
        https://en.wikipedia.org/wiki/Brett_Whiteley -> ("en", "Brett Whiteley")
        https://zh.wikipedia.org/wiki/九子奪嫡 -> ("zh", "九子奪嫡")
    """
    parsed = urlparse(url)
    host_match = re.match(r"^([a-z\-]+)\.(?:m\.)?wikipedia\.org$", parsed.netloc)
    if not host_match:
        raise ValueError(f"Not a Wikipedia URL: {url}")
    lang = host_match.group(1)

    path = parsed.path
    if not path.startswith("/wiki/"):
        raise ValueError(f"Unexpected Wikipedia URL path: {path}")
    title = unquote(path[len("/wiki/"):]).replace("_", " ")
    if not title:
        raise ValueError(f"Empty article title in URL: {url}")
    return lang, title


def fetch_article(lang: str, title: str, session: Optional[requests.Session] = None) -> Article:
    """Fetch wikitext, sections, langlinks, and revision id for one article."""
    session = session or _make_session()
    api_url = f"https://{lang}.wikipedia.org/w/api.php"

    parse_params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext|sections|langlinks|revid",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
    }
    resp = session.get(api_url, params=parse_params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"MediaWiki API error for {lang}:{title}: {data['error']}")

    parse = data["parse"]
    wikitext = parse.get("wikitext", "")
    resolved_title = parse.get("title", title)
    revision_id = int(parse.get("revid", 0))

    sections = [
        Section(
            level=int(s.get("level", 2)),
            title=s.get("line", ""),
            anchor=s.get("anchor", ""),
            index=str(s.get("index", "")),
        )
        for s in parse.get("sections", [])
    ]

    langlinks = [
        LangLink(lang=ll.get("lang", ""), title=ll.get("title", ""))
        for ll in parse.get("langlinks", [])
        if ll.get("lang") and ll.get("title")
    ]

    return Article(
        lang=lang,
        title=resolved_title,
        wikitext=wikitext,
        sections=sections,
        langlinks=langlinks,
        revision_id=revision_id,
    )


def fetch_article_from_url(url: str, session: Optional[requests.Session] = None) -> Article:
    lang, title = parse_wikipedia_url(url)
    return fetch_article(lang, title, session=session)


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


_SECTION_HEADING_RE = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$", re.MULTILINE)


def split_wikitext_by_sections(wikitext: str) -> list[tuple[str, str]]:
    """Split wikitext into [(heading, body), ...].

    The first element has heading="" and contains the lead (text before the
    first section heading). Each subsequent element is one section.
    """
    matches = list(_SECTION_HEADING_RE.finditer(wikitext))
    if not matches:
        return [("", wikitext)]

    chunks: list[tuple[str, str]] = []
    first_start = matches[0].start()
    lead = wikitext[:first_start].rstrip()
    chunks.append(("", lead))

    for i, m in enumerate(matches):
        heading = m.group(0).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(wikitext)
        body = wikitext[body_start:body_end].strip()
        chunks.append((heading, body))

    return chunks
