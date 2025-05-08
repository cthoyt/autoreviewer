"""A source for the Journal of Machine Learning Research (JMLR)."""

import re

import pypdf.errors
import pystow
import requests
from bs4 import BeautifulSoup, Tag
from curies import Reference
from pydantic import ValidationError
from pypdf import PdfReader
from tqdm import tqdm, trange
from tqdm.contrib.logging import logging_redirect_tqdm

from autoreviewer.comparison.sources.utils import (
    ArticlePDFLink,
    ArticleRepositoryLink,
    clean_repository,
    print_tabulate_links,
)

__all__ = [
    "get_jmlr_mloss_repos",
    "get_jmlr_repos",
]

MODULE = pystow.module("jmlr")

HOST = "https://www.jmlr.org"

GITHUB_URL_REF_RE = re.compile(
    r"https?://(?:www\.)?github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+,\s\d{4}\.?"
)
GITHUB_URL_RE = re.compile(r"https?://(?:www\.)?github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


def get_jmlr_repos() -> list[ArticleRepositoryLink]:
    """Get JMLR article-repository links."""
    links = []
    for p in tqdm(get_jmlr_pdfs(), desc="Getting JMLR", unit_scale=True, unit="article"):
        for github in set(_extract_repositories_from_pdf(str(p.pdf_url))):
            try:
                link = ArticleRepositoryLink(
                    reference=p.reference,
                    date=p.date,
                    title=p.title,
                    github=github,
                )
            except ValidationError:
                tqdm.write(
                    f"failed to validate {dict(reference=p.reference, date=p.date, title=p.title, github=github)}"
                )
            else:
                links.append(link)
    return links


def _extract_repositories_from_pdf(url: str) -> list[str]:
    """Return the GitHub repo(s) from the PDF."""
    with logging_redirect_tqdm():
        path = MODULE.ensure("papers", url=url)
        cache = path.with_suffix(".txt")
        if cache.is_file():
            return cache.read_text().splitlines(keepends=False)

        try:
            reader = PdfReader(path)
        except pypdf.errors.EmptyFileError:
            return []
        repositories = set()
        repositories_with_ref = set()
        for page in reader.pages:
            text = page.extract_text()
            stand_alone = list(GITHUB_URL_RE.findall(text))
            with_ref = list(GITHUB_URL_REF_RE.findall(text))
            for repository in stand_alone:
                repositories.add(repository.rstrip("."))
            for repository_with_ref in with_ref:
                repositories_with_ref.add(repository_with_ref.rsplit(",", 1)[0].rstrip("."))
        rv = sorted(clean_repository(r) for r in repositories - repositories_with_ref)
        cache.write_text("\n".join(rv))
        return rv


def get_jmlr_pdfs() -> list[ArticlePDFLink]:
    """Get article-pdf annotations."""
    links: list[ArticlePDFLink] = []
    # start at 7 when html pages evened out
    for volume in trange(7, 26):
        url = f"{HOST}/papers/v{volume}/"

        with logging_redirect_tqdm():
            path = MODULE.ensure("volumes", url=url)
        soup = BeautifulSoup(path.read_text(), features="html.parser")
        content = soup.find(id="content")
        if content is None:
            raise ValueError

        for dl in content.find_all("dl"):
            title_tag = dl.find("dt")
            if not title_tag.text:
                raise ValueError

            date = _get_date(dl)

            pdf_anchor = _get_link(dl, "pdf")
            if pdf_anchor is None:
                tqdm.write(
                    f"[{url}] could not find PDF link for volume {volume} - {title_tag.text}"
                )
                continue

            href = pdf_anchor.attrs["href"]
            if not href.endswith(".pdf"):
                continue
            pdf_url = HOST + pdf_anchor.attrs["href"]

            bib_anchor = _get_link(dl, "bib")
            if bib_anchor is None:
                raise ValueError
            identifier = _parse_jmlr_identifier(bib_anchor)

            links.append(
                ArticlePDFLink(
                    pdf_url=pdf_url,
                    title=title_tag.text,
                    date=date,
                    reference=Reference(prefix="jmlr", identifier=identifier),
                )
            )
    return links


JMLR_MLOSS_FIXES: dict[str, str] = {
    "https://avalanche.continualai.org/": "https://github.com/ContinualAI/avalanche",
    "https://pygod.org": "https://github.com/pygod-team/pygod",
    "https://rtiinternational.github.io/SMART/": "https://github.com/RTIInternational/SMART",
    "http://scikit.ml/": "https://github.com/scikit-multilearn/scikit-multilearn",
    "http://snap.stanford.edu/snapvx/#install": "https://github.com/snap-stanford/snapvx",
    "https://pystruct.github.io": "https://github.com/pystruct/pystruct",
    "https://www.manopt.org": "https://github.com/NicolasBoumal/manopt",
}

JMLR_MLOSS_BASE_URL = "https://www.jmlr.org/mloss/"


def get_jmlr_mloss_repos() -> list[ArticleRepositoryLink]:
    """Get MLOSS article-repository links."""
    res = requests.get(JMLR_MLOSS_BASE_URL)
    soup = BeautifulSoup(res.text, features="html.parser")
    content = soup.find(id="content")
    if content is None:
        raise ValueError

    links: list[ArticleRepositoryLink] = []
    for dl in tqdm(content.find_all("dl"), desc="Getting MLOSS", unit="article"):
        title_tag = dl.find("dt")
        if not title_tag.text:
            raise ValueError

        date = _get_date(dl)

        code_anchor = _get_link(dl, "code")
        if code_anchor is None:
            raise ValueError

        repository_url: str = code_anchor.attrs["href"]
        repository_url = JMLR_MLOSS_FIXES.get(repository_url, repository_url).rstrip("/")
        github: str | None
        if "github.com" in repository_url:
            github = clean_repository(repository_url)
            if "/" not in github:
                github = None
        else:
            github = None

        bib_anchor = _get_link(dl, "bib")
        if bib_anchor is None:
            raise ValueError
        identifier = _parse_jmlr_identifier(bib_anchor)

        links.append(
            ArticleRepositoryLink(
                date=date,
                title=title_tag.text,
                github=github,
                reference=Reference(prefix="jmlr", identifier=identifier),
            )
        )
    return links


def _get_date(dl: Tag) -> str:
    dd = iter(dl.find("dd"))
    next(dd)
    year = next(dd).strip().rstrip(".").split(",")[1].strip()
    date = year + "-01-01"
    return date


def _parse_jmlr_identifier(anchor: Tag) -> str:
    return anchor.attrs["href"].removesuffix(".bib").removeprefix("/papers/v")


def _get_link(dl: Tag, text: str) -> Tag | None:
    for anchor in dl.find_all("a"):
        if anchor.text == text:
            return anchor
    return None


if __name__ == "__main__":
    # print_tabulate_links(get_jmlr_mloss_repos())
    print_tabulate_links(get_jmlr_repos())
