"""A source for journals from BioMed Central."""

import datetime
import functools
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import click
import dateutil.parser
import ebooklib
import requests
from bs4 import BeautifulSoup
from curies import Reference
from ebooklib import epub
from pydantic import ValidationError
from tqdm import tqdm, trange
from tqdm.contrib.concurrent import process_map
from tqdm.contrib.logging import logging_redirect_tqdm

from autoreviewer.comparison.sources.utils import ArticleRepositoryLink
from autoreviewer.utils import MODULE, strip

HERE = Path(__file__).parent.resolve()

BMC_MODULE = MODULE.module("bmc")


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


def _process(
    doi: str,
    *,
    journal_info: JournalInfo,
) -> ArticleRepositoryLink:
    part = doi.removeprefix("10.1186/")
    cache_path = BMC_MODULE.join(name=f"{part}.json")
    if cache_path.is_file():
        return ArticleRepositoryLink.model_validate_json(cache_path.read_text())

    reference = Reference(prefix="doi", identifier=doi)
    with logging_redirect_tqdm():
        try:
            book = ensure_epub(journal_info, doi)
        except (epub.EpubException, urllib.error.HTTPError):
            rv = ArticleRepositoryLink(reference=reference, date=None, title=None, github=None)
        else:
            repos = [
                r for r in get_github(book) if r and "/" in r
            ]  # TODO multiple checks per repo later
            try:
                rv = ArticleRepositoryLink(
                    reference=reference,
                    date=get_date(book),
                    title=get_title(book),
                    github=repos[0] if repos else None,
                )
            except ValidationError:
                tqdm.write(f"[{journal_info.key}] failed to parse {doi}")
                rv = ArticleRepositoryLink(reference=reference, date=None, title=None, github=None)

    cache_path.write_text(rv.model_dump_json())
    return rv


def scrape_biomed_central_dois(journal_info: JournalInfo) -> list[str]:
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


BIOMED_CENTRAL_DOI_PREFIX = "10.1186/"
BIOMED_CENTRAL_DOI_URI_PREFIX = "https://doi.org/10.1186/"
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

BIOMED_CENTRAL_JOURNALS = [JCHEMINF, BMC_BIOINFO]


def get_biomed_central_links(journal_info: JournalInfo) -> list[ArticleRepositoryLink]:
    """Get BioMed Central article-repository links."""
    with logging_redirect_tqdm():
        dois = scrape_biomed_central_dois(journal_info)
        rv1: Iterable[ArticleRepositoryLink] = process_map(
            functools.partial(_process, journal_info=journal_info),
            dois,
            desc="processing ePubs",
            unit="article",
            chunksize=20,
        )
    rv: list[ArticleRepositoryLink] = list(set(rv1))
    return rv
