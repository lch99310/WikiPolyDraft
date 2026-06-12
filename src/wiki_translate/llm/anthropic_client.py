"""Standalone LLM mode: call the Anthropic API directly.

Used by `wiki-translate translate` (the one-shot CLI command). Requires
ANTHROPIC_API_KEY in the environment.
"""

from __future__ import annotations

import os

from .base import TranslationResult, build_translation_prompt, parse_llm_response


class AnthropicClient:
    def __init__(self, model: str = "claude-opus-4-7", max_tokens: int = 4096):
        try:
            import anthropic
        except ImportError as e:
            raise ImportError(
                "The 'anthropic' package is required for standalone mode. "
                "Install with: pip install 'wiki-translate[anthropic]'"
            ) from e

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Either set it, or use agent-driven mode (`wiki-translate prepare` + `finalize`)."
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def translate_section(
        self,
        section_heading: str,
        source_text: str,
        source_lang: str,
        target_lang: str,
        article_title: str,
    ) -> TranslationResult:
        prompt = build_translation_prompt(
            section_heading=section_heading,
            source_text=source_text,
            source_lang=source_lang,
            target_lang=target_lang,
            article_title=article_title,
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text_parts = [block.text for block in response.content if hasattr(block, "text")]
        return parse_llm_response("".join(text_parts))
