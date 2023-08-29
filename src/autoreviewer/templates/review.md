# Reproducibility Review

Repository: [{{ repo }}]({{ url }})

## Review Items

### Does the repository contain a LICENSE file in its root?

{%- if has_license -%}

Yes.

{%- else -%}

No.

The GitHub license picker can be used to facilitate adding one by following this
link: {{ repo_url }}/community/license/new?branch={{ branch }}.

Ideal software licenses for open
source software include the MIT License, BSD family of licenses, and other licenses approved by the
[Open Source Initiative](https://opensource.org/licenses/).

A simple, informative guide for picking a license can be found
at [https://choosealicense.com](https://choosealicense.com).

More information about how GitHub detects licenses can be
found [here](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).

{%- endif -%}

### Does the repository contain a README file in its root?

{%- if has_readme -%}

Yes.

{%- else -%}

No.

No. A minimal viable README file contains:

- A short, one line description of the project
- Information on how to download, install, and run the code locally
- Brief documentation describing the single most important use case for the repository. For scientific code, this is
  ideally a one-liner in Python code, a shell script, or a command line interface (CLI) that can be used to reproduce
  the results of the analysis presented in a corresponding manuscript, use the tool presented in the manuscript, etc.
- Link to an archive on an external system like Zenodo, FigShare, or an equivalent.
- Citation information, e.g., for a pre-print then later for a peer reviewed manuscript

GitHub can be used to create a README file with https://github.com/Macau-LYXia/MVAE-DFDTnet/new/main?filename=README.md.
Repositories typically use the Markdown format, which is explained here.

{%- endif -%}

### Does the repository contain an associated public issue tracker?

### Has the repository been externally archived on Zenodo, FigShare, or equivalent that is referenced in the README?

{% if has_zenodo %}

Yes.

{%- elif not has_readme -%}

No,

This repository does not have a README, and therefore it is not possible for a reader to tell if it is archived.

{%- else -%}

No.

This repository has a README, but it does not reference Zenodo. 



If your Zenodo record iz `XYZ`, then you can use the following in your README:

{% if readme_type == "markdown" %}
```markdown
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.8109085.svg)](https://doi.org/10.5281/zenodo.8109085)
```
{% elif readme_type == "rst" %}
```rst
.. image:: https://zenodo.org/badge/DOI/10.5281/zenodo.8109085.svg
   :target: https://doi.org/10.5281/zenodo.8109085
```
{% else %}
{% endif %}

{%- endif -%}

### Does the README contain installation documentation?

### Is the code from the repository installable in a straight-forward manner?

### Does the code conform to an external linter (e.g., `black` for Python)?
