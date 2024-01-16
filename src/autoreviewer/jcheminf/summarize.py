"""Generate summary charts."""

import datetime

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
    series = df.groupby("year")[column].mean()
    rdf = series.to_frame().reset_index()
    return rdf


def _percentage_axis(ax):
    formatter = FuncFormatter(lambda y, _: "{:.1%}".format(y))
    ax.yaxis.set_major_formatter(formatter)


def main():
    """Generate summary charts."""
    fig, axes = plt.subplots(2, 3, figsize=(11, 5))

    axes = axes.ravel()

    today = datetime.date.today()
    df = pd.read_csv("analysis.tsv", sep="\t")
    df["has_github"] = df["repo"].notna()
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"].notna()]
    df["year"] = df["date"].dt.year
    # 2017 was the first year, where a repository was detected
    df = df[(2017 < df["year"]) & (df["year"] < today.year)]  # don't make ragged chart

    sns.barplot(x="year", y="has_github", data=_percentage(df, "has_github"), ax=axes[0])
    axes[0].set_ylabel("")
    axes[0].set_xlabel("")
    axes[0].set_title("Has GitHub Repo")
    _percentage_axis(axes[0])

    sns.barplot(
        x="year", y="has_issues", data=_percentage(df[df["has_github"]], "has_issues"), ax=axes[1]
    )
    axes[1].set_ylabel("")
    axes[1].set_xlabel("")
    axes[1].set_title("Has Issue Tracker")
    _percentage_axis(axes[1])

    df["package_status"] = df["pyroma_score"].map(_p_status)
    sns.barplot(
        x="year",
        y="package_status",
        data=_percentage(df[df["has_github"]], "package_status"),
        ax=axes[2],
    )
    axes[2].set_xlabel("")
    axes[2].set_ylabel("")
    axes[2].set_title("Packaged Code")
    _percentage_axis(axes[2])

    sns.barplot(
        x="year",
        y="is_blackened",
        data=_percentage(df[df["has_github"]], "is_blackened"),
        ax=axes[3],
    )
    axes[3].set_xlabel("")
    axes[3].set_ylabel("")
    axes[3].set_title("Applied Linting")
    _percentage_axis(axes[3])

    sns.barplot(
        x="year",
        y="has_installation_docs",
        data=_percentage(df[df["has_github"]], "has_installation_docs"),
        ax=axes[4],
    )
    axes[4].set_xlabel("")
    axes[4].set_ylabel("")
    axes[4].set_title("Has Installation Documentation")
    _percentage_axis(axes[4])

    df["license_status"] = df["license"].map(_license_status)
    sns.countplot(x="year", hue="license_status", data=df[df["has_github"]], ax=axes[5])
    axes[5].set_xlabel("")
    axes[5].set_ylabel("")
    axes[5].set_title("License Status")

    plt.suptitle("Analysis of J. Chem. Inf. Papers", fontsize=16)
    plt.tight_layout()
    plt.savefig("jcheminf_summary.png", dpi=300)


if __name__ == "__main__":
    main()
