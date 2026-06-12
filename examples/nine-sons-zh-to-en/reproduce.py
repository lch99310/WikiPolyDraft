"""Reproduce the ZH -> EN translation of 九子奪嫡 without network access.

In the real world the English Wikipedia does NOT have an article for 九子奪嫡
(the Nine Lords' War over the succession in the early Qing dynasty), which is
exactly the kind of asymmetry this tool tries to help with. langlinks for the
synthetic article therefore omit `en`, and no coverage report is generated.

Run from the repo root:
    python examples/nine-sons-zh-to-en/reproduce.py
    # then translate each prompt in examples/nine-sons-zh-to-en/wt-work/prompts/
    # then: wiki-translate finalize examples/nine-sons-zh-to-en/wt-work --out ./output
"""

from pathlib import Path

from wiki_translate.fetcher import Article, Section
from wiki_translate.translator import prepare_agent_driven

FIXTURE_WIKITEXT = """'''九子奪嫡''',指[[清朝]][[康熙帝]]晚年九位皇子爭奪[[皇位]]繼承權的政治鬥爭事件。<ref>{{cite book|title=清史稿|author=趙爾巽|year=1928}}</ref> 此事件最終以[[雍正帝|皇四子胤禛]]繼位告終。<ref name="qingshi" />

== 背景 ==
[[康熙帝]]在位六十一年,初立次子[[胤礽]]為[[太子]],但因[[太子党]]势力膨脹及胤礽個人品行問題,康熙四十七年(1708年)一度廢黜太子。<ref>{{cite book|title=康熙朝實錄|year=1731}}</ref>

== 主要參與者 ==
{| class="wikitable"
|-
! 排行 !! 姓名 !! 派系
|-
| 長子 || [[胤禔]] || 大阿哥黨
|-
| 次子 || [[胤礽]] || 太子黨
|-
| 四子 || [[胤禛]] || 四爺黨(後繼位為[[雍正帝]])
|-
| 八子 || [[胤禩]] || 八爺黨
|-
| 十四子 || [[胤禵]] || 八爺黨(後期)
|}

== 結局 ==
康熙六十一年(1722年)十一月,康熙帝駕崩,[[胤禛]]繼位,是為[[雍正帝]]。<ref name="qingshi">{{cite journal|title=雍正繼位之謎研究|year=2010}}</ref> 其後雍正帝陸續清算諸兄弟,將[[胤禩]]、[[胤禟]]改名為「阿其那」、「塞思黑」並囚禁致死。
"""

FIXTURE_ARTICLE = Article(
    lang="zh",
    title="九子奪嫡",
    wikitext=FIXTURE_WIKITEXT,
    sections=[
        Section(level=2, title="背景", anchor="背景", index="1"),
        Section(level=2, title="主要參與者", anchor="主要參與者", index="2"),
        Section(level=2, title="結局", anchor="結局", index="3"),
    ],
    langlinks=[],  # in reality, en.wikipedia has no equivalent article
    revision_id=88888888,
)


def main() -> None:
    work_dir = Path(__file__).parent / "wt-work"
    if work_dir.exists():
        import shutil
        shutil.rmtree(work_dir)

    job = prepare_agent_driven(FIXTURE_ARTICLE, target_lang="en", work_dir=work_dir)
    print(f"Prepared {len(job.sections)} section(s) from zh:{FIXTURE_ARTICLE.title}")
    print(f"Source permalink: {job.permalink}")
    print(f"Target existing: {job.target_existing_title or '(none — this is the asymmetry case)'}")
    print(f"\nPrompts written to: {work_dir}/prompts/")
    for section in job.sections:
        print(f"  - {section.section_id}: heading={section.heading!r}")
    print(f"\nNext: read each prompt, write translation to {work_dir}/translations/<id>.txt")
    print(f"Then: wiki-translate finalize {work_dir} --out ./output")


if __name__ == "__main__":
    main()
