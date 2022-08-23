# autoreviewer
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
