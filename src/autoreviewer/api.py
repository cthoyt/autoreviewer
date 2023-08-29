# -*- coding: utf-8 -*-

"""Main code."""

import datetime
import os
from dataclasses import dataclass, field
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader
from pystow.utils import get_commit

from autoreviewer.utils import (
    get_default_branch,
    get_has_issues,
    get_license_file,
    get_readme,
    get_setup_config,
    remote_check_github,
)

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
    name: str
    has_license: bool
    has_readme: bool
    has_zenodo: bool
    has_setup: bool
    has_installation_docs: bool
    has_issues: bool
    is_blackened: bool
    commit: str
    date: datetime.date = field(default_factory=datetime.date.today)
    readme_type: str | None = None
    branch: str = "main"

    @property
    def repo(self) -> str:
        """Get the full repo."""
        return f"{self.owner}/{self.name}"

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
                self.is_blackened,
            ]
        )

    def render(self) -> str:
        """Render the template for GitHub issues."""
        return review_template.render(
            repo=self.repo,
            repo_url=f"https://github.com/{self.repo}",
            name=self.name,
            branch=self.branch,
            has_license=self.has_license,
            has_readme=self.has_readme,
            has_zenodo=self.has_zenodo,
            has_setup=self.has_setup,
            has_installation_docs=self.has_installation_docs,
            readme_type=self.readme_type,
            has_issues=self.has_issues,
            date=self.date.strftime("%Y-%m-%d"),
            commit=self.commit,
            passes=self.passes,
            issue=None,  # FIXME
        )

    def write_pandoc(self, path: str | Path) -> None:
        """Write to a PDF with Pandoc."""
        path = Path(path).resolve()
        markdown_path = path.with_suffix(".md")
        markdown_path.write_text(self.render())
        click.echo(f"Wrote review markdown to {markdown_path}")
        command = (
            f"pandoc {markdown_path.as_posix()} -o {path.as_posix()} -V colorlinks=true -V "
            f"linkcolor=blue -V urlcolor=blue -V toccolor=gray"
        )
        click.echo(command)
        os.system(command)


README_MAP = {"README.md": "markdown", "README.rst": "rst", "README": "txt", None: None}


def review(owner: str, name: str) -> Results:
    """Review a repository."""
    repo = f"{owner}/{name}"
    branch = get_default_branch(owner, name)

    readme_name, readme_text = get_readme(repo=repo, branch=branch)
    readme_type = README_MAP[readme_name]
    if readme_type is None:
        has_zenodo = False
        has_installation_docs = False
    elif readme_type == "markdown":
        has_zenodo = (
            readme_text is not None and "https://zenodo.org/badge/DOI/10.5281/" in readme_text
        )
        has_installation_docs = readme_text is not None and "# Installation" in readme_text
    elif readme_type == "rst":
        raise NotImplementedError(f"parser not written for {readme_name} extension")
    elif readme_type == "txt":
        raise NotImplementedError(f"parser not written for {readme_name} extension")
    else:
        raise TypeError

    setup_name, setup_text = get_setup_config(repo=repo, branch=branch)
    has_setup = setup_name is not None

    # TODO get license type - later report on if is OSS appropriate
    license_name, license_text = get_license_file(repo=repo, branch=branch)

    is_blackened = remote_check_github(owner, name)
    has_issues = get_has_issues(owner, name)

    commit = get_commit(owner, name)

    return Results(
        owner=owner,
        name=name,
        has_license=license_name is not None,
        has_readme=readme_name is not None,
        readme_type=readme_type,
        has_installation_docs=has_installation_docs,
        has_zenodo=has_zenodo,
        has_issues=has_issues,
        is_blackened=is_blackened,
        has_setup=has_setup,
        commit=commit,
    )


if __name__ == "__main__":
    review("jonghyunlee1993", "DLM-DTI_hint-based-learning").write_pandoc(
        HERE.joinpath("review.pdf")
    )
