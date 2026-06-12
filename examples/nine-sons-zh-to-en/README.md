# Example: 九子奪嫡 (zh → en)

This is the inverse case to `brett-whiteley-en-to-zh/`: a topic where the
**Chinese** Wikipedia has rich coverage and the **English** Wikipedia does not.
A 九子奪嫡 article on `en.wikipedia.org` does not currently exist, so this
demonstrates the pure-translation path with no existing target version
to compare against.

## ⚠️ About this example

The wikitext was generated from a small synthetic fixture (mimicking the
structural elements of a real article — Infobox-free lead, multiple `<ref>`
citations including a named back-reference, and a wikitable of participants),
not from the live `zh.wikipedia.org/wiki/九子奪嫡` article. This lets the
example run in environments without outbound access to `*.wikipedia.org`.

Run `reproduce.py` to regenerate; on a network that can reach Wikipedia,
the same workflow against the live article looks like:

```bash
wiki-translate prepare https://zh.wikipedia.org/wiki/九子奪嫡 --target en --out ./wt-work
# (host agent translates each prompt in ./wt-work/prompts/)
wiki-translate finalize ./wt-work --out ./output
```

## What's in this directory

| File | Purpose |
|---|---|
| `Nine_Lords_War.wikitext` | The translated English draft, with DRAFT banner and `{{LLM-assisted translation\|reviewed=no}}` template |
| `edit-summary.txt` | CC BY-SA attribution edit summary (cites the zh source permalink) |
| `talk-template.txt` | `{{Translated page}}` template for the en talk page |
| `review-notes.md` | Mandatory checklist + per-section translator notes |

## What this example demonstrates beyond the Brett Whiteley case

1. **Reverse direction works**: ZH→EN through the same prompt/translation
   pipeline; section headings (`== 背景 ==`) translate (`== Background ==`).
2. **Named back-references are preserved**: `<ref name="qingshi" />` in the
   lead and the matching `<ref name="qingshi">…</ref>` later both survive
   through factcheck without being flagged.
3. **Wikitable structure survives** including row/column markers (`|-`,
   `||`, `!`, `! !!`) and `[[wikilinks]]` inside cells.
4. **Translator notes flag real translation judgment calls** — Pinyin vs
   Wade-Giles, faction naming conventions, the (no canonical English name)
   for the topic itself — exactly the things a human reviewer must adjudicate.
