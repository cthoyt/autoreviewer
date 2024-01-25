"""Utilities."""

import hashlib
import json
import subprocess
from contextlib import redirect_stderr, redirect_stdout
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import pystow
import requests
from pyroma import projectdata, ratings
from ratelimit import rate_limited
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

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
def get_repo_metadata(repo: str) -> dict:
    """Get repository metadata."""
    md5 = hashlib.md5()
    md5.update(repo.encode("utf-8"))
    path = MODULE.join("github-info", name=f"{md5.hexdigest()[:8]}.json")
    if path.is_file():
        return json.loads(path.read_text())
    res_json = github_api(f"https://api.github.com/repos/{repo}").json()
    path.write_text(json.dumps(res_json, indent=2))
    return res_json


ResTup = tuple[str, str] | tuple[None, None]


def get_file(
    repo: str, name: str | list[str], *, branch: str = "main", desc: str | None = None
) -> ResTup:
    """Get the file name and text, if available."""
    if isinstance(name, str):
        name = [name]

    owner, repo_name = repo.split("/")
    directory = pystow.join("github", owner, repo_name)
    if directory.exists() and any(directory.iterdir()):
        for n in name:
            p = directory.joinpath(n)
            if p.is_file():
                return n, p.read_text()
        return None, None

    base_url = f"https://raw.githubusercontent.com/{repo}/{branch}"
    for n in tqdm(name, leave=False, desc=desc, disable=True):
        url = f"{base_url}/{n}"
        with logging_redirect_tqdm():
            res = requests.get(
                url, timeout=1
            )  # timeout is short since these are small, simple files
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


def get_repo_path(owner: str, repo: str) -> Path | None:
    """Clone a repository from GitHub locally inside the PyStow folder."""
    directory = pystow.join("github", owner, repo)
    if directory.is_dir():
        if any(directory.iterdir()):  # check not empty
            return directory
    url = f"https://github.com/{owner}/{repo}"
    try:
        subprocess.check_call(["git", "clone", "--depth", "1", url, directory.as_posix()])
    except subprocess.CalledProcessError:
        return None
    return directory


def check_black(directory: str | Path) -> bool:
    """Check if the folder passes ``black --check``."""
    directory = Path(directory).resolve()
    parts = ["black", "--check", "--quiet", directory.as_posix()]
    try:
        subprocess.check_call(parts, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return False
    else:
        return True


def remote_check_black_github(owner, repo) -> bool:
    """Check if the GitHub repository passes ``black --check``."""
    directory = get_repo_path(owner, repo)
    if directory is None:
        raise RuntimeError
    return check_black(directory)


def get_has_issues(owner: str, name: str) -> bool:
    """Check if the GitHub repository has issues enabled."""
    res = get_repo_metadata(f"{owner}/{name}")
    return res["has_issues"]


def get_default_branch(owner: str, name: str) -> str:
    """Get the default branch for a GitHub repository."""
    res = get_repo_metadata(f"{owner}/{name}")
    return res["default_branch"]


def get_programming_language(owner: str, name: str) -> str:
    """Get the primary programing language."""
    res = get_repo_metadata(f"{owner}/{name}")
    return res["language"]


def get_is_fork(owner: str, name: str) -> bool:
    """Get if the repository is a fork."""
    res = get_repo_metadata(f"{owner}/{name}")
    return res["fork"]


def get_license(owner: str, name: str) -> str | None:
    """Get the license SPDX identifier, if available."""
    res = get_repo_metadata(f"{owner}/{name}")
    repo_license = (res.get("license") or {}).get("spdx_id")
    if repo_license == "NOASSERTION":
        return "Unknown"
    return repo_license


def check_pyroma(path: str | Path) -> tuple[int, list[str]]:
    """Return feedback from ``pyroma`` or None if passing."""
    path = Path(path).resolve()
    try:
        with redirect_stdout(None), redirect_stderr(None):
            data = projectdata.get_data(path.as_posix())
            rv = ratings.rate(data)
    except Exception:
        return 0, []
    else:
        return rv


def remote_check_pyroma(owner: str, name: str) -> tuple[int, list[str]]:
    """Check if the GitHub repository passes ``pyroma``."""
    directory = get_repo_path(owner, name)
    if directory is None:
        return 0, []
    return check_pyroma(directory)


def check_no_scripts(owner: str, name: str) -> list[str]:
    """Get scripts sitting in the home directory."""
    directory = get_repo_path(owner, name)
    if directory is None:
        return []
    scripts = directory.glob("*.py")
    skips = {"setup.py"}
    return [s.stem for s in scripts if s.name not in skips]
