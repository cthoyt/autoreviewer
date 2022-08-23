# autoreviewer
Scientists often do the same bad stuff. Automate giving feedback during peer review for Python packages.

Goals:

1. Given a GitHub repository, automate finding common issues such as
   - No setup.py/setup.cfg
   - No documentation
   - No reproducible installation instructions (i.e., does the README contain `pip`)
   - Uses conda for installation
   - Code does not have consistent style (i.e., there's no configuration for `black`)
2. Automate sending issues to the repository instructing how to do these things
