"""
Get target-specific information. Information is assessed from the Guide to Pharmacology API
"""

import re
import os
import requests
import numpy as np
import pandas as pd
from tqdm import tqdm
import zipfile
from io import BytesIO
import json
from urllib.parse import urlparse

__all__ = ["Target"]


class Target:
    def __init__(self, url: str = None):
        """
        :param url: str
            Can be a URL link to the JSON file or file path to JSON file on hard disk. If None, will default to Guide to
            Pharmacology json link.
        """
        # set link to Guide To Pharmacology
        if url is None:
            self.url = "https://www.guidetopharmacology.org/services/targets"
        else:
            self.url = url

        self.data = None

    def get_target(self, target: str = "all", gene: bool = False):
        """
        :param target: str
            Specify information for a specific protein target. Can be given as a target with a name, such as HER3, or an
            HGNC gene symbol, such as CATSPER4. If HGNC gene symbol is given, the gene boolean must be set to True. If
            set to None or "all", all targets will be returned.
        :param gene: bool
            Specify if target information is an HGNC gene symbol or common name.
        """

        url = self.url

        # pull all protein targets
        if target == "all":
            return self._all_target(url)

        # pull specific protein by HGNC
        elif target is not "all" and isinstance(target, str) and gene is True:
            return self._gene_target(target, url)

        # pull specific protein by name
        elif target is not "all" and isinstance(target, str) and gene is False:
            return self._name_target(target, url)

        # error with target input
        else:
            raise ValueError(f"Target {target} not recognized!")

    def get_target_family(self):
        url = self.url

        url = url + "/families"

        json_data = _download_json_with_progress(url)

        json_df = pd.json_normalize(json_data)

        return json_df

    """
    Support functions for class List
    """
    def _all_target(self, url):
        """
        Pull all protein target information
        """
        json_data = _download_json_with_progress(url)
        json_df = pd.json_normalize(json_data)
        return json_df

    def _gene_target(self, target, url):
        """
        Pull all protein target information using HGNC gene name.
        """
        url = url + f"?geneSymbol={target}"
        json_data = _download_json_with_progress(url)
        json_df = pd.json_normalize(json_data)
        return json_df

    def _name_target(self, target, url):
        """
        Pull all protein target information using protein name.
        """
        url = url + f"?name={target}"
        json_data = _download_json_with_progress(url)
        json_df = pd.json_normalize(json_data)
        return json_df


"""
Support functions for the methods above
"""


def _download_json_with_progress(url):
    """
    Support function to download the json file and add a progress bar.
    :param url: str
        Link to download the json file.
    :return: json_data
    """

    response = requests.get(url, stream=True)

    # Get the total file size from the headers
    total_size = int(response.headers.get('content-length', 0))

    # Initialize an empty byte string to accumulate the data
    data = b''

    # Use tqdm to display the progress bar
    for chunk in tqdm(response.iter_content(1024), total=total_size // 1024, unit='KB',
                      desc='Downloading Data From Guide To Pharmacology'):
        # Accumulate the data chunks
        data += chunk

    # Decode the accumulated byte string to a JSON object
    json_guide_data = json.loads(data.decode('utf-8'))

    return json_guide_data


if __name__ == "__main__":
    import doctest

    doctest.testmod()
