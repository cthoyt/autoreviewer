"""A script for downloading and analyzing articles from the Journal of Cheminformatics."""

import datetime
import functools
import json
import urllib.error
from dataclasses import dataclass
from operator import itemgetter
from pathlib import Path
from textwrap import shorten
from typing import Iterable, NamedTuple

import click
import dateutil.parser
import ebooklib
import pandas as pd
import pystow
import requests
from bs4 import BeautifulSoup
from ebooklib import epub
from tabulate import tabulate
from tqdm import tqdm, trange
from tqdm.contrib.concurrent import process_map
from tqdm.contrib.logging import logging_redirect_tqdm

from autoreviewer.api import review
from autoreviewer.utils import MODULE, strip

HERE = Path(__file__).parent.resolve()
ANALYSIS_PATH = HERE.joinpath("analysis.tsv")

BIOMED_CENTRAL_DOI_PREFIX = "10.1186/"
BIOMED_CENTRAL_DOI_URI_PREFIX = "https://doi.org/10.1186/"


@dataclass
class JournalInfo:
    """A data structure to hold BMC journal information."""

    key: str
    epub_fmt: str
    article_list: str
    n_pages: int

    def get_epub_url(self, url_or_doi_or_luid: str) -> str:
        """Get the download link based on a LUID."""
        url_or_doi_or_luid = url_or_doi_or_luid.removeprefix(
            BIOMED_CENTRAL_DOI_URI_PREFIX
        )  # in case a DOI is passed
        url_or_doi_or_luid = url_or_doi_or_luid.removeprefix(
            BIOMED_CENTRAL_DOI_PREFIX
        )  # in case a DOI is passed
        return self.epub_fmt.format(url_or_doi_or_luid)


JCHEMINF = JournalInfo(
    key="jcheminf",
    epub_fmt="https://jcheminf.biomedcentral.com/counter/epub/10.1186/{}.epub",
    article_list="https://jcheminf.biomedcentral.com/articles?searchType=journalSearch&sort=PubDate&page=",
    n_pages=32,
)

BMC_BIOINFO = JournalInfo(
    key="bmcbioinfo",
    epub_fmt="https://bmcbioinformatics.biomedcentral.com/counter/epub/10.1186/{}.epub",
    article_list="https://bmcbioinformatics.biomedcentral.com/articles?searchType=journalSearch&sort=PubDate&page=",
    n_pages=32,
    # n_pages=255,
)

SKIP_JCHEM_INF_REPOS = {
    "shenggenglin/mddi-scl",
    "duaibeom/molfindergithubrepository",
    "awslabs/dgl-livesci",
    "kohulan/smiles-to-iupac-translator",  # password protected
}


def ensure_epub(journal_info: JournalInfo, doi: str) -> epub.EpubBook:
    """Get an ePub object from a BMC journal."""
    url = journal_info.get_epub_url(doi)
    path = MODULE.ensure(
        "epubs", journal_info.key, url=url, download_kwargs=dict(progress_bar=False)
    )
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


def _get_github_from_data_availability(book, data_availability) -> list[str]:
    text = data_availability.get_text(strip=False).strip().replace("‚Äč", "").replace("\u200b", "")
    text_cleaned = remove_non_ascii(text).removeprefix("Availability of data and materials").strip()
    rv = []
    for part in text_cleaned.split():
        part_lower = part.lower()
        if "github.com" in part_lower:
            yv = strip(part_lower.split("github.com")[1])
            rv.append("/".join(yv.split("/")[:2]).split(".")[0])
        # elif "bitbucket.org" in part_lower:
        #     count += 1
        #     yv = strip(part_lower.split("bitbucket.org")[1])
        #     yield "bitbucket", "/".join(yv.split("/")[:2])
        else:
            continue

    if not rv:
        tqdm.write(
            click.style("No GitHub found for ", fg="yellow")
            + click.style(f"{get_title(book)} ({get_year(book)})", fg="yellow", bold=True)
            + "\n"
            + text_cleaned.replace("\n", " ").replace("  ", " ")
            + "\n"
        )
    return rv


def get_github(book: epub.EpubBook) -> Iterable[str]:
    """Iterate over the GitHub references in the "Availability of data and materials" section."""
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_body_content(), "html.parser")
        data_availability = soup.find(class_="DataAvailability")
        if data_availability:
            links = _get_github_from_data_availability(book, data_availability)
        else:
            # TODO alternate implementation?
            links = []
        yield from links


def remove_non_ascii(string: str) -> str:
    """Remove all non-ASCII characters from a string."""
    return string.encode("ascii", errors="ignore").decode()


class ProcessedTuple(NamedTuple):
    """A tuple containing all info about an article + repo."""

    doi: str
    date: str
    title: str | None
    repo: str | None


def _process(
    doi: str,
    *,
    journal_info: JournalInfo,
) -> ProcessedTuple:
    with logging_redirect_tqdm():
        try:
            book = ensure_epub(journal_info, doi)
        except (epub.EpubException, urllib.error.HTTPError):
            return ProcessedTuple(doi, "", None, None)
        else:
            repos = [r for r in get_github(book) if r]  # TODO multiple checks per repo later
            return ProcessedTuple(doi, get_date(book), get_title(book), repos[0] if repos else None)


def scrape_dois(journal_info: JournalInfo) -> list[str]:
    """Scrape the list of DOIs from the BioMed Central articles page."""
    dois: set[str] = set()
    for i in trange(1, journal_info.n_pages + 1, unit="page", desc="Scraping article list"):
        res = requests.get(journal_info.article_list + str(i))
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


def get_joss_tuples(refresh: bool = False):
    """Yield JOSS tuples."""

    def _gt(j):
        name = j["title"]
        repo = j["software_repository"]
        doi = j["doi"]
        year = j["year"]
        return name, repo, doi, year

    module = pystow.module("joss", "papers")

    if refresh:
        for i in trange(1, 8000):
            url = f"https://joss.theoj.org/papers/10.21105/joss.{i:05}.json"
            with logging_redirect_tqdm():
                try:
                    j = module.ensure_json(url=url)
                except Exception:
                    continue
                if "Python" not in j["languages"]:
                    continue
                yield _gt(j)

    else:
        for path in tqdm(list(module.base.glob("*.json")), desc="JOSS", unit_scale=True):
            try:
                data = json.loads(path.read_text())
            except json.decoder.JSONDecodeError:
                continue
            try:
                yv = _gt(data)
            except Exception:
                continue
            if "Python" not in data["languages"]:
                continue
            yield yv


@click.command()
@click.option("--reindex", is_flag=True, help="If true, reindex papers")
def main(reindex: bool) -> None:
    """Run the analysis."""
    rows = []

    for title, repo, doi, year in get_joss_tuples():
        row = {"doi": doi, "date": year, "title": title, "journal": "joss"}
        if "github.com" not in repo:
            tqdm.write(f"[joss] unhandled non-github repo: {repo}")
            continue
        repo = (
            repo.removeprefix("https://github.com/")
            .removeprefix("http://github.com/")
            .removesuffix(".git")
            .rstrip("/")
        )
        owner, _, name = repo.partition("/")
        if not name:
            tqdm.write(f"[joss] malformed repo: {repo}")
            continue
        try:
            results = review(owner, name)
        except Exception:
            tqdm.write(f"[joss] failed to review repo: {repo}")
            rows.append(row)
            continue

        row.update(results.get_dict())
        rows.append(row)

    with logging_redirect_tqdm():
        for journal_info in [JCHEMINF, BMC_BIOINFO]:
            doi_to_github_path = HERE.joinpath(f"{journal_info.key}_doi_to_github.tsv")
            if doi_to_github_path.is_file() and not reindex:
                df = pd.read_csv(doi_to_github_path, sep="\t")
            else:
                dois = scrape_dois(journal_info)
                rv1: Iterable[ProcessedTuple] = process_map(
                    functools.partial(_process, journal_info=journal_info),
                    dois,
                    desc="processing ePubs",
                    unit="article",
                    chunksize=20,
                )
                # sort by date
                rv: list[ProcessedTuple] = sorted(set(rv1), key=itemgetter(1), reverse=True)

                columns = ["doi", "date", "title", "github"]
                df = pd.DataFrame(rv, columns=columns).drop_duplicates()
                click.echo(f"Writing to {doi_to_github_path}")
                df.to_csv(doi_to_github_path, sep="\t", index=False)
                click.echo(
                    tabulate(
                        [
                            (
                                doi.removeprefix(BIOMED_CENTRAL_DOI_PREFIX),
                                date,
                                shorten(title, 60) if title else None,
                                shorten(github, 60),
                            )
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

            for doi, date, title, repo in tqdm(
                df.values, desc="Loading cached", unit="repo", unit_scale=True
            ):
                row = {
                    "doi": doi,
                    "date": date,
                    "title": title,
                    "journal": journal_info.key,
                }
                if pd.isna(repo):
                    rows.append(row)
                    continue

                if "." in repo:  # ends with .git
                    repo = repo.split(".")[0]

                if repo in SKIP_JCHEM_INF_REPOS:
                    # so broken we have to skip
                    rows.append({"doi": doi, "date": date, "title": title})
                    continue

                owner, _, name = repo.partition("/")
                if not name:
                    tqdm.write(f"[{journal_info.key}] repo name malformed: {repo}")
                    rows.append(row)
                    continue

                try:
                    results = review(owner, name)
                except Exception:
                    tqdm.write(f"[{journal_info.key}] failed to review: {repo}")
                    rows.append(row)
                    continue

                row.update(results.get_dict())
                rows.append(row)

    df_full = pd.DataFrame(rows)
    del df_full["ruff_check_errors"]
    click.echo(f"Writing to {ANALYSIS_PATH}")
    df_full.to_csv(ANALYSIS_PATH, sep="\t", index=False)


if __name__ == "__main__":
    main()
