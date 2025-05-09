"""Get repositories from OpenReview."""

import pystow
from curies import Reference
from openreview.api import OpenReviewClient
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from autoreviewer.comparison.sources.utils import (
    MAX_YEAR,
    MIN_YEAR,
    ArticlePDFLink,
    ArticleRepositoryLink,
    get_repos_from_pdfs,
)
from autoreviewer.utils import MODULE

__all__ = [
    "get_openreview_links",
]

OPENREVIEW_VENUES = {
    "iclr": {year: f"ICLR.cc/{year}/Conference" for year in range(MIN_YEAR, MAX_YEAR)},
    "neurips": {year: f"NeurIPS.cc/{year}/Conference" for year in range(MIN_YEAR, MAX_YEAR)},
}


def get_all_openreview_repos() -> list[ArticleRepositoryLink]:
    """Get OpenReview article-repository links."""
    rv = []
    for journal_key in OPENREVIEW_VENUES:
        rv.extend(get_openreview_links(journal_key))
    return rv


def get_openreview_links(journal_key: str) -> list[ArticleRepositoryLink]:
    """Get OpenReview article-repository links for the given journal."""
    pdfs = get_openreview_pdfs(journal_key, OPENREVIEW_VENUES[journal_key])
    return get_repos_from_pdfs(journal_key, pdfs, desc=f"Getting {journal_key}")


def get_openreview_pdfs(journal, conf: dict[int, str]) -> list[ArticlePDFLink]:
    """Fetch submission links for a given venue ID."""
    client = OpenReviewClient(
        baseurl="https://api2.openreview.net",
        username=pystow.get_config("openreview", "username", raise_on_missing=True),
        password=pystow.get_config("openreview", "password", raise_on_missing=True),
    )

    rv: list[ArticlePDFLink] = []
    for year, venue_id in tqdm(conf.items()):
        journal_year_cache_path = MODULE.join(journal, name=f"{year}.jsonl")
        if journal_year_cache_path.is_file():
            with journal_year_cache_path.open() as file:
                rv.extend(ArticlePDFLink.model_validate_json(line) for line in file)
        else:
            with logging_redirect_tqdm():
                submissions = client.get_all_notes(content={"venueid": venue_id})
            tqdm.write(f"{venue_id} has: {len(submissions):,} submissions.")
            if submissions:
                with journal_year_cache_path.open("w") as file:
                    for submission in submissions:
                        ll = ArticlePDFLink(
                            reference=Reference(prefix="openreview", identifier=submission.id),
                            title=submission.content["title"]["value"],
                            date=f"{year}-01-01",
                            pdf_url="https://openreview.net" + submission.content["pdf"]["value"],
                        )
                        file.write(ll.model_dump_json() + "\n")
                        rv.append(ll)

    return rv
