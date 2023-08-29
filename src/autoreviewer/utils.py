"""Utilities."""

from typing import Any, Optional

import pystow
import requests
from ratelimit import rate_limited
from tqdm import tqdm
from functools import lru_cache

#: Wikidata SPARQL endpoint. See https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service#Interfacing
WIKIDATA_ENDPOINT = "https://query.wikidata.org/bigdata/namespace/wdq/sparql"

# Load the GitHub access token via PyStow. We'll
# need it so we don't hit the rate limit
TOKEN = pystow.get_config("github", "token", raise_on_missing=True)

#: The module where JCheminf stuff goes
MODULE = pystow.module("jcheminf")


def strip(s: str) -> str:
    """Strip bad characters."""
    for t in ".,\\/()[]{}_":
        s = s.strip(t)
    return s


@rate_limited(calls=5_000, period=60 * 60)
def github_api(
    url: str, accept: Optional[str] = None, params: Optional[dict[str, Any]] = None
) -> requests.Response:
    """Request an endpoint from the GitHub API."""
    headers = {
        "Authorization": f"token {TOKEN}",
    }
    if accept:
        headers["Accept"] = accept
    return requests.get(url, headers=headers, params=params)


def get_repo_metadata(repo) -> requests.Response:
    return github_api(f"https://api.github.com/repos/{repo}")


ResTup = tuple[str, str] | tuple[None, None]


def get_file(
    repo: str, name: str | list[str], *, branch: str = "main", desc: str | None = None
) -> ResTup:
    base_url = f"https://raw.githubusercontent.com/{repo}/{branch}"
    if isinstance(name, str):
        name = [name]
    for n in tqdm(name, leave=False, desc=desc):
        url = f"{base_url}/{n}"
        res = requests.get(url, timeout=1) # timeout is short since these are small, simple files
        if res.status_code == 200:
            return n, res.text
    return None, None


@lru_cache
def get_setup_config(repo: str, branch: str = "main") -> ResTup:
    return get_file(
        repo, branch=branch, name=["README.md", "README.rst", "README.txt"], desc="Finding README"
    )


@lru_cache
def get_readme(repo: str, branch: str = "main") -> ResTup:
    return get_file(
        repo,
        branch=branch,
        name=["setup.cfg", "setup.py", "pyproject.toml"],
        desc="Finding setup conf.",
    )


@lru_cache
def get_license_file(repo: str, branch: str = "main") -> ResTup:
    return get_file(
        repo, branch=branch, name=["LICENSE", "LICENSE.md", "LICENSE.rst"], desc="Finding license"
    )


def readme_has_zenodo(repo: str, branch: str = "main") -> str | None:
    name, content = get_readme(repo=repo, branch=branch)
    if name is None:
        return None
    if "https://zenodo.org/badge/" not in content:
        return None
    return "found"  # TODO parse file
