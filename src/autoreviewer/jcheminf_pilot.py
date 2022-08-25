"""A script for downloading and analyzing articles from the Journal of Cheminformatics."""

import hashlib
import json
import urllib.error
from operator import itemgetter
from textwrap import shorten
from typing import Iterable, Optional

import click
import dateutil.parser
import ebooklib
import pandas as pd
import pystow
import requests
from bs4 import BeautifulSoup
from ebooklib import epub
from ratelimit import rate_limited
from tabulate import tabulate
from tqdm import tqdm
from tqdm.contrib.concurrent import process_map

URL = "https://jcheminf.biomedcentral.com/track/epub/10.1186"
MODULE = pystow.module("jcheminf")
PREFIX = "https://doi.org/10.1186/"

#: Wikidata SPARQL endpoint. See https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service#Interfacing
WIKIDATA_ENDPOINT = "https://query.wikidata.org/bigdata/namespace/wdq/sparql"

# Load the GitHub access token via PyStow. We'll
# need it so we don't hit the rate limit
TOKEN = pystow.get_config("github", "token", raise_on_missing=True)


def get_dois_wikidata(force: bool = True) -> set[str]:
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


def get_dois_egon(
    user: str = "egonw",  # alternative use jcheminform
    repo: str = "jcheminform-kb",
    branch: str = "main",
    force: bool = False,
) -> set[str]:
    path = MODULE.join(name="egon_dois.txt")
    if path.is_file() and not force:
        return {line.strip() for line in path.read_text().splitlines()}

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
                dois.add(remove_non_ascii(entity).removeprefix(PREFIX).strip())

    path.write_text("\n".join(sorted(dois)))
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
            return strip(remove_non_ascii(title_div.text))
    raise ValueError


def get_date(book: epub.EpubBook) -> str:
    """Get the title of the article."""
    for element in find_class(book, "HistoryDate"):
        return dateutil.parser.parse(remove_non_ascii(element.text)).strftime("%Y-%m-%d")
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
                yield "/".join(yv.split("/")[:2]).split(".")[0]
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
        return doi, "", None, None
    else:
        repos = [r for r in get_github(book) if r]  # TODO multiple checks per repo later
        return doi, get_date(book), get_title(book), repos[0] if repos else None


@rate_limited(calls=5_000, period=60 * 60)
def github_api(url: str, accept: Optional[str] = None, params: Optional[dict[str, any]] = None):
    headers = {
        "Authorization": f"token {TOKEN}",
    }
    if accept:
        headers["Accept"] = accept
    return requests.get(url, headers=headers, params=params).json()


def _main():
    output_path = MODULE.join(name="results.tsv")
    if output_path.is_file():
        df = pd.read_csv(output_path, sep="\t")
    else:
        dois = sorted(get_dois_egon().union(get_dois_wikidata()))
        rv = process_map(_process, dois, desc="processing ePubs", unit="article")
        rv = sorted(set(rv), key=itemgetter(1), reverse=True)  # sort by date

        columns = ["doi", "date", "title", "github"]
        df = pd.DataFrame(rv, columns=columns).drop_duplicates()
        df.to_csv(output_path, sep="\t", index=False)
        print(
            tabulate(
                [
                    (doi, date, shorten(title, 80), github)
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
        print(
            f"Retrieved ePubs for {has_epub}/{length} ({has_epub / length:.2%}) "
            f"and GitHub repos for {has_github}/{length} ({has_github / length:.2%})"
        )

    enriched_path = MODULE.join(name="results_enriched.tsv")

    df = df[df["github"].notna()]
    repo_index = {}
    new_rows = {}
    for repo in tqdm(df["github"].unique(), desc="Getting repository metadata", unit="repo"):
        if "." in repo:
            repo = repo.split(".")[0]
        md5 = hashlib.md5()
        md5.update(repo.encode("utf-8"))
        path = MODULE.join("github-info", name=f"{md5.hexdigest()[:8]}.json")
        if path.is_file():
            info = repo_index[repo] = json.loads(path.read_text())
        else:
            res = github_api(f"https://api.github.com/repos/{repo}")
            if res.get("message") == "Not Found":
                info = repo_index[repo] = None
            else:
                info = repo_index[repo] = res
            path.write_text(json.dumps(repo_index[repo], indent=2))

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

        base_url = f"https://raw.githubusercontent.com/{repo}/main"
        has_setup_config = any(
            requests.get(f"{base_url}/{n}").status_code == 200
            for n in ["setup.cfg", "setup.py", "pyproject.toml"]
        )

        readme_url = f"{base_url}/README.md"
        res = requests.get(readme_url)
        has_readme = res.status_code == 200

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
    df_slim.to_csv(enriched_path, sep="\t", index=False)


if __name__ == "__main__":
    _main()
