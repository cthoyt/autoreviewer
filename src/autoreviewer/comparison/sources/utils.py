"""Utilities for literature sources."""

import datetime
import re

import pypdf.errors
from curies import Reference
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, ValidationError
from pypdf import PdfReader
from tabulate import tabulate
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from autoreviewer.api import Results
from autoreviewer.utils import MODULE, GitHubRepository

__all__ = [
    "ArticleRepositoryLink",
    "ArticlePDFLink",
    "SKIP_REPOSITORIES",
    "ResultPack",
    "print_tabulate_links",
]


class ArticlePDFLink(BaseModel):
    """An object for an article's metadata and PDF link."""

    reference: Reference
    date: datetime.date
    title: str | None
    pdf_url: AnyHttpUrl


def clean_repository(s: str) -> str:
    """Clean a GitHub repository URL string."""
    s = s.removeprefix("https://www.github.com/")
    s = s.removeprefix("http://www.github.com/")
    s = s.removeprefix("https://github.com/")
    s = s.removeprefix("http://github.com/")
    s = s.removesuffix(".git")
    s = s.rstrip("/")
    s = s.strip()
    return s


class ArticleRepositoryLink(BaseModel):
    """A tuple containing all info about an article + repo."""

    model_config = ConfigDict(frozen=True)

    reference: Reference
    date: datetime.date | None
    title: str | None
    github: str | None = Field(..., pattern="^[a-zA-Z0-9-_]+/[a-zA-Z0-9-_\\.]+$")

    def get_github_repository(self) -> GitHubRepository | None:
        """Get a GitHub repository pair."""
        if self.github is None:
            return None

        owner, _, repo = self.github.partition("/")
        if not repo:
            # TODO logging
            return None
        return GitHubRepository(owner, repo)


def print_tabulate_links(links: list[ArticleRepositoryLink]):
    """Print article-repository links."""
    print(  # noqa:T201
        tabulate(
            [(link.date, link.reference.curie, link.github, link.title) for link in links],
            headers=["date", "ref", "github", "title"],
        )
    )


#: A set of repositories to skip from analysis
SKIP_REPOSITORIES: set[GitHubRepository] = {
    GitHubRepository("shenggenglin", "mddi-scl"),
    GitHubRepository("duaibeom", "molfindergithubrepository"),
    GitHubRepository("awslabs", "dgl-livesci"),
    GitHubRepository("kohulan", "smiles-to-iupac-translator"),  # password protected
}


class ResultPack(BaseModel):
    """An object for journal, an article-repo link, and review results."""

    journal: str
    link: ArticleRepositoryLink
    results: Results | None = None


GITHUB_URL_REF_RE = re.compile(
    r"https?://(?:www\.)?github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+,\s\d{4}\.?"
)
GITHUB_URL_RE = re.compile(r"https?://(?:www\.)?github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


def extract_repositories_from_pdf(journal_key: str, url: str) -> list[str]:
    """Return the GitHub repo(s) from the PDF."""
    with logging_redirect_tqdm():
        try:
            path = MODULE.ensure(journal_key, "papers", url=url)
        except Exception:
            return []

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


def get_repos_from_pdfs(
    journal_key: str, inp: list[ArticlePDFLink], desc: str
) -> list[ArticleRepositoryLink]:
    """Get repositories from PDFs."""
    links = []
    for p in tqdm(inp, desc=desc, unit_scale=True, unit="article"):
        for github in set(
            extract_repositories_from_pdf(journal_key=journal_key, url=str(p.pdf_url))
        ):
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


MIN_YEAR = 2018
MAX_YEAR = datetime.date.today().year
