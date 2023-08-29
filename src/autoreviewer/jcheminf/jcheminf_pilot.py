"""A script for downloading and analyzing articles from the Journal of Cheminformatics."""

import datetime
import hashlib
import json
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

from autoreviewer.utils import (
    MODULE,
    WIKIDATA_ENDPOINT,
    get_readme,
    get_repo_metadata,
    get_setup_config,
    strip,
)

HERE = Path(__file__).parent.resolve()
DOI_TO_GITHUB_PATH = HERE.joinpath("doi_to_github.tsv")
ANALYSIS_PATH = HERE.joinpath("analysis.tsv")

#: Add the DOI at the end of this URL to get an ePub file
EPUB_BASE_URL = "https://jcheminf.biomedcentral.com/track/epub/10.1186"
JCHEMINF_DOI_PREFIX = "https://doi.org/10.1186/"


def _get_dois_wikidata(force: bool = True) -> set[str]:
    # NOTE: this is easily replaced with web scraping
    path = MODULE.join(name="wikidata_dois.txt")
    if path.is_file() and not force:
        return {line.strip().lower() for line in path.read_text().splitlines()}
    sparql = "SELECT ?doi WHERE { wd:Q6294930 ^wdt:P1433 / wdt:P356 ?doi . }"
    response = requests.get(WIKIDATA_ENDPOINT, params={"query": sparql, "format": "json"})
    res_json = response.json()
    dois = {
        remove_non_ascii(record["doi"]["value"]).removeprefix("10.1186/").strip().lower()
        for record in res_json["results"]["bindings"]
    }
    path.write_text("\n".join(sorted(dois)))
    return dois


def _get_dois_egon(
    user: str = "egonw",  # alternative use jcheminform
    repo: str = "jcheminform-kb",
    branch: str = "main",
    force: bool = False,
) -> set[str]:
    # NOTE: this is easily replaced with web scraping
    path = MODULE.join(name="egon_dois.txt")
    if path.is_file() and not force:
        return set(path.read_text().splitlines())

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
            if entity.startswith(JCHEMINF_DOI_PREFIX):
                dois.add(remove_non_ascii(entity).removeprefix(JCHEMINF_DOI_PREFIX).strip())

    path.write_text("\n".join(sorted(dois)))
    return dois


def get_jcheminf_epub(doi: str) -> epub.EpubBook:
    """Get an ePub object from Journal of Cheminformatics."""
    doi = doi.removeprefix("10.1186/")
    path = MODULE.ensure("epubs", url=f"{EPUB_BASE_URL}/{doi}", name=f"{doi}.epub")
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


def _process(doi: str):
    try:
        book = get_jcheminf_epub(doi)
    except (epub.EpubException, urllib.error.HTTPError):
        return doi, "", None, None
    else:
        repos = [r for r in get_github(book) if r]  # TODO multiple checks per repo later
        return doi, get_date(book), get_title(book), repos[0] if repos else None


def scrape_dois(top: int = 27) -> set[str]:
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
            if article_type.get_text() == "Editorial":
                tqdm.write(f"Skipping editorial: {title}")
                continue

            doi = a.attrs["href"].removeprefix("/articles/")
            dois.add(doi)
    return dois


@click.command()
def main():
    """Run the analysis."""
    if DOI_TO_GITHUB_PATH.is_file():
        df = pd.read_csv(DOI_TO_GITHUB_PATH, sep="\t")
    else:
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

    df = df[df["github"].notna()]
    repo_index = {}
    queue = []
    for repo in tqdm(df["github"].unique(), desc="Loading cached", unit="repo"):
        if "." in repo:
            repo = repo.split(".")[0]
        md5 = hashlib.md5()
        md5.update(repo.encode("utf-8"))
        path = MODULE.join("github-info", name=f"{md5.hexdigest()[:8]}.json")
        if path.is_file():
            data = json.loads(path.read_text())
            if data is not None:
                repo_index[repo] = data
        else:
            queue.append((path, repo))

    for path, repo in tqdm(queue, desc="Get repo metadata"):
        res = get_repo_metadata(repo)
        if res.status_code != 200:
            tqdm.write(f"Bad status for {repo}: {res.text}")
            continue
        res_json = res.json()
        if res_json.get("message") == "Not Found":
            continue
        repo_index[repo] = res_json
        path.write_text(json.dumps(res_json, indent=2))

    new_rows = {}
    for repo, info in tqdm(repo_index.items(), desc="Process repo metadata"):
        if info is None:
            continue
        try:
            is_fork = info["fork"]
        except KeyError:
            tqdm.write(f"could not get fork info for {repo}: {info}")
            continue
        has_issues = info["has_issues"]
        language = info["language"]
        repo_license = (info.get("license") or {}).get("spdx_id")
        if repo_license == "NOASSERTION":
            repo_license = "Other"

        has_setup_config = get_setup_config(repo) is not None
        has_readme = get_readme(repo, branch="main") is not None

        new_rows[repo] = (
            is_fork,
            has_issues,
            language,
            repo_license,
            has_readme,
            has_setup_config,
        )

    columns = [
        "is_fork",
        "has_issues",
        "language",
        "license",
        "has_readme",
        "is_packaged",
    ]
    df_slim_rows = [
        (doi, date, title, github, *new_rows.get(github, [None] * len(columns)))
        for doi, date, title, github in df[
            df["github"].map(lambda key: repo_index.get(key) is not None, na_action="ignore")
        ].values
    ]
    df_slim = pd.DataFrame(
        df_slim_rows,
        columns=[*df.columns, *columns],
    )
    click.echo(f"Writing to {ANALYSIS_PATH}")
    df_slim.to_csv(ANALYSIS_PATH, sep="\t", index=False)


if __name__ == "__main__":
    main()
