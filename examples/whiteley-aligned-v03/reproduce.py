"""V0.3 demo: section alignment + URL reachability check.

Differs from the V0.1 Brett Whiteley example by simulating the harder case:
the target language (Chinese) already has a stub for Brett Whiteley with
partial coverage. Demonstrates:

  1. LLM-driven section alignment between the en source and the zh stub
     (the host agent answers `_alignment.prompt.txt`).
  2. The upgraded coverage report — alignment table + per-section merge plan
     telling the reviewer where to integrate vs. leave alone.
  3. Level 2 fact-check — citation URL reachability surfaced in
     review-notes.md (the URL check result is supplied as a fixture so
     the demo works offline).

Run from the repo root:
    python examples/whiteley-aligned-v03/reproduce.py
    # then translate prompts AND _alignment.prompt.txt
    # then: wiki-translate finalize examples/whiteley-aligned-v03/wt-work --out ./output
"""

import json
from pathlib import Path

from wiki_translate.comparator import emit_alignment_prompt, write_target_info
from wiki_translate.fetcher import Article, LangLink, Section
from wiki_translate.translator import prepare_agent_driven

SOURCE_WIKITEXT = """{{Infobox artist
| name = Brett Whiteley
| birth_date = 7 April 1939
| death_date = 15 June 1992
}}

'''Brett Whiteley''' (7 April 1939 – 15 June 1992) was an Australian [[painter]] known for his vivid colour palette and works depicting [[Sydney Harbour]].<ref>{{cite web|title=Australian Art profile|url=https://example.org/whiteley-profile}}</ref> He won the [[Archibald Prize]] three times.<ref name="archibald" />

== Early life ==
Whiteley was born in [[Sydney]] and studied at [[Julian Ashton Art School]].<ref>{{cite web|title=Whiteley early years|url=https://example.invalid/whiteley-bio}}</ref>

== Reception ==
Whiteley's exhibitions in the late 1970s drew strong critical attention.<ref name="archibald">{{cite journal|title=Whiteley and the Archibald|url=https://example.org/archibald-whiteley}}</ref>
"""

SOURCE_ARTICLE = Article(
    lang="en",
    title="Brett Whiteley",
    wikitext=SOURCE_WIKITEXT,
    sections=[
        Section(level=2, title="Early life", anchor="Early_life", index="1"),
        Section(level=2, title="Reception", anchor="Reception", index="2"),
    ],
    langlinks=[LangLink(lang="zh", title="布雷特·懷特利")],
    revision_id=111222333,
)

# The "existing" zh stub — partial coverage; covers Early life but not Reception,
# and has a section the source doesn't (影響).
TARGET_EXISTING = Article(
    lang="zh",
    title="布雷特·懷特利",
    wikitext="(omitted for fixture)",
    sections=[
        Section(level=2, title="早年生涯", anchor="", index="1"),
        Section(level=2, title="影響", anchor="", index="2"),
    ],
    langlinks=[],
    revision_id=999000111,
)

# Pretend the URL check ran. In a real run, `wiki-translate prepare --check-urls`
# would produce this file by HEAD-checking each citation URL.
URL_CHECK_FIXTURE = [
    {"url": "https://example.org/whiteley-profile", "status": "ok",
     "detail": "HTTP 200"},
    {"url": "https://example.invalid/whiteley-bio", "status": "error",
     "detail": "Name or service not known"},
    {"url": "https://example.org/archibald-whiteley", "status": "dead",
     "detail": "HTTP 404"},
]


def main() -> None:
    work_dir = Path(__file__).parent / "wt-work"
    if work_dir.exists():
        import shutil
        shutil.rmtree(work_dir)

    job = prepare_agent_driven(SOURCE_ARTICLE, target_lang="zh", work_dir=work_dir)
    # Wire in V0.3 artifacts the CLI would normally write for us.
    write_target_info(TARGET_EXISTING, work_dir)
    emit_alignment_prompt(SOURCE_ARTICLE, TARGET_EXISTING, work_dir)
    (work_dir / "url-check.json").write_text(
        json.dumps(URL_CHECK_FIXTURE, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Prepared {len(job.sections)} section(s) from en:Brett Whiteley -> zh")
    print(f"Source permalink: {job.permalink}")
    print(f"Target stub: zh:{TARGET_EXISTING.title} (revision {TARGET_EXISTING.revision_id})")
    print(f"\nPrompts written to {work_dir}/prompts/:")
    for section in job.sections:
        print(f"  - {section.section_id}: heading={section.heading!r}")
    print("  - _alignment.prompt.txt  <- align en sections against the zh stub")
    print(f"\nFixture URL check written to {work_dir}/url-check.json")
    print(f"\nNext: write translations and _alignment.txt under {work_dir}/translations/")
    print(f"Then: wiki-translate finalize {work_dir} --out ./output")


if __name__ == "__main__":
    main()
