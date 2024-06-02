# FDA-NME-Scraping

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Why make this?

Obtaining a list of Novel Drug Approvals from the FDA is important for anyone interested in drug development.
Unfortunately, I have not found many good tools that does this. The FDA has the OpenFDA API, but I do not have the 
patience to figure that out (if anyone can point to me a good tutorial to help me, that would be great!).

While searching, I came across this excellent [post by Phyo Phyo PhD](https://drzinph.com/how-to-scrape-fda-drug-approval-data-with-python/). She details showing how to extract Novel 
Drug Approvals from the FDA website. It was what I was looking for and also a chance for me to dive into other python 
tools that I wanted - but have been too lazy - to try. Particularly with webscraping. That is where this repository 
comes in.

The skeleton of the scripts were lifted from the post, but have been modified to make a neat module/package. In 
particular, I have included scripts for making some figures to make the data more informative. I may consider wrapping 
this into a pip installable package in the future (ping me if you think I should?).

## Tools

Main scripts are used to scrap the website. Graphs used Matplotlib or Seaborn.

## Special Thanks

This repository was inspired by [Phyo Phyo, PhD](https://drzinph.com/about-me/).