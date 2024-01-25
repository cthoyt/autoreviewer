# -*- coding: utf-8 -*-

"""Main code."""

import dataclasses
import datetime
import os
from dataclasses import dataclass, field
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader
from pystow.utils import get_commit
from tqdm import tqdm

from autoreviewer.utils import (
    check_no_scripts,
    get_default_branch,
    get_has_issues,
    get_is_fork,
    get_license,
    get_programming_language,
    get_readme,
    get_setup_config,
    remote_check_black_github,
    remote_check_pyroma,
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
    language: str
    license_name: str | None
    has_zenodo: bool
    has_setup: bool
    has_installation_docs: bool
    has_issues: bool
    is_fork: bool
    is_blackened: bool
    pyroma_score: int
    pyroma_failures: list[str]
    commit: str
    branch: str
    root_scripts: list[str]

    date: datetime.date = field(default_factory=datetime.date.today)
    readme_type: str | None = None

    def get_dict(self):
        """Get this review as a dict."""
        d = dataclasses.asdict(self)
        d["repo"] = self.repo_url
        d["license"] = d.pop("license_name")
        d["commit"] = d.pop("commit")[:8]
        del d["owner"]
        del d["name"]
        del d["pyroma_failures"]
        del d["date"]
        return d

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
            is_blackened=self.is_blackened,
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
            "linkcolor=blue -V urlcolor=blue -V toccolor=gray"
        )
        click.echo(command)
        os.system(command)


README_MAP = {"README.md": "markdown", "README.rst": "rst", "README.txt": "txt", None: None}


def _has_markdown_installation(text: str | None) -> bool:
    if not text:
        return False
    for line in text.splitlines():
        if line.startswith("#") and "installation" in line.lower():
            return True
    return False


def review(owner: str, name: str) -> Results:
    """Review a repository."""
    repo = f"{owner}/{name}"
    branch = get_default_branch(owner, name)
    is_blackened = remote_check_black_github(owner, name)

    readme_name, readme_text = get_readme(repo=repo, branch=branch)
    readme_type = README_MAP[readme_name]
    if readme_type is None:
        has_zenodo = False
        has_installation_docs = False
    elif readme_type == "markdown":
        has_zenodo = readme_text is not None and (
            "https://zenodo.org/badge/DOI/10.5281/" in readme_text
            or "https://zenodo.org/badge/latestdoi/" in readme_text
        )
        has_installation_docs = _has_markdown_installation(readme_text)
    elif readme_type == "rst":
        has_zenodo = False
        has_installation_docs = False
        tqdm.write(f"README was RST, assuming missing zenodo/installation docs: {repo}")
    elif readme_type == "txt":
        has_zenodo = False
        has_installation_docs = False
        tqdm.write(f"README was TXT, assuming missing zenodo/installation docs: {repo}")
    else:
        raise TypeError

    setup_name, setup_text = get_setup_config(repo=repo, branch=branch)
    has_setup = setup_name is not None

    license_name = get_license(owner, name)

    pyroma_score, pyroma_failures = remote_check_pyroma(owner, name)
    has_issues = get_has_issues(owner, name)
    language = get_programming_language(owner, name)
    is_fork = get_is_fork(owner, name)
    commit = get_commit(owner, name)

    root_scripts = check_no_scripts(owner, name)

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
        is_blackened=is_blackened,
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
