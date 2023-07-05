"""Utilities."""

import json
from typing import Any, Optional

import pystow
import requests
from ratelimit import rate_limited

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


LINK_PREFIX = "https://jcheminf.biomedcentral.com/articles/10.1186/"


def _get_jcheminf_repositories_dict():
    # NOTE: this is easily replaced with web scraping
    path = MODULE.join(name="github-dois.json")
    if path.is_file():
        return json.loads(path.read_text())
    rv = {}
    for repo in _iter_jcheminf_repositories():
        name = repo["full_name"]
        description = repo.get("description")
        if not description or LINK_PREFIX not in description:
            continue
        for part in description.split():
            part = strip(part)
            if part.startswith(LINK_PREFIX):
                rv[name] = part.removeprefix(LINK_PREFIX)
    path.write_text(json.dumps(rv, indent=2))
    return rv


def _iter_jcheminf_repositories(owner: str = "jcheminform", force: bool = False):
    """List repositories."""
    # NOTE: this is easily replaced with web scraping
    # TODO make this more extensible later. this works b.c. there are less than 300
    for page in range(1, 5):
        path = MODULE.join("github-jcheminform", name=f"{page}.json")
        if path.is_file() and not force:
            yield from json.loads(path.read_text())
        r = github_api(
            f"https://api.github.com/orgs/{owner}/repos",
            params={"per_page": 100, "page": page},
            accept="application/vnd.github+json",
        ).json()
        path.write_text(json.dumps(r, indent=2))
        yield from r
