"""A script for downloading and analyzing articles from the Journal of Cheminformatics."""

import urllib.error
from operator import itemgetter
from textwrap import shorten
from typing import Iterable

import click
import ebooklib
import pystow
from functools import partial
import requests
import dateutil.parser
from bs4 import BeautifulSoup
from ebooklib import epub
from tabulate import tabulate
from tqdm import tqdm
from tqdm.contrib.concurrent import process_map
import pandas as pd

URL = "https://jcheminf.biomedcentral.com/track/epub/10.1186"
MODULE = pystow.module("jcheminf")
PREFIX = "https://doi.org/10.1186/"

#: Wikidata SPARQL endpoint. See https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service#Interfacing
WIKIDATA_ENDPOINT = "https://query.wikidata.org/bigdata/namespace/wdq/sparql"


def get_dois_wikidata(force: bool = False) -> list[str]:
    path = MODULE.join(name="wikidata_dois.txt")
    if path.is_file() and not force:
        return list(path.read_text().splitlines())
    sparql = "SELECT ?doi WHERE { wd:Q6294930 ^wdt:P1433 / wdt:P356 ?doi . }"
    response = requests.get(WIKIDATA_ENDPOINT, params={"query": sparql, "format": "json"})
    res_json = response.json()
    dois = sorted(
        {
            record["doi"]["value"].removeprefix("10.1186/")
            for record in res_json["results"]["bindings"]
        }
    )
    path.write_text("\n".join(dois))
    return dois


def get_dois_egon(
    user: str = "egonw",  # alternative use jcheminform
    repo: str = "jcheminform-kb",
    branch: str = "main",
    force: bool = False,
) -> list[str]:
    path = MODULE.join(name="egon_dois.txt")
    if path.is_file() and not force:
        return list(path.read_text().splitlines())

    response = requests.get(
        f"https://api.github.com/repos/{user}/{repo}/git/trees/{branch}?recursive=1"
    )
    response.raise_for_status()

    dois = set()
    for element in tqdm(
        response.json()["tree"], desc="Downloading article metadata", unit="article"
    ):
        if not element["path"].endswith(".ttl"):
            continue
        graph = MODULE.ensure_rdf(
            "egon-rdf",
            url=f'https://raw.githubusercontent.com/{user}/{repo}/{branch}/{element["path"]}',
            parse_kwargs={"format": "turtle"},
        )
        for entity in graph.subjects():
            if entity.startswith(PREFIX):
                dois.add(entity.removeprefix(PREFIX))

    dois = sorted(dois)
    path.write_text("\n".join(dois))
    return dois


def get_jcheminf_epub(doi: str) -> epub.EpubBook:
    """Get an ePub object from Journal of Cheminformatics"""
    path = MODULE.ensure("epubs", url=f"{URL}/{doi}", name=f"{doi}.epub")
    return epub.read_epub(path)


def get_title(book: epub.EpubBook) -> str:
    """Get the title of the article."""
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_body_content(), "html.parser")
        title_div = soup.find(**{"class": "ArticleTitle"})
        if title_div:
            return title_div.text
    raise ValueError


def get_date(book: epub.EpubBook) -> str:
    """Get the title of the article."""
    for element in find_class(book, "HistoryDate"):
        return dateutil.parser.parse(element.text).strftime("%Y-%m-%d")
    return ""


def find_class(book: epub.EpubBook, name):
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
                yield "/".join(yv.split("/")[:2])
            # elif "bitbucket.org" in part_lower:
            #     count += 1
            #     yv = strip(part_lower.split("bitbucket.org")[1])
            #     yield "bitbucket", "/".join(yv.split("/")[:2])
            else:
                continue
        if not count:
            tqdm.write(
                click.style(f"No GitHub found for ", fg="yellow")
                + click.style(get_title(book), fg="yellow", bold=True, italic=True)
                + "\n"
                + text_cleaned.replace("\n", " ").replace("  ", " ")
                + "\n"
            )


def remove_non_ascii(string: str) -> str:
    return string.encode("ascii", errors="ignore").decode()


def strip(s: str) -> str:
    for t in ".,\\/()[]{}_":
        s = s.strip(t)
    return s


def _process(doi: str):
    try:
        book = get_jcheminf_epub(doi)
    except (epub.EpubException, urllib.error.HTTPError):
        return doi, None, None, None
    else:
        github = ", ".join(sorted({x for x in get_github(book) if x}))
        return doi, get_date(book), shorten(get_title(book), 80), github


def _main():
    _map = partial(process_map, chunksize=100, desc="processing ePubs", unit="article")
    # _map = map
    rv = _map(_process, get_dois_wikidata())
    rv = sorted(rv, key=itemgetter(1), reverse=True)  # sort by date

    output_path = MODULE.join(name="results.tsv")
    columns = ["doi", "date", "title", "github"]
    pd.DataFrame(rv, columns=columns).to_csv(output_path, sep="\t", index=False)
    print(tabulate([row for row in rv if row[3]], headers=columns, tablefmt="github"))

    length = len(rv)
    has_epub = sum(bool(row[1]) for row in rv)
    has_github = sum(bool(row[3]) for row in rv)
    print(
        f"Retrieved ePubs for {has_epub}/{length} ({has_epub / length:.2%}) "
        f"and GitHub repos for {has_github}/{length} ({has_github / length:.2%})"
    )


if __name__ == "__main__":
    _main()
