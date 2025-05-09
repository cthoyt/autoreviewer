"""Generate summary charts."""

import datetime
import gzip
from collections import ChainMap

import click
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from autoreviewer.comparison.main import ANALYSIS_PATH, HERE
from autoreviewer.comparison.sources.utils import MAX_YEAR, MIN_YEAR, ResultPack

SUMMARY_PATH = HERE.joinpath("summary.svg")
ANALYSIS_TSV_PATH = HERE.joinpath("analysis.tsv")


def _p_status(x):
    if pd.isna(x):
        return None
    elif x <= 0:
        return False
    else:
        return True


def _license_status(x):
    if pd.isna(x):
        return "No License"
    elif x == "Unknown":
        return "Unknown"
    else:
        return "Present"


def _percentage(df, column):
    series = df.groupby(["year", "journal"])[column].mean()
    rdf = series.to_frame().reset_index()
    return rdf


def _percentage_axis(ax):
    from matplotlib.ticker import FuncFormatter

    formatter = FuncFormatter(lambda y, _: "{:.1%}".format(y))
    ax.yaxis.set_major_formatter(formatter)


JOURNAL = {
    "joss": "JOSS",
    "iclr": "ICLR",
    "neurips": "NeurIPS",
    "jmlr": "JMLR",
    "mloss": "JMLR-MLOSS",
    "jcheminf": "J. Chem. Inf.",
    "bmcbioinfo": "BMC Bioinformatics",
}


@click.command()
def main():
    """Generate summary charts."""
    with gzip.open(ANALYSIS_PATH, "rt") as file:
        models = [ResultPack.model_validate_json(line) for line in file]
    summarize(models)


def summarize(models: list[ResultPack]) -> None:
    """Summarize all result packs."""
    fig, axes = plt.subplots(2, 4, figsize=(14, 5))

    axes = axes.ravel()

    rows = [
        dict(
            ChainMap(
                model.link.model_dump(),
                (model.results.model_dump() if model.results else {}),
                {"journal": model.journal},
            )
        )
        for model in models
    ]

    df = pd.DataFrame(rows)
    del df["ruff_check_errors"]
    del df["pyroma_failures"]
    df["has_github"] = df["github"].notna()
    df["journal"] = df["journal"].map(lambda s: JOURNAL.get(s, s))

    def _fix_date(s):
        if pd.isna(s):
            return s

        if isinstance(s, datetime.date):
            return s.year

        if isinstance(s, str):
            return s[:5]

        raise TypeError

    df = df[df["date"].notna()]
    df["year"] = df["date"].map(_fix_date)
    df = df[(MIN_YEAR <= df["year"]) & (df["year"] < MAX_YEAR)]  # don't make ragged chart

    df["license_status"] = df["license_name"].map(_license_status)
    df["has_known_license"] = df["license_status"] == "Present"
    df["package_status"] = df["pyroma_score"].map(_p_status)
    df["reference"] = df["reference"].map(lambda x: x["prefix"] + ":" + x["identifier"])
    df["has_loose_root_scripts"] = df["root_scripts"].map(
        lambda x: isinstance(x, list) and len(x) > 0
    )
    del df["root_scripts"]

    df.to_csv(ANALYSIS_TSV_PATH, sep="\t", index=False)

    g1 = sns.lineplot(
        x="year",
        y="has_github",
        hue="journal",
        data=_percentage(df, "has_github"),
        ax=axes[0],
    )
    g1.legend_.remove()
    axes[0].set_ylabel("")
    axes[0].set_xlabel("")
    axes[0].set_title("Has GitHub Repo")
    _percentage_axis(axes[0])

    g2 = sns.lineplot(
        x="year",
        y="has_issues",
        hue="journal",
        data=_percentage(df[df["has_github"]], "has_issues"),
        ax=axes[1],
    )
    g2.legend_.remove()
    axes[1].set_ylabel("")
    axes[1].set_xlabel("")
    axes[1].set_title("Has Issue Tracker")
    _percentage_axis(axes[1])

    g3 = sns.lineplot(
        x="year",
        y="package_status",
        hue="journal",
        data=_percentage(df[df["has_github"] & df["package_status"].notna()], "package_status"),
        ax=axes[2],
    )
    g3.legend_.remove()
    axes[2].set_xlabel("")
    axes[2].set_ylabel("")
    axes[2].set_title("Packaged Code")
    _percentage_axis(axes[2])

    g4 = sns.lineplot(
        x="year",
        y="is_formatted",
        hue="journal",
        data=_percentage(df[df["has_github"]], "is_formatted"),
        ax=axes[3],
    )
    g4.legend_.remove()
    axes[3].set_xlabel("")
    axes[3].set_ylabel("")
    axes[3].set_title("Applied Formatting")
    _percentage_axis(axes[3])

    g5 = sns.lineplot(
        x="year",
        y="is_linted",
        hue="journal",
        data=_percentage(df[df["has_github"]], "is_linted"),
        ax=axes[4],
    )
    g5.legend_.remove()
    axes[4].set_xlabel("")
    axes[4].set_ylabel("")
    axes[4].set_title("Applied Linting")
    _percentage_axis(axes[4])

    g6 = sns.lineplot(
        x="year",
        y="has_installation_docs",
        hue="journal",
        data=_percentage(df[df["has_github"]], "has_installation_docs"),
        ax=axes[5],
    )
    g6.legend_.remove()
    axes[5].set_xlabel("")
    axes[5].set_ylabel("")
    axes[5].set_title("Has Installation Documentation")
    _percentage_axis(axes[5])

    g7 = sns.lineplot(
        y="has_known_license",
        x="year",
        hue="journal",
        data=_percentage(df[df["has_github"]], "has_known_license"),
        ax=axes[6],
    )
    axes[6].set_xlabel("")
    axes[6].set_ylabel("")
    axes[6].set_title("Has (Known) License")
    _percentage_axis(axes[6])

    axes[7].axis("off")

    handles, labels = axes[6].get_legend_handles_labels()
    axes[7].legend(handles=handles, labels=labels, title="Venue")
    g7.legend_.remove()

    plt.suptitle("Cross-Venue Comparison", fontsize=16)
    plt.tight_layout()
    plt.savefig(SUMMARY_PATH, dpi=300)


if __name__ == "__main__":
    main()
