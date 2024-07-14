# Drug NME - Get New Molecular Entities From the FDA
[![python](https://img.shields.io/badge/Python->=3.9-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![jupyter](https://img.shields.io/badge/Jupyter-Lab-F37626.svg?style=flat&logo=Jupyter)](https://jupyterlab.readthedocs.io/en/stable)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

## What is this?
Drug approval data from the U.S. Food and Drug Administration (FDA) is a valuable resource for researchers, 
pharmaceutical professionals, and enthusiasts. Keeping track can give insight into trends from the department or what m
ay be in the next in the drug pipeline.   

This project, Drug NME, seeks to collect tools to allow users to quickly obtain this information and generate informative 
charts. Much of the code can be demoed [here](/Tutorial).

More information on the project and the hurdles I had on making the project will be forthcoming on my blog (**will be** 
**linked when project is finished**)

## Tools
Drug NME obtains information from two methods - Web Scraping the [FDA CDER website for New Drug Approvals](https://www.fda.gov/drugs/development-approval-process-drugs/novel-drug-approvals-fda)
or utilizing API from two sources - the [OpenFDA](https://open.fda.gov) API or the [Guide To Pharmacology](https://www.guidetopharmacology.org/webServices.jsp).

Two sources, FDA and Guide to Pharmacology, were used during the creation due to issues of learning the API and tools 
available. Additional information and reasoning's will be detailed in the future. 

## Why make this?
Obtaining a list of Novel Drug Approvals from the FDA is important for anyone interested in drug development.
Unfortunately, I have not found many good tools that does this. The FDA has the OpenFDA API, but it took a long time 
(and patience!) to figure it out. 

While searching, I came across this excellent [post by Phyo Phyo PhD](https://drzinph.com/how-to-scrape-fda-drug-approval-data-with-python/). Here Dr. Phyo demoed how to extract Novel 
Drug Approvals from the FDA website. It was what I was looking for and also a chance for me to dive into other python 
tools that I wanted - but have been too lazy - to try. Particularly with webscraping. That is where this repository 
comes in.

While the skeleton of the scripts were borrowed from Dr. Phyo's post, I quickly found several issues for my needs: 
- The U.S. FDA will regularly update and archive data from past years, rendering the code unusable. For example, Dr. 
- Phyo's post details information from 2023 to 2015. As of this writing, the [FDA CDER website for New Drug Approvals](https://www.fda.gov/drugs/development-approval-process-drugs/novel-drug-approvals-fda) 
is only available for years 2021-2024.
- I can be data hungry and prefer to obtain information further from earlier years if possible. 

This has led me to adapt the code for not only scraping the websites available by the FDA, but also their archival pages.
As of this writing, this project can extract information from the current year (2024) to 1999. 

Additionally, I have included basic plotting tools to quickly generate informative graphs and information that we may 
typically see for every review paper during January/February (see examples here, here, and here).

## Special Thanks
This repository was inspired by [Phyo Phyo, PhD](https://drzinph.com/about-me/).