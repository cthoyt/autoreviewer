"""A script for downloading and analyzing articles from the Journal of Cheminformatics."""

import functools
import gzip
from pathlib import Path
from typing import Callable, Iterable

import click
from tqdm import tqdm

from autoreviewer.api import Results, review
from autoreviewer.comparison.sources.biomed_central import (
    BIOMED_CENTRAL_JOURNALS,
    get_biomed_central_links,
)
from autoreviewer.comparison.sources.jmlr import get_jmlr_mloss_repos, get_jmlr_repos
from autoreviewer.comparison.sources.joss import get_joss_repos
from autoreviewer.comparison.sources.openrv import OPENREVIEW_VENUES, get_openreview_links
from autoreviewer.comparison.sources.utils import (
    SKIP_REPOSITORIES,
    ArticleRepositoryLink,
    ResultPack,
)
from autoreviewer.utils import MODULE, GitHubRepository

HERE = Path(__file__).parent.resolve()
ANALYSIS_PATH = HERE.joinpath("analysis.jsonl.gz")

REVIEW_MODULE = MODULE.module("reviews")


def _get_review_path(github_repository: GitHubRepository) -> Path:
    return REVIEW_MODULE.join(github_repository.owner, name=f"{github_repository.repo}.json")


@click.command()
def main() -> None:
    """Run the analysis.

    Still to do:

    1. How to identify the correct GitHub repository from a list of many?
       This hugely overinflates statistics for JMLR
    2. How to filter out non-Python repositories from the analysis?
    """
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
    for journal_key in OPENREVIEW_VENUES:
        link_getters.append(
            (
                journal_key,
                functools.partial(get_openreview_links, journal_key=journal_key),
            )
        )

    for journal, func in link_getters:
        for link in tqdm(func(), desc=f"Reviewing {journal}", unit_scale=True):
            if not link.github:
                results = None
            elif not (github_repository := link.get_github_repository()):
                tqdm.write(f"[{journal}] malformed repo: {link.github}")
                results = None
            elif github_repository in SKIP_REPOSITORIES:
                tqdm.write(f"[{journal}] skipping blocklisted repo: {link.github}")
                continue
            else:
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

    with gzip.open(ANALYSIS_PATH, "wt") as file:
        for row in rows:
            file.write(row.model_dump_json(exclude={"results.ruff_check_errors"}) + "\n")

    from .summarize import summarize

    summarize(rows)


if __name__ == "__main__":
    main()
