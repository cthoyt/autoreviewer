"""A script for downloading and analyzing articles from the Journal of Cheminformatics."""

import datetime
import urllib.error
from operator import itemgetter
from pathlib import Path
from textwrap import shorten
from typing import Iterable

import click
import dateutil.parser
import ebooklib
import pandas as pd
import requests
from bs4 import BeautifulSoup
from ebooklib import epub
from tabulate import tabulate
from tqdm.auto import tqdm, trange
from tqdm.contrib.concurrent import process_map
from tqdm.contrib.logging import logging_redirect_tqdm

from autoreviewer.api import review
from autoreviewer.utils import MODULE, strip

HERE = Path(__file__).parent.resolve()
DOI_TO_GITHUB_PATH = HERE.joinpath("doi_to_github.tsv")
ANALYSIS_PATH = HERE.joinpath("analysis.tsv")

DOI_PREFIX = "10.1186/"
JCHEMINF_DOI_PREFIX = "https://doi.org/10.1186/"


def get_epub_url(luid: str) -> str:
    """Get the download link based on a LUID."""
    luid = luid.removeprefix(DOI_PREFIX)  # in case a DOI is passed
    return f"https://jcheminf.biomedcentral.com/counter/epub/10.1186/{luid}.epub"


def get_jcheminf_epub(doi: str) -> epub.EpubBook:
    """Get an ePub object from Journal of Cheminformatics."""
    luid = doi.removeprefix(DOI_PREFIX)
    url = get_epub_url(luid)
    path = MODULE.ensure("epubs", url=url, download_kwargs=dict(progress_bar=False))
    return epub.read_epub(path, options=dict(ignore_ncx=True))


def get_title(book: epub.EpubBook) -> str:
    """Get the title of the article."""
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_body_content(), "html.parser")
        title_div = soup.find(**{"class": "ArticleTitle"})
        if title_div:
            return strip(remove_non_ascii(title_div.text))
    raise ValueError


def _get_date(book: epub.EpubBook) -> datetime.date | None:
    """Get the title of the article."""
    for element in find_class(book, "HistoryDate"):
        return dateutil.parser.parse(remove_non_ascii(element.text))
    return None


def get_date(book: epub.EpubBook) -> str:
    """Get the date of the article in YYYY-MM-DD."""
    d = _get_date(book)
    if d:
        return d.strftime("%Y-%m-%d")
    return ""


def get_year(book: epub.EpubBook) -> str:
    """Get the year of the article."""
    d = _get_date(book)
    if d:
        return d.strftime("%Y")
    return ""


def find_class(book: epub.EpubBook, name: str):
    """Get the title of the article."""
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_body_content(), "html.parser")
        if element := soup.find(**{"class": name}):
            yield element


def get_github(book: epub.EpubBook) -> Iterable[str]:
    """Iterate over the GitHub references in the "Availability of data and materials" section."""
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_body_content(), "html.parser")
        data_availability = soup.find(**{"class": "DataAvailability"})
        if not data_availability:
            continue

        text = (
            data_availability.get_text(strip=False).strip().replace("‚Äč", "").replace("\u200b", "")
        )
        text_cleaned = (
            remove_non_ascii(text).removeprefix("Availability of data and materials").strip()
        )
        count = 0
        for part in text_cleaned.split():
            part_lower = part.lower()
            if "github.com" in part_lower:
                count += 1
                yv = strip(part_lower.split("github.com")[1])
                yield "/".join(yv.split("/")[:2]).split(".")[0]
            # elif "bitbucket.org" in part_lower:
            #     count += 1
            #     yv = strip(part_lower.split("bitbucket.org")[1])
            #     yield "bitbucket", "/".join(yv.split("/")[:2])
            else:
                continue
        if not count:
            tqdm.write(
                click.style("No GitHub found for ", fg="yellow")
                + click.style(f"{get_title(book)} ({get_year(book)})", fg="yellow", bold=True)
                + "\n"
                + text_cleaned.replace("\n", " ").replace("  ", " ")
                + "\n"
            )


def remove_non_ascii(string: str) -> str:
    """Remove all non-ASCII characters from a string."""
    return string.encode("ascii", errors="ignore").decode()


def _process(doi: str) -> tuple[str, str, str | None, str | None]:
    with logging_redirect_tqdm():
        try:
            book = get_jcheminf_epub(doi)
        except (epub.EpubException, urllib.error.HTTPError):
            return doi, "", None, None
        else:
            repos = [r for r in get_github(book) if r]  # TODO multiple checks per repo later
            return doi, get_date(book), get_title(book), repos[0] if repos else None


def scrape_dois(top: int = 28) -> list[str]:
    """Scrape the list of DOIs from the Journal of Cheminformatics' articles page."""
    url = "https://jcheminf.biomedcentral.com/articles?searchType=journalSearch&sort=PubDate&page="
    dois: set[str] = set()
    for i in trange(1, top + 1, unit="page", desc="Scraping JChemInf site"):
        res = requests.get(url + str(i))
        soup = BeautifulSoup(res.text, "html.parser")
        for element in soup.find_all(**{"class": "c-listing__item"}):
            a = element.find(**{"data-test": "title-link"})
            if a is None:
                continue
            title = a.get_text()

            article_type = element.find(**{"data-test": "result-list"})
            article_type_text = article_type.get_text()
            if article_type_text in {"Editorial", "Review"}:
                tqdm.write(f"Skipping {article_type_text}: {title}")
                continue

            doi = a.attrs["href"].removeprefix("/articles/")
            dois.add(doi)
    return sorted(dois)


SKIP_REPOS = {
    "shenggenglin/mddi-scl",
    "duaibeom/molfindergithubrepository",
    "awslabs/dgl-livesci",
}


@click.command()
@click.option("--reindex", is_flag=True, help="If true, reindex papers")
def main(reindex: bool) -> None:
    """Run the analysis."""
    if DOI_TO_GITHUB_PATH.is_file() and not reindex:
        df = pd.read_csv(DOI_TO_GITHUB_PATH, sep="\t")
    else:
        with logging_redirect_tqdm():
            dois = scrape_dois()
        rv = process_map(_process, dois, desc="processing ePubs", unit="article", chunksize=20)
        rv = sorted(set(rv), key=itemgetter(1), reverse=True)  # sort by date

        columns = ["doi", "date", "title", "github"]
        df = pd.DataFrame(rv, columns=columns).drop_duplicates()
        click.echo(f"Writing to {DOI_TO_GITHUB_PATH}")
        df.to_csv(DOI_TO_GITHUB_PATH, sep="\t", index=False)
        click.echo(
            tabulate(
                [
                    (doi.removeprefix("10.1186/"), date, shorten(title, 60), shorten(github, 60))
                    for doi, date, title, github in rv
                    if github
                ],
                headers=columns,
                tablefmt="github",
            )
        )
        length = len(rv)
        has_epub = sum(bool(row[1]) for row in rv)
        has_github = sum(bool(row[3]) for row in rv)
        click.echo(
            f"Retrieved ePubs for {has_epub:,}/{length:,} ({has_epub / length:.1%}) "
            f"and GitHub repos for {has_github:,}/{length:,} ({has_github / length:.1%})"
        )

    rows = []
    for doi, date, title, repo in tqdm(df.values, desc="Loading cached", unit="repo"):
        row = {"doi": doi, "date": date, "title": title}
        if pd.isna(repo):
            rows.append(row)
            continue

        if "." in repo:  # ends with .git
            repo = repo.split(".")[0]

        if repo in SKIP_REPOS:
            # so broken we have to skip
            rows.append({"doi": doi, "date": date, "title": title})
            continue
        try:
            owner, name = repo.split("/")
        except ValueError:
            tqdm.write(f"Failed: {repo}")
            rows.append(row)
            continue
        try:
            results = review(owner, name)
        except Exception:
            tqdm.write(f"Failed: {repo}")
            rows.append(row)
            continue

        row.update(results.get_dict())
        rows.append(row)

    df_full = pd.DataFrame(rows)
    click.echo(f"Writing to {ANALYSIS_PATH}")
    df_full.to_csv(ANALYSIS_PATH, sep="\t", index=False)


if __name__ == "__main__":
    main()
