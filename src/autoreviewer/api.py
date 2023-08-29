# -*- coding: utf-8 -*-

"""Main code."""

from dataclasses import dataclass, field
from pathlib import Path
import os
import datetime
from jinja2 import Environment, FileSystemLoader

from autoreviewer.utils import get_readme, get_license_file, get_setup_config

HERE = Path(__file__).parent.resolve()
TEMPLATES = HERE.joinpath("templates")

environment = Environment(
    autoescape=True, loader=FileSystemLoader(TEMPLATES), trim_blocks=True, lstrip_blocks=True
)
review_template = environment.get_template("review.md")


@dataclass
class Results:
    """Results from analysis.

    1. Does the repository contain a LICENSE file in its root?
    2. Does the repository contain a README file in its root?
    3. Does the repository contain an associated public issue tracker?
    4. Has the repository been externally archived on Zenodo, FigShare, or equivalent that is referenced in the README?
    5. Does the README contain installation documentation?
    6. Is the code from the repository installable in a straight-forward manner?
    7. Does the code conform to an external linter (e.g., black for Python)?
    """

    owner: str
    repository: str
    has_license: bool
    has_readme: bool
    has_zenodo: bool
    date: datetime.date = field(default_factory=datetime.date.today)
    readme_type: str | None = None
    branch: str = "main"

    @property
    def passes(self) -> bool:
        return False

    def render(self) -> str:
        return review_template.render(
            repo=f"{self.owner}/{self.repository}",
            repo_url=f"https://github.com/{self.owner}/{self.repository}",
            branch=self.branch,
            has_license=self.has_license,
            has_readme=self.has_readme,
            has_zenodo=self.has_zenodo,
            readme_type=self.readme_type,
            date=self.date.strftime("%Y-%m-%d"),
            commit="12345678",  # FIXME
            passes=self.passes,
            issue=1, #  FIXME
        )

    def print(self, file=None) -> None:
        print(self.render(), file=file)

    def write_pandoc(self, path: str | Path) -> None:
        path = Path(path).resolve()
        markdown_path = path.with_suffix(".md")
        markdown_path.write_text(self.render())
        command = f"pandoc {markdown_path.as_posix()} -o {path.as_posix()}"
        print(command)
        os.system(command)


README_MAP = {"README.md": "markdown", "README.rst": "rst", "README": "txt", None: None}


def review(owner: str, repository: str) -> Results:
    """Review a repository."""
    repo = f"{owner}/{repository}"
    branch = "main"  # TODO get main branch from GitHub API

    # TODO get license type - later report on if is OSS appropriate
    license_name, license_text = get_license_file(repo=repo, branch=branch)
    readme_name, readme_text = get_readme(repo=repo, branch=branch)
    readme_type = README_MAP[readme_name]
    if readme_name is None:
        has_zenodo = False
    elif readme_name == "README.md":
        has_zenodo = False  # FIXME implement parser
    else:
        raise NotImplementedError(f"parser not written for {readme_name} extension")

    return Results(
        owner=owner,
        repository=repository,
        has_license=license_text is not None,
        has_readme=readme_text is not None,
        readme_type=readme_type,
        has_zenodo=has_zenodo,
    )


if __name__ == "__main__":
    review("jonghyunlee1993", "DLM-DTI_hint-based-learning").write_pandoc(
        HERE.joinpath("review.pdf")
    )
