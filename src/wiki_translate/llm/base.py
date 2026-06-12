"""Abstract LLM client interface.

Two concrete implementations:
- PromptsOnlyClient (agent-driven mode): writes prompts to disk for a host
  agent (Claude Code, Codex, etc.) to execute, then reads results back.
- AnthropicClient (standalone mode): calls the Anthropic API directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class TranslationResult:
    translated_text: str
    notes: str = ""  # translator notes (uncertain terms, judgments made, etc.)


class LLMClient(Protocol):
    def translate_section(
        self,
        section_heading: str,
        source_text: str,
        source_lang: str,
        target_lang: str,
        article_title: str,
    ) -> TranslationResult: ...


def build_translation_prompt(
    section_heading: str,
    source_text: str,
    source_lang: str,
    target_lang: str,
    article_title: str,
) -> str:
    """Construct the translation prompt sent to the LLM.

    The prompt is shared between standalone and agent-driven modes so behavior
    is consistent.
    """
    lang_names = {"en": "English", "zh": "Chinese", "ja": "Japanese", "es": "Spanish"}
    src = lang_names.get(source_lang, source_lang)
    tgt = lang_names.get(target_lang, target_lang)
    heading_note = f" (section heading: {section_heading})" if section_heading else " (lead section)"

    return f"""You are translating a Wikipedia article section from {src} to {tgt}.

Article title: {article_title}
Source language: {src}
Target language: {tgt}
This is part of the article{heading_note}.

CRITICAL RULES:
1. Preserve ALL wiki markup exactly: [[links]], {{{{templates}}}}, <ref>citations</ref>,
   tables ({{| ... |}}), lists, italics ('' ''), bold (''' '''), etc.
2. Translate ONLY the natural-language text. Do NOT translate template names,
   parameter names, citation URLs, or category names inside [[Category:...]].
3. For internal links [[X]] or [[X|Y]]: keep the link target X as-is (it points
   to the {src} Wikipedia). The reviewing editor will resolve the link to the
   {tgt} equivalent if one exists.
4. Preserve all <ref>...</ref> citations unchanged.
5. If the source begins with a section heading written as `== Heading ==` (or
   `=== Subheading ===` etc.), translate the heading TEXT into {tgt} but keep
   the surrounding `==` markers exactly as they appear.
6. If you encounter a term whose translation is uncertain (proper nouns, technical
   terms, ambiguous phrasing), keep the source term in parentheses after the
   translation, e.g. "巴雷特·惠特利 (Brett Whiteley)".
7. Do NOT add information that is not in the source. Do NOT remove information.
8. Do NOT add your own commentary, opinions, or explanations to the article body.

OUTPUT FORMAT:
Return ONLY the translated section body (no preamble, no closing remarks).
If you have translator notes for the human reviewer (uncertain terms, decisions
made, possible hallucination risks), put them after a line containing exactly:
---TRANSLATOR-NOTES---
and write them in {tgt} or English.

SOURCE TEXT:
{source_text}
"""


def parse_llm_response(raw: str) -> TranslationResult:
    """Parse an LLM response, splitting body from translator notes."""
    marker = "---TRANSLATOR-NOTES---"
    if marker in raw:
        body, _, notes = raw.partition(marker)
        return TranslationResult(translated_text=body.strip(), notes=notes.strip())
    return TranslationResult(translated_text=raw.strip(), notes="")
