"""CLI entry point for wiki-translate.

Subcommands:
    prepare   — fetch source article, emit prompts for a host agent (Skill mode)
    finalize  — read the agent's translation outputs, write final draft + attribution
    translate — one-shot standalone translation using an LLM API (requires API key)
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

import json

from .comparator import (
    compare_sections,
    coverage_report_md,
    emit_alignment_prompt,
    read_alignment_response,
    read_target_info,
    render_coverage_md,
    write_target_info,
)
from .factcheck import UrlCheck, check_url_reachability, extract_ref_urls
from .fetcher import fetch_article, fetch_article_from_url
from .formatter import write_output
from .translator import (
    PreparedJob,
    collect_translations,
    prepare_agent_driven,
    translate_standalone,
)

_URL_CHECK_FILENAME = "url-check.json"


def _try_prepare_target_artifacts(article, target_lang: str, work_dir: Path) -> bool:
    """If the source has a langlink to target_lang, try to fetch that article,
    write a V0.2-style coverage report (no alignment yet), an alignment prompt
    for the host agent, and a target-info.json that finalize will rebuild from.

    Returns True if all of the above succeeded; False if no langlink exists,
    or if the network fetch failed (we don't want a flaky target wiki to
    block the actual translation).
    """
    target_title = article.langlink_for(target_lang)
    if not target_title:
        return False
    try:
        target_existing = fetch_article(target_lang, target_title)
    except Exception as e:
        click.echo(
            f"Note: failed to fetch existing {target_lang} article "
            f"'{target_title}' for coverage report ({e}). Continuing without it.",
            err=True,
        )
        return False
    coverage = compare_sections(article, target_existing)
    skeleton = coverage_report_md(article, target_existing, coverage, alignments=None)
    (work_dir / "coverage-report.md").write_text(skeleton, encoding="utf-8")
    emit_alignment_prompt(article, target_existing, work_dir)
    write_target_info(target_existing, work_dir)
    return True


def _run_url_check(article, work_dir: Path) -> list[UrlCheck]:
    urls = extract_ref_urls(article.wikitext)
    if not urls:
        return []
    click.echo(f"Checking reachability of {len(urls)} citation URL(s)...")
    results = check_url_reachability(urls)
    (work_dir / _URL_CHECK_FILENAME).write_text(
        json.dumps(
            [{"url": r.url, "status": r.status, "detail": r.detail} for r in results],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return results


def _load_url_check(work_dir: Path) -> list[UrlCheck]:
    path = work_dir / _URL_CHECK_FILENAME
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [UrlCheck(url=r["url"], status=r["status"], detail=r["detail"]) for r in raw]


def _heading_text_from_unit(heading_marker: str) -> str | None:
    """`== Early life ==` -> `Early life`; empty / lead -> None."""
    h = (heading_marker or "").strip()
    if not h:
        return None
    return h.strip("=").strip() or None


def _rebuild_coverage_with_alignment(job: PreparedJob, work_dir: Path) -> str | None:
    """If we have target-info.json and an alignment response, return the
    upgraded coverage report. Otherwise return the existing skeleton (if
    present) or None.
    """
    target_info = read_target_info(work_dir)
    coverage_path = work_dir / "coverage-report.md"
    existing = coverage_path.read_text(encoding="utf-8") if coverage_path.exists() else None
    if target_info is None:
        return existing
    alignments = read_alignment_response(work_dir)
    source_headings = [
        h for h in (_heading_text_from_unit(s.heading) for s in job.sections) if h
    ]
    upgraded = render_coverage_md(
        source_lang=job.source_lang,
        source_title=job.article_title,
        source_url=job.article_url,
        source_revision=job.revision_id,
        source_headings=source_headings,
        target_lang=target_info["lang"],
        target_title=target_info["title"],
        target_url=target_info["article_url"],
        target_revision=int(target_info["revision_id"]),
        target_headings=list(target_info["headings"]),
        alignments=alignments,
    )
    return upgraded


DRAFT_REMINDER = (
    "\n>>> This produced a DRAFT. Open review-notes.md before doing anything "
    "with the wikitext.\n>>> Per Wikipedia:LLM-assisted_translation, the "
    "editor publishing this must be fluent in both languages and must verify "
    "all citations and facts.\n"
)


@click.group()
@click.version_option()
def main() -> None:
    """AI-assisted Wikipedia translation — DRAFT output only."""


@main.command()
@click.argument("url")
@click.option("--target", "-t", required=True, help="Target language code, e.g. zh, en, ja.")
@click.option(
    "--out",
    "-o",
    "work_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("./wt-work"),
    show_default=True,
    help="Work directory where prompts and translations will live.",
)
@click.option(
    "--check-urls/--no-check-urls",
    default=False,
    show_default=True,
    help=(
        "Level 2 fact-check: HEAD-check every citation URL in the source "
        "article and surface dead links in review-notes.md. Off by default "
        "because it hits the network and can be slow on big articles."
    ),
)
def prepare(url: str, target: str, work_dir: Path, check_urls: bool) -> None:
    """Fetch the source article and emit prompts for the host agent."""
    article = fetch_article_from_url(url)
    if article.lang == target:
        raise click.ClickException(
            f"Source and target languages are both '{target}'. Nothing to translate."
        )
    job = prepare_agent_driven(article, target, work_dir)

    click.echo(f"Prepared {len(job.sections)} section(s) from {article.lang}:{article.title}")
    click.echo(f"Source permalink (for attribution): {job.permalink}")
    if job.target_existing_title:
        click.echo(
            f"Note: {target}.wikipedia already has '{job.target_existing_title}'. "
            "The reviewing editor will need to compare and merge manually."
        )
        if _try_prepare_target_artifacts(article, target, work_dir):
            click.echo(f"Coverage report skeleton: {work_dir}/coverage-report.md")
            click.echo(f"Alignment prompt: {work_dir}/prompts/_alignment.prompt.txt")
    if check_urls:
        results = _run_url_check(article, work_dir)
        bad = [r for r in results if r.status != "ok"]
        click.echo(
            f"URL check: {len(results)} URL(s), {len(bad)} non-OK (see "
            f"{work_dir}/url-check.json)"
        )
    click.echo(f"Prompts written to: {work_dir}/prompts/")
    click.echo("Next: host agent reads each prompt, writes translation to "
               f"{work_dir}/translations/<section_id>.txt")
    click.echo(f"Then: wiki-translate finalize {work_dir}")


@main.command()
@click.argument(
    "work_dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
@click.option(
    "--out",
    "-o",
    "out_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("./output"),
    show_default=True,
    help="Where to write the final draft and attribution files.",
)
def finalize(work_dir: Path, out_dir: Path) -> None:
    """Assemble the final draft from the agent's translation outputs."""
    job_path = work_dir / "job.json"
    if not job_path.exists():
        raise click.ClickException(
            f"No job.json in {work_dir}. Did you run `wiki-translate prepare` first?"
        )
    job = PreparedJob.from_json(job_path.read_text(encoding="utf-8"))
    try:
        translations = collect_translations(work_dir, job)
    except RuntimeError as e:
        raise click.ClickException(str(e))

    coverage_md = _rebuild_coverage_with_alignment(job, work_dir)
    url_checks = _load_url_check(work_dir)

    paths = write_output(
        job,
        translations,
        out_dir,
        coverage_md=coverage_md,
        url_checks=url_checks,
    )
    click.echo(f"Draft wikitext: {paths['wikitext']}")
    click.echo(f"Edit summary:   {paths['edit_summary']}")
    click.echo(f"Talk template:  {paths['talk_template']}")
    click.echo(f"Review notes:   {paths['review_notes']}")
    if "coverage_report" in paths:
        click.echo(f"Coverage report: {paths['coverage_report']}")
    click.echo(DRAFT_REMINDER, err=False)


@main.command()
@click.argument("url")
@click.option("--target", "-t", required=True, help="Target language code, e.g. zh, en, ja.")
@click.option(
    "--out",
    "-o",
    "out_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("./output"),
    show_default=True,
    help="Where to write the final draft and attribution files.",
)
@click.option("--model", default="claude-opus-4-7", show_default=True,
              help="Anthropic model id for standalone mode.")
def translate(url: str, target: str, out_dir: Path, model: str) -> None:
    """One-shot standalone translation (requires ANTHROPIC_API_KEY)."""
    from .llm.anthropic_client import AnthropicClient

    article = fetch_article_from_url(url)
    if article.lang == target:
        raise click.ClickException(
            f"Source and target languages are both '{target}'. Nothing to translate."
        )
    client = AnthropicClient(model=model)
    translations = translate_standalone(article, target, client)

    job = PreparedJob(
        source_lang=article.lang,
        target_lang=target,
        article_title=article.title,
        article_url=article.article_url,
        revision_id=article.revision_id,
        permalink=article.permalink,
        target_existing_title=article.langlink_for(target),
        sections=[unit for unit, _ in translations],
    )
    # Standalone mode renders an unaligned coverage report when applicable;
    # alignment is an agent-driven feature only.
    coverage_md = None
    target_title = article.langlink_for(target)
    if target_title:
        try:
            target_existing = fetch_article(target, target_title)
            coverage = compare_sections(article, target_existing)
            coverage_md = coverage_report_md(article, target_existing, coverage)
        except Exception as e:
            click.echo(f"Note: target coverage skipped ({e}).", err=True)
    paths = write_output(job, translations, out_dir, coverage_md=coverage_md)
    click.echo(f"Draft wikitext: {paths['wikitext']}")
    click.echo(f"Edit summary:   {paths['edit_summary']}")
    click.echo(f"Talk template:  {paths['talk_template']}")
    click.echo(f"Review notes:   {paths['review_notes']}")
    if "coverage_report" in paths:
        click.echo(f"Coverage report: {paths['coverage_report']}")
    click.echo(DRAFT_REMINDER, err=False)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
