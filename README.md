<h1 align="center">
  AutoReviewer
</h1>

<p align="center">
    <a href="https://github.com/cthoyt/autoreviewer/actions?query=workflow%3ATests">
        <img alt="Tests" src="https://github.com/cthoyt/autoreviewer/workflows/Tests/badge.svg" />
    </a>
    <a href="https://pypi.org/project/autoreviewer">
        <img alt="PyPI" src="https://img.shields.io/pypi/v/autoreviewer" />
    </a>
    <a href="https://pypi.org/project/autoreviewer">
        <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/autoreviewer" />
    </a>
    <a href="https://github.com/cthoyt/autoreviewer/blob/main/LICENSE">
        <img alt="PyPI - License" src="https://img.shields.io/pypi/l/autoreviewer" />
    </a>
    <a href='https://autoreviewer.readthedocs.io/en/latest/?badge=latest'>
        <img src='https://readthedocs.org/projects/autoreviewer/badge/?version=latest' alt='Documentation Status' />
    </a>
    <a href="https://codecov.io/gh/cthoyt/autoreviewer/branch/main">
        <img src="https://codecov.io/gh/cthoyt/autoreviewer/branch/main/graph/badge.svg" alt="Codecov status" />
    </a>  
    <a href="https://github.com/cthoyt/cookiecutter-python-package">
        <img alt="Cookiecutter template from @cthoyt" src="https://img.shields.io/badge/Cookiecutter-snekpack-blue" /> 
    </a>
    <a href='https://github.com/psf/black'>
        <img src='https://img.shields.io/badge/code%20style-black-000000.svg' alt='Code style: black' />
    </a>
    <a href="https://github.com/cthoyt/autoreviewer/blob/main/.github/CODE_OF_CONDUCT.md">
        <img src="https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg" alt="Contributor Covenant"/>
    </a>
</p>

Scientists often do the same bad stuff. Automate giving feedback during peer review for Python packages.

Goals:

1. Given a GitHub repository, automate finding common issues such as
    - No setup.py/setup.cfg/pyproject.toml
    - No zenodo archive linked from the README
    - Non-standard code layout (`src/` or bust)
    - Files contain hard-coded file paths
    - No documentation (search README for link to readthedocs)
    - Package name doesn't match github repository name
    - No reproducible installation instructions (i.e., does the README contain `pip`)
    - Uses conda for installation
    - Code does not have consistent style (i.e., there's no configuration for `black`)
    - `pyroma` doesn't pass 10/10
    - missing `LICENSE` file
    - missing `CITATION.cff` file
2. Automate sending issues to the repository instructing how to do these things
    - Use deterministic titles for all issues to avoid duplicates / make idempotent
    - Create and edit "epic" issue that links others

Example Reviews:

- https://github.com/fanavarro/lexical-analysis-obo-foundry/issues/4
- https://github.com/krishnanlab/PecanPy/issues/12
- https://github.com/huihui1126/drugSim-pathway/issues/14

Want to collaborate? What do you expect out of Python packages? Let me know in the comments. I envision this being sort
of modular so people can contribute their own checks.

Desired interface:

Run on the command line with:

```shell
$ autoreviewer https://github.com/rs-costa/sbml2hyb
```

## J. Chem. Inf. Analysis

![](/src/autoreviewer/jcheminf/jcheminf_summary.png)

There's a submodule `autoreviewer.jcheminf` that has utilities for scraping the paper list
from the Journal of Cheminformatics, getting their ePub files,
extracting GitHub references from the availability statements, running autoreview on each,
then making the following summary with `python -m autoreviewer.jcheminf`.

## 🚀 Installation

The most recent release can be installed from
[PyPI](https://pypi.org/project/autoreviewer/) with:

```bash
$ pip install autoreviewer
```

The most recent code and data can be installed directly from GitHub with:

```bash
$ pip install git+https://github.com/cthoyt/autoreviewer.git
```

You'll also need to make sure [`pandoc`](https://pandoc.org/) is installed.
The best way to do this is `brew install pandoc` on macOS.

## 👐 Contributing

Contributions, whether filing an issue, making a pull request, or forking, are appreciated. See
[CONTRIBUTING.md](https://github.com/cthoyt/autoreviewer/blob/master/.github/CONTRIBUTING.md) for more information on
getting involved.

## 👋 Attribution

### ⚖️ License

The code in this package is licensed under the MIT License.

### 🍪 Cookiecutter

This package was created with [@audreyfeldroy](https://github.com/audreyfeldroy)'s
[cookiecutter](https://github.com/cookiecutter/cookiecutter) package using [@cthoyt](https://github.com/cthoyt)'s
[cookiecutter-snekpack](https://github.com/cthoyt/cookiecutter-snekpack) template.

## 🛠️ For Developers

<details>
  <summary>See developer instructions</summary>


The final section of the README is for if you want to get involved by making a code contribution.

### Development Installation

To install in development mode, use the following:

```bash
$ git clone git+https://github.com/cthoyt/autoreviewer.git
$ cd autoreviewer
$ pip install -e .
```

### 🥼 Testing

After cloning the repository and installing `tox` with `pip install tox`, the unit tests in the `tests/` folder can be
run reproducibly with:

```shell
$ tox
```

Additionally, these tests are automatically re-run with each commit in
a [GitHub Action](https://github.com/cthoyt/autoreviewer/actions?query=workflow%3ATests).

### 📖 Building the Documentation

The documentation can be built locally using the following:

```shell
$ git clone git+https://github.com/cthoyt/autoreviewer.git
$ cd autoreviewer
$ tox -e docs
$ open docs/build/html/index.html
``` 

The documentation automatically installs the package as well as the `docs`
extra specified in the [`setup.cfg`](setup.cfg). `sphinx` plugins
like `texext` can be added there. Additionally, they need to be added to the
`extensions` list in [`docs/source/conf.py`](docs/source/conf.py).

### 📦 Making a Release

After installing the package in development mode and installing
`tox` with `pip install tox`, the commands for making a new release are contained within the `finish` environment
in `tox.ini`. Run the following from the shell:

```shell
$ tox -e finish
```

This script does the following:

1. Uses [Bump2Version](https://github.com/c4urself/bump2version) to switch the version number in the `setup.cfg`,
   `src/autoreviewer/version.py`, and [`docs/source/conf.py`](docs/source/conf.py) to not have the `-dev` suffix
2. Packages the code in both a tar archive and a wheel using [`build`](https://github.com/pypa/build)
3. Uploads to PyPI using [`twine`](https://github.com/pypa/twine). Be sure to have a `.pypirc` file configured to avoid
   the need for manual input at this
   step
4. Push to GitHub. You'll need to make a release going with the commit where the version was bumped.
5. Bump the version to the next patch. If you made big changes and want to bump the version by minor, you can
   use `tox -e bumpversion minor` after.

</details>
