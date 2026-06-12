"""Compare a source article with the existing target-language article (if any).

V0.2: structural coverage — list the level-2 headings on each side.
V0.3: LLM-driven cross-language section alignment plus a per-section merge
plan that tells the reviewer where to integrate translated content. We still
do NOT auto-merge or pick winners — the merge plan is a suggestion the
reviewer acts on, not edited output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .fetcher import Article


@dataclass
class SectionCoverage:
    source_headings: list[str] = field(default_factory=list)
    target_headings: list[str] = field(default_factory=list)


def compare_sections(source: Article, target_existing: Article) -> SectionCoverage:
    """List the level-2 section headings on each side.

    We do not attempt cross-language alignment (e.g. matching "Early life"
    to "早年生涯"); that requires an LLM and is V0.3 territory. The human
    reviewer aligns them using the side-by-side coverage report.
    """
    src_headings = [s.title for s in source.sections if s.level == 2 and s.title]
    tgt_headings = [s.title for s in target_existing.sections if s.level == 2 and s.title]
    return SectionCoverage(
        source_headings=src_headings,
        target_headings=tgt_headings,
    )


# --- V0.3: LLM-driven section alignment -------------------------------------


@dataclass
class SectionAlignment:
    """One row of the alignment table the LLM produces."""
    kind: str  # "matched" | "only-source" | "only-target"
    source_heading: str | None
    target_heading: str | None

    def merge_action(self, source_lang: str, target_lang: str) -> str:
        """Short, reviewer-facing suggestion for what to do with this row."""
        if self.kind == "matched":
            return (
                f"Both wikis have this section. Compare the translated "
                f"{source_lang}→{target_lang} draft with the existing target "
                f"section side-by-side. Integrate any genuinely new information; "
                f"do NOT overwrite."
            )
        if self.kind == "only-source":
            return (
                f"Only the {source_lang} side has this. Strong candidate to add "
                f"as a new section to the existing {target_lang} article using the "
                f"translated draft."
            )
        if self.kind == "only-target":
            return (
                f"Only the existing {target_lang} article has this. Keep as-is; "
                f"the source did not cover this topic."
            )
        return self.kind


_TARGET_INFO_FILENAME = "target-info.json"
_ALIGNMENT_PROMPT_FILENAME = "_alignment.prompt.txt"
_ALIGNMENT_OUTPUT_FILENAME = "_alignment.txt"


def write_target_info(target_existing: Article, work_dir: Path) -> Path:
    """Persist the minimal information about the existing target article
    that finalize needs to rebuild the coverage report.
    """
    import json
    info = {
        "lang": target_existing.lang,
        "title": target_existing.title,
        "article_url": target_existing.article_url,
        "revision_id": target_existing.revision_id,
        "headings": [s.title for s in target_existing.sections if s.level == 2 and s.title],
    }
    path = Path(work_dir) / _TARGET_INFO_FILENAME
    path.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def read_target_info(work_dir: Path) -> Optional[dict]:
    import json
    path = Path(work_dir) / _TARGET_INFO_FILENAME
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


_LANG_NAMES = {"en": "English", "zh": "Chinese", "ja": "Japanese", "es": "Spanish"}


def build_alignment_prompt(
    source: Article,
    target_existing: Article,
) -> str:
    """Prompt for the host agent to align section headings across the two wikis."""
    src_name = _LANG_NAMES.get(source.lang, source.lang)
    tgt_name = _LANG_NAMES.get(target_existing.lang, target_existing.lang)
    src_headings = [s.title for s in source.sections if s.level == 2 and s.title]
    tgt_headings = [s.title for s in target_existing.sections if s.level == 2 and s.title]

    def numbered(items: list[str]) -> str:
        if not items:
            return "  (none)"
        return "\n".join(f"  {i + 1}. {h}" for i, h in enumerate(items))

    return f"""You are aligning section headings between two language editions of \
the same Wikipedia article.

Article topic: {source.title}

Source ({src_name}) — {source.title}
Level-2 sections:
{numbered(src_headings)}

Existing target ({tgt_name}) — {target_existing.title}
Level-2 sections:
{numbered(tgt_headings)}

TASK
Produce one line per relationship using these forms, in this exact format:

MATCH: <source heading> | <target heading>
ONLY-SOURCE: <source heading>
ONLY-TARGET: <target heading>

RULES
1. MATCH only when the two headings cover SEMANTICALLY the same scope, not just
   when their wording is similar. "Early life" ⇔ "早年生涯" is a match;
   "Reception" ⇔ "影響" is NOT (reception ≠ influence).
2. Conservative is better than over-matching. When in doubt, mark
   ONLY-SOURCE / ONLY-TARGET rather than MATCH.
3. Every source heading must appear in exactly one line (MATCH or ONLY-SOURCE).
4. Every target heading must appear in exactly one line (MATCH or ONLY-TARGET).
5. Do not output anything else — no preamble, no explanation, no markdown.
"""


_MATCH_LINE_RE = re.compile(r"^\s*MATCH\s*:\s*(.+?)\s*\|\s*(.+?)\s*$", re.IGNORECASE)
_ONLY_SRC_RE = re.compile(r"^\s*ONLY[\s\-]?SOURCE\s*:\s*(.+?)\s*$", re.IGNORECASE)
_ONLY_TGT_RE = re.compile(r"^\s*ONLY[\s\-]?TARGET\s*:\s*(.+?)\s*$", re.IGNORECASE)


def parse_alignment_response(raw: str) -> list[SectionAlignment]:
    """Parse the host agent's alignment output. Lines that don't match any
    expected form are silently ignored (they're treated as commentary).
    """
    out: list[SectionAlignment] = []
    for line in raw.splitlines():
        m = _MATCH_LINE_RE.match(line)
        if m:
            out.append(SectionAlignment(
                kind="matched",
                source_heading=m.group(1).strip(),
                target_heading=m.group(2).strip(),
            ))
            continue
        m = _ONLY_SRC_RE.match(line)
        if m:
            out.append(SectionAlignment(
                kind="only-source",
                source_heading=m.group(1).strip(),
                target_heading=None,
            ))
            continue
        m = _ONLY_TGT_RE.match(line)
        if m:
            out.append(SectionAlignment(
                kind="only-target",
                source_heading=None,
                target_heading=m.group(1).strip(),
            ))
    return out


def emit_alignment_prompt(
    source: Article,
    target_existing: Article,
    work_dir: Path,
) -> Path:
    """Write the alignment prompt into the host agent's prompts/ directory."""
    prompts_dir = Path(work_dir) / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    path = prompts_dir / _ALIGNMENT_PROMPT_FILENAME
    path.write_text(build_alignment_prompt(source, target_existing), encoding="utf-8")
    return path


def read_alignment_response(work_dir: Path) -> Optional[list[SectionAlignment]]:
    """Read and parse the alignment response, if the host agent produced one."""
    path = Path(work_dir) / "translations" / _ALIGNMENT_OUTPUT_FILENAME
    if not path.exists():
        return None
    return parse_alignment_response(path.read_text(encoding="utf-8"))


def coverage_report_md(
    source: Article,
    target_existing: Article,
    coverage: SectionCoverage,
    alignments: list[SectionAlignment] | None = None,
) -> str:
    """Render the coverage report a human reviewer reads before merging.

    If `alignments` is provided (from an LLM run), an alignment table and
    merge plan replace the V0.2 placeholder.
    """
    return render_coverage_md(
        source_lang=source.lang,
        source_title=source.title,
        source_url=source.article_url,
        source_revision=source.revision_id,
        source_headings=coverage.source_headings,
        target_lang=target_existing.lang,
        target_title=target_existing.title,
        target_url=target_existing.article_url,
        target_revision=target_existing.revision_id,
        target_headings=coverage.target_headings,
        alignments=alignments,
    )


def render_coverage_md(
    *,
    source_lang: str,
    source_title: str,
    source_url: str,
    source_revision: int,
    source_headings: list[str],
    target_lang: str,
    target_title: str,
    target_url: str,
    target_revision: int,
    target_headings: list[str],
    alignments: list[SectionAlignment] | None,
) -> str:
    lines = [
        f"# Coverage report: {source_title}",
        "",
        f"Source ({source_lang}): [{source_title}]({source_url}) "
        f"(revision {source_revision})",
        "",
        f"Existing target ({target_lang}): "
        f"[{target_title}]({target_url}) "
        f"(revision {target_revision})",
        "",
        "## ⚠️ The target language already has an article",
        "",
        "**Do NOT overwrite the existing target article with the translated draft.** "
        "Instead:",
        "",
        "1. Compare the two section lists below.",
        "2. Identify which information in the draft is genuinely missing from the "
        "existing target article.",
        "3. Integrate (do not replace) into the existing target article, preserving "
        "its existing structure, citations, and stylistic conventions.",
        "4. The CC BY-SA attribution still applies for any content you add: see "
        "`edit-summary.txt` and `talk-template.txt`.",
        "",
        f"## Source article sections ({source_lang})",
        "",
    ]
    if source_headings:
        for h in source_headings:
            lines.append(f"- {h}")
    else:
        lines.append("_(no level-2 sections detected; article may be short or "
                     "consist of a single lead paragraph.)_")

    lines += [
        "",
        f"## Existing target article sections ({target_lang})",
        "",
    ]
    if target_headings:
        for h in target_headings:
            lines.append(f"- {h}")
    else:
        lines.append("_(no level-2 sections detected.)_")

    lines += ["", "## Cross-language section alignment", ""]

    if alignments is None:
        lines += [
            "Section alignment was not produced for this run. If you used the "
            "agent-driven workflow, the host agent should have read "
            "`prompts/_alignment.prompt.txt` and written its answer to "
            "`translations/_alignment.txt`; rerun `wiki-translate finalize` once "
            "that file exists to regenerate this report with an alignment table "
            "and per-section merge plan.",
            "",
        ]
    elif not alignments:
        lines += [
            "The alignment response could not be parsed. Manually map the two "
            "section lists above when deciding what to merge.",
            "",
        ]
    else:
        lines += [
            "| Kind | Source heading | Target heading |",
            "| --- | --- | --- |",
        ]
        for a in alignments:
            s = a.source_heading or "—"
            t = a.target_heading or "—"
            lines.append(f"| {a.kind} | {s} | {t} |")
        lines += ["", "## Per-section merge plan", ""]
        for i, a in enumerate(alignments, start=1):
            heading_label = (
                f"`{a.source_heading}` ⇔ `{a.target_heading}`"
                if a.kind == "matched"
                else f"`{a.source_heading or a.target_heading}`"
            )
            lines.append(f"{i}. **{a.kind}** — {heading_label}")
            lines.append(f"   - {a.merge_action(source_lang, target_lang)}")
        lines.append("")

    return "\n".join(lines) + "\n"
