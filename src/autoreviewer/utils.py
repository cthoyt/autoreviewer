"""Utilities."""

import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import pystow
import requests
from ratelimit import rate_limited
from tqdm import tqdm

#: Wikidata SPARQL endpoint. See https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service#Interfacing
WIKIDATA_ENDPOINT = "https://query.wikidata.org/bigdata/namespace/wdq/sparql"


#: The module where JCheminf stuff goes
MODULE = pystow.module("jcheminf")


def strip(s: str) -> str:
    """Strip bad characters."""
    for t in ".,\\/()[]{}_":
        s = s.strip(t)
    return s


@rate_limited(calls=5_000, period=60 * 60)
def github_api(
    url: str,
    accept: Optional[str] = None,
    params: Optional[dict[str, Any]] = None,
    token: str | None = None,
) -> requests.Response:
    """Request an endpoint from the GitHub API."""
    if token is None:
        # Load the GitHub access token via PyStow. We'll
        # need it, so we don't hit the rate limit
        token = pystow.get_config("github", "token", raise_on_missing=True)
    headers = {
        "Authorization": f"token {token}",
    }
    if accept:
        headers["Accept"] = accept
    return requests.get(url, headers=headers, params=params)


@lru_cache
def get_repo_metadata(repo) -> requests.Response:
    """Get repository metadata."""
    return github_api(f"https://api.github.com/repos/{repo}")


ResTup = tuple[str, str] | tuple[None, None]


def get_file(
    repo: str, name: str | list[str], *, branch: str = "main", desc: str | None = None
) -> ResTup:
    """Get the file name and text, if available."""
    base_url = f"https://raw.githubusercontent.com/{repo}/{branch}"
    if isinstance(name, str):
        name = [name]
    for n in tqdm(name, leave=False, desc=desc):
        url = f"{base_url}/{n}"
        res = requests.get(url, timeout=1)  # timeout is short since these are small, simple files
        if res.status_code == 200:
            return n, res.text
    return None, None


@lru_cache
def get_readme(repo: str, branch: str = "main") -> ResTup:
    """Get the readme file name and text, if available."""
    return get_file(
        repo, branch=branch, name=["README.md", "README.rst", "README.txt"], desc="Finding README"
    )


@lru_cache
def get_setup_config(repo: str, branch: str = "main") -> ResTup:
    """Get the setup configuration file name and text, if available."""
    return get_file(
        repo,
        branch=branch,
        name=["setup.cfg", "setup.py", "pyproject.toml"],
        desc="Finding setup conf.",
    )


@lru_cache
def get_license_file(repo: str, branch: str = "main") -> ResTup:
    """Get the license file name and text, if available."""
    return get_file(
        repo, branch=branch, name=["LICENSE", "LICENSE.md", "LICENSE.rst"], desc="Finding license"
    )


def get_repo_path(owner: str, repo: str) -> Path:
    """Clone a repository from GitHub locally inside the PyStow folder."""
    directory = pystow.join("github", owner, repo)
    if directory.is_dir():
        return directory
    directory.mkdir(parents=True)
    url = f"https://github.com/{owner}/{repo}"
    subprocess.check_call(["git", "clone", url, directory.as_posix()])
    return directory


def check_black(path: str | Path) -> bool:
    """Check if the folder passes ``black --check``."""
    path = Path(path).resolve()
    try:
        subprocess.check_call(["black", path.as_posix(), "--check"])
    except subprocess.CalledProcessError:
        return False
    else:
        return True


def remote_check_black(url) -> bool:
    """Check if the Git repository passes ``black --check``."""
    with tempfile.TemporaryDirectory() as directory:
        d = Path(directory)
        subprocess.check_call(["git", "clone", url, d.as_posix()])
        return check_black(d)


def remote_check_github(owner, repo) -> bool:
    """Check if the GitHub repository passes ``black --check``."""
    return remote_check_black(f"https://github.com/{owner}/{repo}")


def get_has_issues(owner: str, name: str) -> bool:
    """Check if the GitHub repository has issues enabled."""
    res = get_repo_metadata(f"{owner}/{name}").json()
    return res["has_issues"]


def get_default_branch(owner: str, name: str) -> str:
    """Get the default branch for a GitHub repository."""
    res = get_repo_metadata(f"{owner}/{name}").json()
    return res["default_branch"]
