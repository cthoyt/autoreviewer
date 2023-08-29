# Reproducibility Review

Below is a seven point reproducibility review prescribed by [Improving reproducibility and reusability in the
Journal of Cheminformatics](https://doi.org/10.1186/s13321-023-00730-y) of the `{{ branch }}` branch of
repository [{{ repo_url }}]({{ repo_url }}) (commit [`{{ commit[:8] }}`]({{ repo_url }}/commit/{{ commit }})),
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

{% if has_issues %}
Yes.
{% else %}
No, issues have been disabled in {{ repo_url }}. This is a profoundly un-scientific choice,
as turning off the issue tracker on a repository signifies that the authors are uninterested
or unwilling to discuss the work with readers or users who might have questions.
{% endif %}

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

{% if has_installation_docs %}
Yes.
{% elif not has_readme %}
No,

This repository does not have a README, and therefore it is not possible for a reader to easily find installation
documentation.
{% elif readme_type == "markdown" %}
No,

this repository has a README, but it does not contain a section header entitled `# Installation`
(it's allowed to be any level deep).
{% elif readme_type == "rst" %}
No,

this repository has a README, but it does not contain a section header entitled `Installation`
(it's allowed to be any level deep).
{% endif %}
Please add a section that includes information
on how the user should get the code (e.g., clone it from GitHub) and install it locally.  This might read like:

```shell
git clone {{ repo_url }}
cd {{ name }}
pip install --editable .
```

Alternatively, you can deploy your code to the [Python Package Index (PyPI)](https://pypi.org/)
and document how it can be installed with `pip install`. This might read like:

```shell
pip install {{ name.lower().replace("-", "_") }}
```

### Is the code from the repository installable in a straight-forward manner?

{% if has_setup %}
Yes.
{% else %}
No,

no packing setup configuration (e.g., `setup.py`, `setup.cfg`, `pyproject.toml`) was found.
This likely means that the project can not be installed in a straightforward, reproducible way.
Your code should be laid out in a standard structure and configured for installation with one of these
files. See the following resources:

- https://packaging.python.org/en/latest/tutorials/packaging-projects/
- https://blog.ionelmc.ro/2014/05/25/python-packaging
- https://hynek.me/articles/testing-packaging/
- https://cthoyt.com/2020/06/03/how-to-code-with-me-organization.html

Note that the following do not qualify as straightforward and reproducible because their goals are to
set up an environment in a certain way, and not to package code such that it can be distributed
and reused.

1. `requirements.txt`
2. Conda/Anaconda environment configuration
   {% endif %}

### Does the code conform to an external linter (e.g., `black` for Python)?

{% if is_blackened %}
Yes.
{% else %}
No,

the repository does not conform to an external linter. This is important because there is a large
cognitive burden for reading code that does not conform to community standards. Linters take care
of formatting code to reduce burden on readers, therefore better communicating your work to readers.

For example, [`black`](https://github.com/psf/black)
can be applied to auto-format Python code with the following:

```shell
git clone {{ repo_url }}
cd {{ name }}
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

Because the repository does not pass all seven criteria of the reproducibility review, I
recommend rejecting the associated article and inviting later resubmission after the criteria have all been
satisfied.

{% endif %}

{% if issue is not none %}
For posterity, this review has also been included on {{ repo_url }}/issues/{{ issue }}.
{% endif %}
