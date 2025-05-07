import datetime

from curies import Reference
from pydantic import AnyHttpUrl, BaseModel, Field
from tabulate import tabulate

from autoreviewer.utils import GitHubRepository

__all__ = [
    "ArticleRepositoryLink",
    "ArticlePDFLink",
    "SKIP_REPOSITORIES",
    "print_tabulate_links",
]


class ArticlePDFLink(BaseModel):
    reference: Reference
    date: datetime.date
    title: str | None
    pdf_url: AnyHttpUrl


class ArticleEpubLink(BaseModel):
    reference: Reference
    date: datetime.date
    title: str | None
    pdf: AnyHttpUrl


def clean_repository(s: str) -> str:
    s = s.removeprefix("https://github.com/")
    s = s.removeprefix("http://github.com/")
    s = s.removesuffix(".git")
    s = s.rstrip("/")
    return s


class ArticleRepositoryLink(BaseModel):
    """A tuple containing all info about an article + repo."""

    reference: Reference
    date: datetime.date | None
    title: str | None
    github: str | None = Field(..., pattern="^[a-zA-Z0-9-_]+/[a-zA-Z0-9-_\\.]+$")

    def get_github_repository(self) -> GitHubRepository | None:
        if self.github is None:
            return None

        owner, _, repo = self.github.partition("/")
        if not repo:
            # TODO logging
            return None
        return GitHubRepository(owner, repo)


def print_tabulate_links(links: list[ArticleRepositoryLink]):
    print(
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
