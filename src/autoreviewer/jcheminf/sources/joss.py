"""A source for the Journal of Open Source Software (JOSS)."""

import json
from typing import Any

import pystow
from curies import Reference
from tqdm import tqdm, trange
from tqdm.contrib.logging import logging_redirect_tqdm

from autoreviewer.jcheminf.sources.utils import ArticleRepositoryLink, clean_repository

__all__ = [
    "get_joss_repos",
]

MODULE = pystow.module("joss", "papers")

type ArticleMetadata = dict[str, Any]


def ensure_article_metadata_json(joss_article_id: int | str) -> ArticleMetadata:
    """Ensure the JOSS metadata via API."""
    if isinstance(joss_article_id, int):
        joss_article_id = str(joss_article_id).ljust(5, "0")
    url = f"https://joss.theoj.org/papers/10.21105/joss.{joss_article_id}.json"
    return MODULE.ensure_json(url=url)


def _get_tuple(j: ArticleMetadata) -> ArticleRepositoryLink:
    name = j["title"]

    repo_raw = j["software_repository"]
    if "github.com" not in repo_raw:
        repo = None
    elif "tree/master" in repo_raw:
        repo, _, _ = repo_raw.partition("/tree/master")
        repo = clean_repository(repo)
    else:
        repo = clean_repository(repo_raw)

    doi = j["doi"]
    year = f"{j["year"]}-01-01"
    return ArticleRepositoryLink(
        reference=Reference(prefix="doi", identifier=doi), date=year, title=name, github=repo
    )


def _not_python(j: ArticleMetadata) -> bool:
    return "Python" not in j["languages"]


def get_joss_repos(*, refresh: bool = False) -> list[ArticleRepositoryLink]:
    """Yield JOSS tuples."""
    if refresh:
        links = []
        for i in trange(1, 8000, desc="Getting JOSS", unit_scale=True, unit="article"):
            with logging_redirect_tqdm():
                try:
                    metadata = ensure_article_metadata_json(i)
                except Exception:
                    continue
                if _not_python(metadata):
                    continue
                links.append(_get_tuple(metadata))
        return links
    else:
        links = []
        for path in tqdm(
            list(MODULE.base.glob("*.json")), desc="Getting JOSS", unit_scale=True, unit="article"
        ):
            try:
                metadata = json.loads(path.read_text())
            except json.decoder.JSONDecodeError:
                continue
            try:
                yv = _get_tuple(metadata)
            except Exception as e:
                tqdm.write(f"failed on {path}: {e}")
                continue
            if _not_python(metadata):
                continue
            links.append(yv)
        return links
