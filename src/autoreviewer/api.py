# -*- coding: utf-8 -*-

"""Main code."""

import dataclasses
import datetime
import logging
import os
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field
from pystow.utils import get_commit
from tqdm import tqdm

from autoreviewer.utils import (
    check_no_scripts,
    get_default_branch,
    get_has_issues,
    get_is_fork,
    get_license,
    get_packaging_config,
    get_programming_language,
    get_readme,
    get_repo_path,
    remote_check_formatted_github,
    remote_check_pyroma,
    remove_check_linted_github,
)
from autoreviewer.version import get_version

HERE = Path(__file__).parent.resolve()
TEMPLATES = HERE.joinpath("templates")

environment = Environment(
    autoescape=True,
    loader=FileSystemLoader(TEMPLATES),
    trim_blocks=True,
    lstrip_blocks=True,
)
review_template = environment.get_template("review.md")

logging.getLogger("build").setLevel(logging.CRITICAL + 10)


class Results(BaseModel):
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
    name: str
    language: str
    license_name: str | None
    has_zenodo: bool
    has_setup: bool
    has_installation_docs: bool
    has_issues: bool
    is_fork: bool
    is_formatted: bool
    is_linted: bool
    pyroma_score: int
    pyroma_failures: list[str]
    commit: str
    branch: str
    root_scripts: list[str]
    ruff_check_errors: list

    date: datetime.date = Field(default_factory=datetime.date.today)
    readme_type: str | None = None

    @property
    def has_readme(self) -> bool:
        """Get if there is a README."""
        return self.readme_type is not None

    @property
    def repo(self) -> str:
        """Get the full repo."""
        return f"{self.owner}/{self.name}"

    @property
    def repo_url(self) -> str:
        """Get the repo URL."""
        return f"https://github.com/{self.repo}"

    @property
    def has_license(self) -> bool:
        """Get if the license exists."""
        return self.license_name is not None

    @property
    def passes(self) -> bool:
        """Return if all checks have passed."""
        return all(
            [
                self.has_issues,
                self.has_license,
                self.has_readme,
                self.has_zenodo,
                self.has_setup,
                self.has_installation_docs,
                self.is_formatted,
            ]
        )

    def render(self) -> str:
        """Render the template for GitHub issues."""
        return review_template.render(
            repo=self.repo,
            repo_url=self.repo_url,
            name=self.name,
            name_norm=self.name.replace("-", "_"),
            branch=self.branch,
            license_name=self.license_name,
            has_readme=self.has_readme,
            has_zenodo=self.has_zenodo,
            has_setup=self.has_setup,
            root_scripts=self.root_scripts,
            has_installation_docs=self.has_installation_docs,
            readme_type=self.readme_type,
            has_issues=self.has_issues,
            pyroma_score=self.pyroma_score,
            pyroma_failures=self.pyroma_failures,
            date=self.date.strftime("%Y-%m-%d"),
            commit=self.commit,
            passes=self.passes,
            is_formatted=self.is_formatted,
            is_linted=self.is_linted,
            ruff_check_errors=self.ruff_check_errors,
            issue=None,  # FIXME
            version=get_version(with_git_hash=True),
        )

    def write_pandoc(self, path: str | Path) -> None:
        """Write to a PDF with Pandoc."""
        path = Path(path).resolve()
        markdown_path = path.with_suffix(".md")
        markdown_path.write_text(self.render())
        click.echo(f"Wrote review markdown to {markdown_path}")
        command = (
            f"pandoc {markdown_path.as_posix()} -o {path.as_posix()} -V colorlinks=true -V "
            "linkcolor=blue -V urlcolor=blue -V toccolor=gray"
        )
        click.echo(command)
        os.system(command)


README_MAP: dict[str, str] = {
    "README.md": "markdown",
    "README.rst": "rst",
    "README.txt": "txt",
}


def _has_markdown_installation(text: str | None) -> bool:
    if not text:
        return False
    for line in text.splitlines():
        if line.startswith("#") and "installation" in line.lower():
            return True
    return False


def review(owner: str, name: str, *, cache: bool = True) -> Results:
    """Review a repository."""
    branch = get_default_branch(owner, name)

    # Get the repository, and re-cache if necessary
    get_repo_path(owner, name, cache=cache, branch=branch)

    is_formatted = remote_check_formatted_github(owner, name, branch=branch)

    lint_errors = remove_check_linted_github(owner, name, branch=branch)

    readme_result = get_readme(owner, name, branch=branch)
    if readme_result is None:
        readme_type = None
        has_zenodo = False
        has_installation_docs = False
    else:
        readme_type = README_MAP[readme_result.filename]
        match readme_type:
            case "markdown":
                has_zenodo = readme_result.contents is not None and (
                    "https://zenodo.org/badge/DOI/10.5281/" in readme_result.contents
                    or "https://zenodo.org/badge/latestdoi/" in readme_result.contents
                )
                has_installation_docs = _has_markdown_installation(readme_result.contents)
            case "rst":
                has_zenodo = False
                has_installation_docs = False
                tqdm.write(
                    f"README was RST, assuming missing zenodo/installation docs: {owner}/{name}"
                )
            case "txt":
                has_zenodo = False
                has_installation_docs = False
                tqdm.write(
                    f"README was TXT, assuming missing zenodo/installation docs: {owner}/{name}"
                )
            case _:
                raise TypeError

    packaging_config = get_packaging_config(owner, name, branch=branch)
    has_setup = packaging_config is not None

    license_name = get_license(owner, name)

    # TODO handle -1 for pyroma score, which happens when install fails
    pyroma_score, pyroma_failures = remote_check_pyroma(owner, name, branch=branch)
    has_issues = get_has_issues(owner, name)
    language = get_programming_language(owner, name)
    is_fork = get_is_fork(owner, name)
    commit = get_commit(owner, name)

    root_scripts = check_no_scripts(owner, name, branch=branch)

    return Results(
        owner=owner,
        name=name,
        language=language,
        license_name=license_name,
        readme_type=readme_type,
        has_installation_docs=has_installation_docs,
        has_zenodo=has_zenodo,
        has_issues=has_issues,
        is_fork=is_fork,
        is_formatted=is_formatted,
        ruff_check_errors=lint_errors,
        is_linted=len(lint_errors) == 0,
        pyroma_score=pyroma_score,
        pyroma_failures=pyroma_failures,
        has_setup=has_setup,
        root_scripts=root_scripts,
        commit=commit,
        branch=branch,
    )


if __name__ == "__main__":
    review("jonghyunlee1993", "DLM-DTI_hint-based-learning").write_pandoc(
        HERE.joinpath("review.pdf")
    )
