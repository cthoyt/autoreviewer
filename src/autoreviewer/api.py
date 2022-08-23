# -*- coding: utf-8 -*-

"""Main code."""

from dataclasses import dataclass
from pathlib import Path
from typing import Union

from jinja2 import Environment, FileSystemLoader

HERE = Path(__file__).parent.resolve()
TEMPLATES = HERE.joinpath("templates")

environment = Environment(
    autoescape=True, loader=FileSystemLoader(TEMPLATES), trim_blocks=True, lstrip_blocks=True
)


@dataclass
class Results:
    """Results from analysis."""

    owner: str
    repository: str

    def write(self, path: Union[str, Path]):
        """Write to a path."""


def review(owner: str, repository: str) -> Results:
    """Review a repository."""
    return Results(
        owner=owner,
        repository=repository,
    )
