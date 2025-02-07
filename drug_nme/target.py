"""
Get target-specific information. Information is assessed from the Guide to Pharmacology API
"""

import re
import os
import requests
import numpy as np
import pandas as pd
from tqdm import tqdm
from typing import Union
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
        Get Target information from Guide to Pharmacology API.
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
        elif target != "all" and isinstance(target, str) and gene is True:
            return self._gene_target(target, url)

        # pull specific protein by name
        elif target != "all" and isinstance(target, str) and gene is False:
            return self._name_target(target, url)

        # error with target input
        else:
            raise ValueError(f"Target {target} not recognized!")

    def get_target_family(self):
        """
        Get protein family information from Guide to Pharmacology API.
        """
        url = self.url

        url = url + "/families"

        json_data = _download_json_with_progress(url)

        json_df = pd.json_normalize(json_data)

        return json_df

    def get_ids(self, target_id: Union[str, int] = None, species: str = "Human"):
        """
        Get IDs for a given target from the ChEMBL, Ensembl, or UniProtKB database.
        :param target_id: Union[str, int]
            The query target_id. The initial query ID must be the targetId from the Guide to pharmacology API.
        :param species: str
            Get the IDs for target based on species. Only 'Human', 'Mouse', and 'Rat' are available.
        """
        # convert str input into a list
        if isinstance(target_id, str):
            target_id = [target_id]

        # ensure species param is capitalized
        species_cap = species.capitalize()

        if species_cap not in ["Human", "Mouse", "Rat"]:
            raise ValueError(f"Only 'Human', 'Mouse', and 'Rat', or 'all' are valid species")
        elif species_cap == "All":
            species_keep = ["Human", "Mouse", "Rat"]
        else:
            species_keep = [species_cap]

        cols_to_drop = ['url']
        dbs_to_keep = ['ChEMBL Target', 'Ensembl Gene', 'UniProtKB']

        dfs = []

        # get ID numbers
        for target in tqdm(target_id, desc="Obtaining Target Ids"):
            # donwload data
            url = self.url
            url = url + f"/{target}/databaseLinks"
            json_data = _download_json_with_progress(url, progress=False)
            json_df = pd.json_normalize(json_data)

            # drop junk cols
            json_df = json_df.drop(columns=cols_to_drop)

            # keep species
            json_df = json_df[json_df['species'].isin(species_keep)]

            # keep dbs
            json_df = json_df[json_df['database'].isin(dbs_to_keep)]

            # add GtP targetID to column
            json_df['targetID'] = target

            # add dbs to list
            dfs.append(json_df)

        # combine dfs
        df = pd.concat(dfs).reset_index(drop=True)

        return df

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

    def _filter_human_protein_data(self, json_data):
        # Convert JSON to DataFrame
        df = pd.DataFrame(json_data)

        # Define filtering criteria
        valid_databases = {"ChEMBL Target", "UniProtKB", "Ensembl Gene"}

        # Filter DataFrame
        filtered_df = df[(df["species"] == "Human") & (df["database"].isin(valid_databases))]

        return filtered_df


"""
Support functions for the methods above
"""


def _download_json_with_progress(url, progress: bool = True):
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
    if progress:
        for chunk in tqdm(response.iter_content(1024), total=total_size // 1024, unit='KB',
                          desc='Downloading Data From Guide To Pharmacology'):
            # Accumulate the data chunks
            data += chunk
    else:
        for chunk in response.iter_content(1024):
            # Accumulate the data chunks
            data += chunk

    # Decode the accumulated byte string to a JSON object
    json_guide_data = json.loads(data.decode('utf-8'))

    return json_guide_data


if __name__ == "__main__":
    import doctest

    doctest.testmod()
