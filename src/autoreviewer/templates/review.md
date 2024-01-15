# Reproducibility Review

Below is a seven point reproducibility review prescribed by [Improving reproducibility and reusability in the
Journal of Cheminformatics](https://doi.org/10.1186/s13321-023-00730-y) of the `{{ branch }}` branch of
repository [{{ repo_url }}]({{ repo_url }}) (commit [`{{ commit[:8] }}`]({{ repo_url }}/commit/{{ commit }})),
accessed on {{ date }}.

## 1. Does the repository contain a LICENSE file in its root?

{% if license_name is none %}

No, the GitHub license picker can be used to facilitate adding one by following this
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

{% elif license_name != "Unknown" %}

Yes, {{ license_name }}.

{% else %}

Yes, **but**, it is not a standard license that GitHub can automatically recognize, meaning that it increases
the cognitive burden on potential users for the terms of use.

More information about how GitHub detects licenses can be
found [here](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).

{% endif %}

## 2. Does the repository contain a README file in its root?

{% if has_readme %}

Yes.

{% else %}

No, a minimal viable README file contains:

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

## 3. Does the repository contain an associated public issue tracker?

{% if has_issues %}
Yes.
{% else %}
No, issues have been disabled in {{ repo_url }}. This is a profoundly un-scientific choice,
as turning off the issue tracker on a repository signifies that the authors are uninterested
or unwilling to discuss the work with readers or users who might have questions.
{% endif %}

## 4. Has the repository been externally archived on Zenodo, FigShare, or equivalent that is referenced in the README?

{% if has_zenodo %}
Yes.
{% elif not has_readme %}
No,  this repository does not have a README, and therefore it is not possible for a reader to tell if it is archived.
{% else %}
No, this repository has a README, but it does not reference Zenodo. The GitHub-Zenodo integration can be
set up by following [this tutorial](https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content).

If your Zenodo record is `XYZ`, then you can use the following in your README:

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
Ideally, you switch your README.md to use either Markdown or ReStructured Text. If this is not possible,
link to the Zenodo record:

```
https://doi.org/10.5281/zenodo.XYZ
```

{% endif %}

{% endif %}

## 5. Does the README contain installation documentation?

{% if has_installation_docs %}
Yes.
{% elif not has_readme %}
No, this repository does not have a README, and therefore it is not possible for a reader to easily find installation
documentation.
{% else %} 
{% if readme_type == "markdown" %}
No, this repository has a markdown README, but it does not contain a section header entitled `# Installation`
(it's allowed to be any level deep).
{% elif readme_type == "rst" %}
No, this repository has a RST README, but it does not contain a section header entitled `Installation`
(it's allowed to be any level deep).
{% else %}
No, this repository has a text readme. Please change to a formatted README.
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

{% endif %}

## 6. Is the code from the repository installable in a straight-forward manner?

{% if has_setup %}
Yes.

### Packaging Metadata

{% if pyroma_score == 10 %}
Your packaging has all required metadata based on [`pyroma`](https://github.com/regebro/pyroma).
{% else %}
[`pyroma`](https://github.com/regebro/pyroma) rating: {{ pyroma_score }}/10

{% for failure in pyroma_failures %}
1. {{ failure }}
{% endfor %}

These results can be regenerated locally using the following shell commands:

```shell
git clone {{ repo_url }}
cd {{ name }}
python -m pip install pyroma
pyroma .
```

{% endif %}
{% else %}
No, no packing setup configuration (e.g., `setup.py`, `setup.cfg`, `pyproject.toml`) was found.
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
2. `Pipfile.lock`
3. Conda/Anaconda environment configuration

{% if root_scripts %}

### Root Scripts

The repository contains the following scripts in the root directory:

{% for root_script in root_scripts %}
- `{{ root_script }}.py`
{% endfor %}

This is bad because these scripts are not packaged. This means that users will have to manually clone
and set up the code from version control, and will be forced to run it based on where the code lives on
the local file system. These all encumber easy reproducibility.

{% if has_setup %}Instead,{% else %}After properly packaging this code,{% endif %}
they should be included inside the package and run with `python -m {{ name }}.<your submodule>`
(see [here](https://docs.python.org/3/using/cmdline.html#cmdoption-m)). One way to organize these
scripts is to put them inside a `cli` submodule, such that they can be run like this:

{% for root_script in root_scripts %}
- `python -m {{ name }}.cli.{{ root_script }}`
{% endfor %}

Another possibility is to put these Python scripts in the root of the package
(not to be confused with the root of the repository) such that they can be run like:

{% for root_script in root_scripts %}
- `python -m {{ name }}.{{ root_script }}`
{% endfor %}

{% endif %}
{% endif %}

## 7. Does the code conform to an external linter (e.g., `black` for Python)?

{% if is_blackened %}
Yes.
{% else %}
No, the repository does not conform to an external linter. This is important because there is a large
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

# Summary

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

# Colophon

This review was automatically generated with the following commands:

```shell
python -m pip install autoreviewer
python -m autoreviewer {{ repo }}
```

Please leave any feedback about the completeness and/or correctness of this review on the issue tracker for
[cthoyt/autoreviewer](https://github.com/cthoyt/autoreviewer).
