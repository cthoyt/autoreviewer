# Reproducibility Review of [{{ repo }}]({{ repo_url }})

Below is applied the seven point reproducibility review prescribed by [Improving reproducibility and reusability in the
Journal of Cheminformatics](https://doi.org/10.1186/s13321-023-00730-y) to the `{{ branch }}` branch of
repository [{{ repo_url }}]({{ repo_url }}) (commit [`{{ commit }}`]({{ repo_url }}/commit/{{ commit }})),
accessed on {{ date }}.

## Criteria

### Does the repository contain a LICENSE file in its root?

{% if has_license %}

Yes.

{% else %}

No,

the GitHub license picker can be used to facilitate adding one by following this
link: [{{ repo_url }}/community/license/new?branch={{ branch }}]({{ repo_url }}/community/license/new?branch={{
branch }}).

Ideal software licenses for open
source software include the [MIT License](https://opensource.org/license/mit/),
[BSD-3 Clause License](https://opensource.org/license/bsd-3-clause/),
and other licenses approved by the
[Open Source Initiative](https://opensource.org/licenses/).
A simple, informative guide for picking a license can be found
at [https://choosealicense.com](https://choosealicense.com).

More information about how GitHub detects licenses can be
found [here](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).

{% endif %}

### Does the repository contain a README file in its root?

{% if has_readme %}

Yes.

{% else %}

No,

a minimal viable README file contains:

- A short, one line description of the project
- Information on how to download, install, and run the code locally
- Brief documentation describing the single most important use case for the repository. For scientific code, this is
  ideally a one-liner in Python code, a shell script, or a command line interface (CLI) that can be used to reproduce
  the results of the analysis presented in a corresponding manuscript, use the tool presented in the manuscript, etc.
- Link to an archive on an external system like Zenodo, FigShare, or an equivalent.
- Citation information, e.g., for a pre-print then later for a peer reviewed manuscript

GitHub can be used to create a README file with
[{{ repo_url }}/new/main?filename=README.md]({{ repo_url }}/new/main?filename=README.md).
Repositories typically use the Markdown format, which is
explained [here](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax).

{% endif %}

### Does the repository contain an associated public issue tracker?

### Has the repository been externally archived on Zenodo, FigShare, or equivalent that is referenced in the README?

{% if has_zenodo %}

Yes.

{% elif not has_readme %}

No,

This repository does not have a README, and therefore it is not possible for a reader to tell if it is archived.

{% else %}

No,

this repository has a README, but it does not reference Zenodo. If your Zenodo record iz `XYZ`, then you can use the
following in your README:

{% if readme_type == "markdown" %}

```markdown
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XYZ.svg)](https://doi.org/10.5281/zenodo.XYZ)
```

{% elif readme_type == "rst" %}

```rst
.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.XYZ.svg
   :target: https://doi.org/10.5281/zenodo.XYZ
```

{% else %}
Ideally, you switch your README.md to use either Markdown or Restructured Text. If this is not possible,
link to the Zenodo record:

```
https://doi.org/10.5281/zenodo.XYZ
```

{% endif %}

{% endif %}

### Does the README contain installation documentation?

### Is the code from the repository installable in a straight-forward manner?

### Does the code conform to an external linter (e.g., `black` for Python)?

{% if is_blackened %}
Yes.
{% else %}
No,

The repository does not conform to an external linter. This is important because there is a large
cognitive burden for reading code that does not conform to community standards. Linters take care
of formatting code to reduce burden on readers, therefore better communicating your work to readers.

For example, [`black`](https://github.com/psf/black) 
can be applied to auto-format Python code with the following:

```shell
git clone {{ repo_url }} tmp
cd tmp
python -m pip install black
black .
git commit -m "Blacken code"
git push
```
{% endif %}

## Summary

{% if passes %}

This repository passes all seven criteria. This is not the end of your journey towards reproducibility,
but it is a good start. Nice job so far!

{% else %}

Scientific integrity depends on enabling others to understand the methodology (written as computer code) and reproduce
the results generated from it. This reproducibility review reflects steps towards this goal that may be new for some
researchers, but will ultimately raise standards across our community and lead to better science.

Because the work presented in this article does not pass all seven criteria of the reproducibility review, I
recommend rejecting the article and inviting later resubmission following addressing the points.

{% endif %}

For posterity, this review has also been included on {{ repo_url }}/issues/1.
