"""A script for downloading and analyzing articles from the Journal of Cheminformatics."""

import functools
from pathlib import Path
from typing import Callable, Iterable

import click
import pandas as pd
from pydantic import BaseModel
from tqdm import tqdm

from autoreviewer.api import Results, review
from autoreviewer.jcheminf.sources.biomed_central import (
    BIOMED_CENTRAL_JOURNALS,
    get_biomed_central_links,
)
from autoreviewer.jcheminf.sources.jmlr import get_jmlr_mloss_repos, get_jmlr_repos
from autoreviewer.jcheminf.sources.joss import get_joss_repos
from autoreviewer.jcheminf.sources.utils import SKIP_REPOSITORIES, ArticleRepositoryLink
from autoreviewer.utils import MODULE, GitHubRepository

HERE = Path(__file__).parent.resolve()
ANALYSIS_PATH = HERE.joinpath("analysis.tsv")

REVIEW_MODULE = MODULE.module("reviews")


def _get_review_path(github_repository: GitHubRepository) -> Path:
    return REVIEW_MODULE.join(github_repository.owner, name=f"{github_repository.repo}.json")


class ResultPack(BaseModel):
    journal: str
    link: ArticleRepositoryLink
    results: Results | None = None


@click.command()
@click.option("--reindex", is_flag=True, help="If true, reindex papers")
def main(reindex: bool) -> None:
    """Run the analysis."""
    rows: list[ResultPack] = []

    link_getters: list[tuple[str, Callable[[], Iterable[ArticleRepositoryLink]]]] = [
        ("jmlr", get_jmlr_repos),
        ("mloss", get_jmlr_mloss_repos),
        ("joss", get_joss_repos),
    ]
    for journal_info in BIOMED_CENTRAL_JOURNALS:
        link_getters.append(
            (
                journal_info.key,
                functools.partial(get_biomed_central_links, journal_info=journal_info),
            )
        )

    for journal, func in link_getters:
        for link in tqdm(func(), desc=f"Reviewing {journal}", unit_scale=True):
            github_repository = link.get_github_repository()
            if not github_repository:
                tqdm.write(f"[{journal}] malformed repo: {link.github}")
                continue
            elif github_repository in SKIP_REPOSITORIES:
                tqdm.write(f"[{journal}] skipping blocklisted repo: {link.github}")
                continue

            cache_path = _get_review_path(github_repository)
            if cache_path.is_file():
                results = Results.model_validate_json(cache_path.read_text())
            else:
                try:
                    results = review(github_repository.owner, github_repository.repo)
                except Exception:
                    tqdm.write(f"[{journal}] failed to review repo: {link.github}")
                    results = None
                else:
                    cache_path.write_text(results.model_dump_json(indent=2))

            row = ResultPack(
                journal=journal,
                link=link,
                results=results,
            )
            rows.append(row)

    df_full = pd.DataFrame(rows)
    del df_full["ruff_check_errors"]
    click.echo(f"Writing to {ANALYSIS_PATH}")
    df_full.to_csv(ANALYSIS_PATH, sep="\t", index=False)


if __name__ == "__main__":
    main()
