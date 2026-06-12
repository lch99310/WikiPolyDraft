"""Translation orchestrator: splits the source article into sections, runs each
through the LLM (standalone or agent-driven), and collects results.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .fetcher import Article, split_wikitext_by_sections
from .llm.base import TranslationResult
from .llm.prompts_only import PromptsOnlyClient


@dataclass
class SectionUnit:
    section_id: str
    heading: str
    source_text: str


@dataclass
class PreparedJob:
    """State persisted between `prepare` and `finalize` in agent-driven mode."""
    source_lang: str
    target_lang: str
    article_title: str
    article_url: str
    revision_id: int
    permalink: str
    target_existing_title: str | None
    sections: list[SectionUnit] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(
            {
                "source_lang": self.source_lang,
                "target_lang": self.target_lang,
                "article_title": self.article_title,
                "article_url": self.article_url,
                "revision_id": self.revision_id,
                "permalink": self.permalink,
                "target_existing_title": self.target_existing_title,
                "sections": [asdict(s) for s in self.sections],
            },
            ensure_ascii=False,
            indent=2,
        )

    @classmethod
    def from_json(cls, raw: str) -> "PreparedJob":
        data = json.loads(raw)
        return cls(
            source_lang=data["source_lang"],
            target_lang=data["target_lang"],
            article_title=data["article_title"],
            article_url=data["article_url"],
            revision_id=data["revision_id"],
            permalink=data["permalink"],
            target_existing_title=data.get("target_existing_title"),
            sections=[SectionUnit(**s) for s in data["sections"]],
        )


_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_\-]+")


def _slugify(text: str, index: int) -> str:
    base = _SAFE_ID_RE.sub("-", text)[:40].strip("-").lower() or "section"
    return f"{index:03d}-{base}"


def article_to_section_units(article: Article) -> list[SectionUnit]:
    chunks = split_wikitext_by_sections(article.wikitext)
    units: list[SectionUnit] = []
    for i, (heading, body) in enumerate(chunks):
        if not body.strip():
            continue
        section_id = _slugify(heading or "lead", i)
        units.append(SectionUnit(section_id=section_id, heading=heading, source_text=body))
    return units


def prepare_agent_driven(
    source: Article,
    target_lang: str,
    work_dir: Path,
) -> PreparedJob:
    """Emit prompts and a manifest for the host agent to translate.

    The agent should:
      1. Read each work_dir/prompts/<section_id>.prompt.txt
      2. Perform the translation (as instructed in the prompt)
      3. Write the result to work_dir/translations/<section_id>.txt
      4. Run `wiki-translate finalize <work_dir>`
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    units = article_to_section_units(source)
    target_existing = source.langlink_for(target_lang)

    job = PreparedJob(
        source_lang=source.lang,
        target_lang=target_lang,
        article_title=source.title,
        article_url=source.article_url,
        revision_id=source.revision_id,
        permalink=source.permalink,
        target_existing_title=target_existing,
        sections=units,
    )
    (work_dir / "job.json").write_text(job.to_json(), encoding="utf-8")

    client = PromptsOnlyClient(work_dir)
    for unit in units:
        client.emit_prompt(
            section_id=unit.section_id,
            section_heading=unit.heading,
            source_text=unit.source_text,
            source_lang=source.lang,
            target_lang=target_lang,
            article_title=source.title,
        )

    _emit_agent_readme(work_dir, job)
    return job


def collect_translations(work_dir: Path, job: PreparedJob) -> list[tuple[SectionUnit, TranslationResult]]:
    """Read the agent's translation outputs back. Raises if any are missing."""
    client = PromptsOnlyClient(work_dir)
    results: list[tuple[SectionUnit, TranslationResult]] = []
    missing: list[str] = []
    for unit in job.sections:
        try:
            result = client.read_translation(unit.section_id)
        except FileNotFoundError:
            missing.append(unit.section_id)
            continue
        results.append((unit, result))
    if missing:
        raise RuntimeError(
            "Missing translation files for sections: "
            + ", ".join(missing)
            + "\nThe host agent must complete all translations before finalize."
        )
    return results


def translate_standalone(
    source: Article,
    target_lang: str,
    client,
) -> list[tuple[SectionUnit, TranslationResult]]:
    """One-shot translation using a standalone LLM client."""
    units = article_to_section_units(source)
    results: list[tuple[SectionUnit, TranslationResult]] = []
    for unit in units:
        res = client.translate_section(
            section_heading=unit.heading,
            source_text=unit.source_text,
            source_lang=source.lang,
            target_lang=target_lang,
            article_title=source.title,
        )
        results.append((unit, res))
    return results


def _emit_agent_readme(work_dir: Path, job: PreparedJob) -> None:
    target_note = (
        f"\n  Note: The target language Wikipedia already has an article titled "
        f"'{job.target_existing_title}'. The reviewing editor should compare and merge "
        f"manually; this MVP only translates the source article.\n"
        if job.target_existing_title
        else ""
    )
    body = f"""# Agent translation work directory

Translating: {job.article_title} ({job.source_lang} -> {job.target_lang})
Source permalink: {job.permalink}
{target_note}
## Your task (host agent)

1. For each file in `prompts/`, read it and follow the instructions inside.
2. Write your translation to `translations/<same-section-id>.txt`.
   - The filename must match: a prompt at `prompts/001-lead.prompt.txt`
     produces a translation at `translations/001-lead.txt`.
3. When all sections are translated, the user (or you) runs:
   `wiki-translate finalize {work_dir}`

## Reminder

This produces a DRAFT for human review. Per Wikipedia:LLM-assisted_translation,
the publishing editor must be fluent in both languages and must verify all
content and citations before any publication.
"""
    (work_dir / "AGENT_README.md").write_text(body, encoding="utf-8")
