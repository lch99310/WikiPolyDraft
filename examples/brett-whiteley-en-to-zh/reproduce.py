"""Reproduce the example outputs in this directory without hitting the network.

Drives `prepare_agent_driven` with a synthetic fixture that mimics the
structural elements of a Wikipedia article (Infobox, internal links, <ref>,
italics, wikitable). Lets you exercise the prepare -> translate -> finalize
pipeline locally even when the live Wikipedia API is unreachable.

Run from the repo root:
    python examples/brett-whiteley-en-to-zh/reproduce.py
    # then translate each prompt in examples/brett-whiteley-en-to-zh/wt-work/prompts/
    # then: wiki-translate finalize examples/brett-whiteley-en-to-zh/wt-work --out ./output
"""

from pathlib import Path

from wiki_translate.fetcher import Article, LangLink, Section
from wiki_translate.translator import prepare_agent_driven

FIXTURE_WIKITEXT = """{{Infobox artist
| name = Brett Whiteley
| birth_date = 7 April 1939
| death_date = 15 June 1992
}}

'''Brett Whiteley''' (7 April 1939 – 15 June 1992) was an Australian [[painter]]
known for his vivid colour palette and works depicting [[Sydney Harbour]].<ref>{{cite book|title=Australian Art|year=2001}}</ref> He won the [[Archibald Prize]] three times.<ref name="archibald" />

== Early life ==
Whiteley was born in [[Sydney]] and studied at [[Julian Ashton Art School]].<ref>{{cite news|title=Whiteley early years|date=1990}}</ref>

== Selected works ==
{| class="wikitable"
|-
! Year !! Title
|-
| 1976 || ''Self-Portrait in the Studio''
|-
| 1978 || ''The American Dream''
|}
"""

FIXTURE_ARTICLE = Article(
    lang="en",
    title="Brett Whiteley",
    wikitext=FIXTURE_WIKITEXT,
    sections=[
        Section(level=2, title="Early life", anchor="Early_life", index="1"),
        Section(level=2, title="Selected works", anchor="Selected_works", index="2"),
    ],
    langlinks=[],
    revision_id=999999999,
)


def main() -> None:
    work_dir = Path(__file__).parent / "wt-work"
    if work_dir.exists():
        import shutil
        shutil.rmtree(work_dir)

    job = prepare_agent_driven(FIXTURE_ARTICLE, target_lang="zh", work_dir=work_dir)
    print(f"Prepared {len(job.sections)} section(s)")
    print(f"Source permalink: {job.permalink}")
    print(f"Target existing: {job.target_existing_title or '(none)'}")
    print(f"\nPrompts written to: {work_dir}/prompts/")
    for section in job.sections:
        print(f"  - {section.section_id}: heading={section.heading!r}")
    print(f"\nNext: read each prompt, write translation to {work_dir}/translations/<id>.txt")
    print(f"Then: wiki-translate finalize {work_dir} --out ./output")


if __name__ == "__main__":
    main()
