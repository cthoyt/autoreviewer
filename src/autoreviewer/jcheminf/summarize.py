"""Generate summary charts."""

import datetime

import click
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.ticker import FuncFormatter


def _p_status(x):
    if pd.isna(x):
        return "No Repo"
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
    formatter = FuncFormatter(lambda y, _: "{:.1%}".format(y))
    ax.yaxis.set_major_formatter(formatter)


JOURNAL = {
    "joss": "JOSS",
    "jcheminf": "J. Chem. Inf.",
    "bmcbioinfo": "BMC Bioinformatics",
}


@click.command()
def main():
    """Generate summary charts."""
    fig, axes = plt.subplots(2, 4, figsize=(14, 5))

    axes = axes.ravel()

    today = datetime.date.today()
    df = pd.read_csv("analysis.tsv", sep="\t")
    df["has_github"] = df["repo"].notna()

    df["journal"] = df["journal"].map(JOURNAL)

    def _fix_date(s):
        if pd.isna(s):
            return s
        if len(s) == 4:
            return s + "-01-01"
        return s

    df["date"] = pd.to_datetime(df["date"].map(_fix_date))
    df = df[df["date"].notna()]
    df["year"] = df["date"].dt.year
    # 2017 was the first year, where a repository was detected
    df = df[(2017 < df["year"]) & (df["year"] < today.year)]  # don't make ragged chart

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

    df["package_status"] = df["pyroma_score"].map(_p_status)
    g3 = sns.lineplot(
        x="year",
        y="package_status",
        hue="journal",
        data=_percentage(df[df["has_github"]], "package_status"),
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

    df["license_status"] = df["license"].map(_license_status)
    df["has_known_license"] = df["license_status"] == "Present"
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
    plt.savefig("summary.png", dpi=300)


if __name__ == "__main__":
    main()
