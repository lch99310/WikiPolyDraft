# Example: Brett Whiteley (en → zh)

This directory contains the **actual output** the tool produces when translating
an English Wikipedia article into Chinese, end-to-end.

## ⚠️ About this example

The wikitext here was generated from a **small synthetic fixture** that mimics
the structural elements of a real Wikipedia article (Infobox, internal links,
`<ref>` citations, a wikitable), not from the live `en.wikipedia.org/wiki/Brett_Whiteley`
article. This lets us show realistic output without copying live Wikipedia
content into the repo, and lets the example run in environments without
outbound access to `*.wikipedia.org`.

To reproduce against the live article, run from a network that can reach
Wikipedia:

```bash
wiki-translate prepare https://en.wikipedia.org/wiki/Brett_Whiteley \
  --target zh --out ./wt-work
# (host agent translates each prompt in ./wt-work/prompts/)
wiki-translate finalize ./wt-work --out ./output
```

## What's in this directory

| File | Purpose |
|---|---|
| `Brett_Whiteley.wikitext` | The translated draft. Note the DRAFT banner, `{{LLM-assisted translation\|reviewed=no}}` template, translated section headings (`== 早年生涯 ==`), and preserved markup. |
| `edit-summary.txt` | CC BY-SA attribution edit summary. Paste this when publishing. |
| `talk-template.txt` | `{{Translated page}}` template for the article's talk page. |
| `review-notes.md` | The mandatory review checklist plus translator notes for each section. **A reviewer must work through this before publishing.** |

## What this example demonstrates

1. **Wiki markup preservation**: `{{Infobox}}`, `[[links|display]]`, `<ref>...</ref>`,
   `''italics''`, `'''bold'''`, and `{| wikitable |}` all survive intact.
2. **Section headings are translated** (`== Early life ==` → `== 早年生涯 ==`),
   not left in the source language.
3. **CC BY-SA attribution** is automatically generated in the format the
   English-Wikipedia community expects.
4. **DRAFT banner** is unconditionally injected at the top of the wikitext,
   making accidental publication visible.
5. **Translator notes** from the host agent are surfaced in `review-notes.md`
   so the reviewer knows where the AI made judgment calls.
