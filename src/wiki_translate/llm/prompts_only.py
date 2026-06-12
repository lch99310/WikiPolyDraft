"""Agent-driven LLM mode: write prompts to disk, expect the host agent
(Claude, Codex, etc.) to perform the translation and write results back.

This is the default mode for use inside Skills, where the host agent IS the LLM
and we don't want to require a separate API key.
"""

from __future__ import annotations

from pathlib import Path

from .base import TranslationResult, build_translation_prompt, parse_llm_response


class PromptsOnlyClient:
    """Writes prompts to a working directory. Reads completed translations from
    a parallel directory. The host agent fills in the gap between the two.
    """

    def __init__(self, work_dir: Path):
        self.work_dir = Path(work_dir)
        self.prompts_dir = self.work_dir / "prompts"
        self.translations_dir = self.work_dir / "translations"
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.translations_dir.mkdir(parents=True, exist_ok=True)

    def emit_prompt(
        self,
        section_id: str,
        section_heading: str,
        source_text: str,
        source_lang: str,
        target_lang: str,
        article_title: str,
    ) -> Path:
        prompt = build_translation_prompt(
            section_heading=section_heading,
            source_text=source_text,
            source_lang=source_lang,
            target_lang=target_lang,
            article_title=article_title,
        )
        path = self.prompts_dir / f"{section_id}.prompt.txt"
        path.write_text(prompt, encoding="utf-8")
        return path

    def read_translation(self, section_id: str) -> TranslationResult:
        path = self.translations_dir / f"{section_id}.txt"
        if not path.exists():
            raise FileNotFoundError(
                f"Translation for section '{section_id}' not found at {path}. "
                "The host agent must read the corresponding prompt file and write "
                "its translation to this path before finalize."
            )
        return parse_llm_response(path.read_text(encoding="utf-8"))
