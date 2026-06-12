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

from .fetcher import fetch_article_from_url
from .formatter import write_output
from .translator import (
    PreparedJob,
    collect_translations,
    prepare_agent_driven,
    translate_standalone,
)


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
def prepare(url: str, target: str, work_dir: Path) -> None:
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

    paths = write_output(job, translations, out_dir)
    click.echo(f"Draft wikitext: {paths['wikitext']}")
    click.echo(f"Edit summary:   {paths['edit_summary']}")
    click.echo(f"Talk template:  {paths['talk_template']}")
    click.echo(f"Review notes:   {paths['review_notes']}")
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
    paths = write_output(job, translations, out_dir)
    click.echo(f"Draft wikitext: {paths['wikitext']}")
    click.echo(f"Edit summary:   {paths['edit_summary']}")
    click.echo(f"Talk template:  {paths['talk_template']}")
    click.echo(f"Review notes:   {paths['review_notes']}")
    click.echo(DRAFT_REMINDER, err=False)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
