# Drug NME - Get New Molecular Entities From the FDA
[![Drug NME Versions](https://img.shields.io/pypi/v/drug_nme.svg?label=Drug_NME&color=blue)](https://pypi.org/project/drug-nme/)
[![Python Versions](https://img.shields.io/pypi/pyversions/drug_nme?style=flat&logo=python&logoColor=white)](https://pypi.org/project/drug-nme/)
[![jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626.svg?style=flat&logo=Jupyter)](https://jupyterlab.readthedocs.io/en/stable)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

## What is this?
Drug approval data from the U.S. Food and Drug Administration (FDA) is a valuable resource for researchers, 
pharmaceutical professionals, and enthusiasts. Keeping track can give insight into trends from the department or what m
ay be in the next in the drug pipeline.   

This project, Drug NME, seeks to collect tools to allow users to quickly obtain this information and generate informative 
charts. Much of the code can be demoed [here](/Tutorials).

## Tools
Drug NME obtains information from two methods - Web Scraping the [FDA CDER website for New Drug Approvals](https://www.fda.gov/drugs/development-approval-process-drugs/novel-drug-approvals-fda)
or utilizing API from two sources - the [OpenFDA](https://open.fda.gov) or the [Guide To Pharmacology](https://www.guidetopharmacology.org/webServices.jsp).

## Installation
The drug_nme can be installed as follows:
```
pip install drug_nme
```

and can be updated using:
```
pip install drug_nme -U
```

## To-Dos
- [ ] Add module to get chemical name and numbering
- [ ] Add plot options for FDA sources
- [ ] Update tutorials
- [ ] Add additional plot styles

## Special Thanks
This repository was inspired from a blog post by [Phyo Phyo Kyaw Zin, PhD](https://drzinph.com/how-to-scrape-fda-drug-approval-data-with-python/). 

