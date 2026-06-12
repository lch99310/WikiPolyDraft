# wiki-translate

AI-assisted Wikipedia article translation tool that produces **drafts for human review** — designed to help editors prepare cross-language Wikipedia translations more efficiently while respecting Wikipedia community policy.

## ⚠️ Important Notice / 重要聲明

**This tool produces DRAFTS, not publishable articles.**
本工具產出的是「草稿」，不是「可直接發布的條目」。

- Wikipedia policy requires human review by editors fluent in both languages before any translated content is published. **This tool does NOT replace that review.**
- 維基百科政策要求：所有翻譯內容必須由精通雙語的人類編輯審核後才能發布。**本工具不替代該審核流程。**
- The author is **not affiliated** with the Wikimedia Foundation or any Wikipedia community.
- The author assumes **no liability** for content published using this tool. Users are solely responsible for compliance with Wikipedia policies, copyright law, and the CC BY-SA 4.0 license.
- Misuse — for example, publishing unreviewed AI translations into Wikipedia mainspace — **violates Wikipedia community guidelines** (see [Wikipedia:LLM-assisted translation](https://en.wikipedia.org/wiki/Wikipedia:LLM-assisted_translation)) and may result in account sanctions for the user.

## Motivation

Wikipedia articles on the same topic often differ greatly in depth across languages, because volunteer editors are naturally more familiar with topics in their own language. This means readers in other languages may have limited access to the same body of knowledge.

This project explores whether modern LLMs can help **human editors** prepare high-quality cross-language drafts more efficiently, while keeping humans firmly in the loop for the review and publication steps that Wikipedia policy requires.

The first phase supports **English ↔ Chinese** translation.

## How It Works

```
URL → fetch wikitext + langlinks → prepare prompts → LLM translates →
      formatter adds CC BY-SA attribution + DRAFT banner → review-notes.md →
      human editor reviews → human editor publishes
```

Two LLM modes:

- **Agent-driven (default for Skills)**: The CLI emits prompt files. A host agent (Claude Code, Codex, etc.) reads them, performs the translation in conversation, and writes results back. Zero API key needed; allows interactive refinement.
- **Standalone**: The CLI calls an LLM API directly (Anthropic; OpenAI/Gemini planned). User brings their own API key.

## Install

```bash
pip install -e .
# or, with Anthropic standalone support:
pip install -e ".[anthropic]"
```

## Quick Start

### Agent-driven mode (recommended for use inside Claude Code / Codex CLI)

```bash
# Step 1: fetch source + target-language version, emit prompt files
wiki-translate prepare https://en.wikipedia.org/wiki/Brett_Whiteley \
  --target zh --out ./wt-work

# Step 2: (your agent reads ./wt-work/prompts/*.txt, performs translation,
#          writes results to ./wt-work/translations/)

# Step 3: assemble final draft with CC BY-SA attribution + review-notes
wiki-translate finalize ./wt-work --out ./output
```

### Standalone mode

```bash
export ANTHROPIC_API_KEY=sk-...
wiki-translate translate https://en.wikipedia.org/wiki/Brett_Whiteley \
  --target zh --out ./output
```

## Output Files

For each translated article, `output/<title>/` contains:

| File | Purpose |
|---|---|
| `<title>.wikitext` | The translated draft, with `{{LLM-assisted translation\|reviewed=no}}` template and a DRAFT banner |
| `edit-summary.txt` | Ready-to-paste edit summary with original article permalink (required by CC BY-SA attribution) |
| `talk-template.txt` | `{{Translated page}}` template for the article's talk page (required by CC BY-SA attribution) |
| `review-notes.md` | Hallucination candidates, low-confidence sections, source verification results |

**The publishing editor must open `review-notes.md` and verify each item.** The DRAFT banner and `reviewed=no` flag ensure the maintenance category is visible to other editors if published prematurely.

## Wikipedia Policy Compliance

This tool is designed around [Wikipedia:LLM-assisted translation](https://en.wikipedia.org/wiki/Wikipedia:LLM-assisted_translation):

1. The tool produces drafts; the human editor must be skilled in both languages to verify the translation.
2. The output automatically includes the `{{LLM-assisted translation}}` template.
3. `review-notes.md` highlights items the editor must check (hallucinations, sources, citations).
4. Attribution is generated in the format required by CC BY-SA 4.0 (edit summary + `{{Translated page}}` on talk).
5. The CLI has **no** `--publish` flag and does not call the Wikipedia edit API.

## Examples

Three end-to-end examples are checked in, each with its own `reproduce.py`
that drives the pipeline against a synthetic fixture (so they run offline):

- [`examples/brett-whiteley-en-to-zh/`](examples/brett-whiteley-en-to-zh/) —
  English to Chinese translation when no target article exists.
- [`examples/nine-sons-zh-to-en/`](examples/nine-sons-zh-to-en/) —
  Chinese to English translation of 九子奪嫡 — the rich-on-one-wiki,
  missing-on-the-other asymmetry that motivated this tool.
- [`examples/whiteley-aligned-v03/`](examples/whiteley-aligned-v03/) —
  Brett Whiteley with an **existing zh stub**: demonstrates LLM-driven
  cross-language section alignment, the per-section merge plan, and the
  Level 2 URL reachability check surfaced in `review-notes.md`.

If the source article has a langlink to an existing target-language article,
`wiki-translate prepare` additionally fetches that article, writes a
coverage-report skeleton, and emits an `_alignment.prompt.txt` for the host
agent. After translation, `finalize` upgrades the coverage report with the
alignment result and a per-section merge plan. Add `--check-urls` to also
HEAD-check every citation URL.

## Project Status

Early. See plan and [CONTRIBUTING.md](CONTRIBUTING.md).

## Contributing

We welcome contributions that improve translation quality, expand language support, or strengthen the review-assistance features. **We do not accept pull requests that add automated publishing to Wikipedia** — see CONTRIBUTING.md.

## License

MIT — see [LICENSE](LICENSE).
