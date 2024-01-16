"""Generate summary charts."""

import datetime

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def _p_status(x):
    if pd.isna(x):
        return "No Repo"
    elif x <= 0:
        return "Unpackaged"
    else:
        return "Packaged"


def _license_status(x):
    if pd.isna(x):
        return "No License"
    elif x == "Unknown":
        return "Unknown"
    else:
        return "Present"


def main():
    """Generate summary charts."""
    fig, axes = plt.subplots(2, 3, figsize=(11, 5), sharey=True)

    axes = axes.ravel()

    today = datetime.date.today()
    df = pd.read_csv("analysis.tsv", sep="\t")
    df["has_github"] = df["repo"].notna()
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"].notna()]
    df["year"] = df["date"].dt.year
    # 2017 was the first year where a repository was detected
    df = df[(2017 < df["year"]) & (df["year"] < today.year)]  # don't make ragged chart

    sns.countplot(x="year", hue="has_github", data=df, ax=axes[0])
    axes[0].set_ylabel("Count")
    axes[0].set_xlabel("")
    axes[0].set_title("Papers with Code")

    sns.countplot(x="year", hue="has_issues", data=df[df["has_github"]], ax=axes[1])
    axes[1].set_ylabel("Count")
    axes[1].set_xlabel("")
    axes[1].set_title("Issue Tracker Availability")

    df["package_status"] = df["pyroma_score"].map(_p_status)
    sns.countplot(x="year", hue="package_status", data=df[df["has_github"]], ax=axes[2])
    axes[2].set_xlabel("")
    axes[2].set_ylabel("Count")
    axes[2].set_title("Packaging Status")

    sns.countplot(x="year", hue="is_blackened", data=df[df["has_github"]], ax=axes[3])
    axes[3].set_xlabel("")
    axes[3].set_ylabel("Count")
    axes[3].set_title("Linting Status")

    sns.countplot(x="year", hue="has_installation_docs", data=df[df["has_github"]], ax=axes[4])
    axes[4].set_xlabel("")
    axes[4].set_ylabel("Count")
    axes[4].set_title("Installation Documentation Status")

    df["license_status"] = df["license"].map(_license_status)
    sns.countplot(x="year", hue="license_status", data=df[df["has_github"]], ax=axes[5])
    axes[5].set_xlabel("")
    axes[5].set_ylabel("Count")
    axes[5].set_title("License Status")

    plt.suptitle("Analysis of J. Chem. Inf. Papers", fontsize=16)
    plt.tight_layout()
    plt.savefig("jcheminf_summary.png", dpi=300)


if __name__ == "__main__":
    main()
