# -*- coding: utf-8 -*-

"""Command line interface for :mod:`autoreviewer`.

Why does this file exist, and why not put this in ``__main__``? You might be tempted to import things from ``__main__``
later, but that will cause problems--the code will get executed twice:

- When you run ``python3 -m autoreviewer`` python will execute``__main__.py`` as a script.
  That means there won't be any ``autoreviewer.__main__`` in ``sys.modules``.
- When you import __main__ it will get executed again (as a module) because
  there's no ``autoreviewer.__main__`` in ``sys.modules``.

.. seealso:: https://click.palletsprojects.com/en/7.x/setuptools/#setuptools-integration
"""

import logging
from pathlib import Path

import click

from autoreviewer import review

__all__ = [
    "main",
]

logger = logging.getLogger(__name__)


@click.command()
@click.argument("name_or_url")
@click.option("--path", type=click.Path())
def main(name_or_url: str, path: Path | None):
    """CLI for autoreviewer."""
    owner, repo, *_ = (
        name_or_url.removeprefix("https://github.com/").removesuffix(".git").rstrip("/").split("/")
    )
    repo_clean = repo.lower().replace("_", "-")
    results = review(owner, repo)
    if path is not None:
        results.write_pandoc(path)
    else:
        path = Path.cwd().joinpath(f"{repo_clean}-review.pdf")
        results.write_pandoc(path)
        click.echo(f"Wrote review PDF to {path}")


if __name__ == "__main__":
    main()
