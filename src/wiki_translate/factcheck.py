"""Level 1 source-integrity checks for translations.

Compares the `<ref>` citations in the source section with those in the
translated section. Flags:

- **missing**: a citation was in the source but is gone from the translation
- **extra**: the translation has a citation that wasn't in the source
  (almost certainly an LLM hallucination — refs are not invented)
- **content_changed**: a named ref was preserved but its content was modified
  (the LLM is told to keep refs verbatim; any change needs review)

These are mechanical checks. They do not verify that the cited source is
reliable, that it actually supports the claim, or that the URL still works
(those are Level 2 and Level 3, deferred to V0.3).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


_REF_RE = re.compile(
    r"<ref(?P<attrs>\s[^>]*)?(?:/\s*>|>(?P<content>.*?)</ref\s*>)",
    re.DOTALL | re.IGNORECASE,
)
_REF_NAME_RE = re.compile(
    r"""name\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s/>]+))""",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Ref:
    name: str | None
    content: str  # "" for self-closing or pure-name refs


@dataclass
class RefIssue:
    section_id: str
    heading: str
    kind: str  # "missing" | "extra" | "content_changed"
    detail: str


def extract_refs(text: str) -> list[Ref]:
    """Extract all <ref> citations from a chunk of wikitext."""
    refs: list[Ref] = []
    for m in _REF_RE.finditer(text):
        attrs = m.group("attrs") or ""
        name_m = _REF_NAME_RE.search(attrs)
        name: str | None = None
        if name_m:
            name = name_m.group(1) or name_m.group(2) or name_m.group(3)
        content = (m.group("content") or "").strip()
        refs.append(Ref(name=name, content=content))
    return refs


def check_ref_integrity(
    section_id: str,
    heading: str,
    source_text: str,
    translated_text: str,
) -> list[RefIssue]:
    """Compare refs between source and translation; return discrepancies.

    Matching strategy (greedy, in order):
      1. Exact match on (name, content) — perfect preservation.
      2. Match on name when both sides specify the same ref name — content
         differs, which is flagged as `content_changed`.
      3. Match on content alone — same citation, name attribute changed or
         dropped (we treat this as preserved; the citation text is the
         meaningful part).
    Refs that fail all three are reported as missing (source side) or
    extra (translation side).
    """
    src_refs = list(extract_refs(source_text))
    tgt_refs = list(extract_refs(translated_text))
    issues: list[RefIssue] = []

    src_remaining = list(src_refs)
    for tgt in tgt_refs:
        matched_idx: int | None = None

        # 1. exact (name, content)
        for i, s in enumerate(src_remaining):
            if s.name == tgt.name and s.content == tgt.content:
                matched_idx = i
                break

        # 2. same name, different content
        if matched_idx is None and tgt.name:
            for i, s in enumerate(src_remaining):
                if s.name == tgt.name:
                    matched_idx = i
                    if s.content != tgt.content:
                        issues.append(RefIssue(
                            section_id=section_id,
                            heading=heading,
                            kind="content_changed",
                            detail=(
                                f"<ref name=\"{tgt.name}\"> content changed in "
                                f"translation. Source: {s.content[:80]!r}; "
                                f"translation: {tgt.content[:80]!r}"
                            ),
                        ))
                    break

        # 3. same content, name dropped/changed — treat as preserved
        if matched_idx is None:
            for i, s in enumerate(src_remaining):
                if s.content and s.content == tgt.content:
                    matched_idx = i
                    break

        if matched_idx is None:
            issues.append(RefIssue(
                section_id=section_id,
                heading=heading,
                kind="extra",
                detail=(
                    "Translation has a <ref> with no counterpart in the source. "
                    "Likely hallucination — verify and remove if invented. "
                    f"Ref content: {tgt.content[:80]!r}"
                ),
            ))
        else:
            src_remaining.pop(matched_idx)

    for missing in src_remaining:
        label = f"<ref name=\"{missing.name}\">" if missing.name else "<ref>"
        issues.append(RefIssue(
            section_id=section_id,
            heading=heading,
            kind="missing",
            detail=(
                f"Source {label} was dropped from the translation. "
                f"Citation content: {missing.content[:80]!r}"
            ),
        ))

    return issues
