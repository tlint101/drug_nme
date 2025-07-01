"""
Get target-specific information. Information is assessed from the Guide to Pharmacology API
"""

import requests
import pandas as pd
from tqdm import tqdm
from typing import Union, Optional
from drug_nme.utils import GtoP, uniprot_query

__all__ = ["Target"]


class Target:
    def __init__(self, uniprot_id: Optional[Union[str, list]] = None):
        """
        uniprot_id: Union[str, list]
            Set the UniprotID for target query.
        """
        # set link to Guide To Pharmacology
        self.GTOPDB = GtoP
        self.uniprot = uniprot_id

    def get_data(self, uniprot_id: Optional[Union[str, list]] = None):
        """
        Get information for a protein target by their Uniprot ID. This will give a table containing their accession,
        source database, target_id for the Guide to Pharmacology API, protein type and protein target name. The protein
        target name will match the targe gene.
        :param uniprot_id: Union[str, list]
            Get gene id for a protein by their Uniprot ID.
        """
        # check instance variable
        if uniprot_id is None:
            uniprot_id = self.uniprot
        if self.uniprot is None and uniprot_id is None:
            raise AttributeError("You must specify a target Uniprot ID!")

        # if input is a str, convert to a list
        if isinstance(uniprot_id, str):
            uniprot_id = [uniprot_id]

        dfs = []
        for uni_id in tqdm(uniprot_id, desc=f'Getting Target Data'):
            target_id, target_type, target_name = self._get_target_id_by_uniprot_id(uni_id)

            # if there is no target_name
            if target_name == "" or target_name is None:
                target_name = self.get_gene_id(uni_id, pbar=False)
                target_name = next(iter(target_name.values()))  # extract value/target_name from dict
                # print('New target name:', target_name)

            # # for troubleshooting
            # print(f"Target Name: {target_name}")

            pull_data = self._get_data_by_target_id(target_id, target_type, target_name)
            dfs.append(pull_data)

            # combine dataframes
        data = pd.concat(dfs, ignore_index=True)

        return data

    def get_gene_id(self, uniprot_id: Optional[Union[str, list]] = None, pbar: bool = False):
        """
        Get gene of protein using protein Uniprot ID.
        :param uniprot_id: Optional[Union[str, list]}
            Get gene id for a protein by their Uniprot ID.
        :param pbar: bool
            Set progress bar.
        """
        if uniprot_id is None:
            uniprot_id = self.uniprot
        if self.uniprot is None and uniprot_id is None:
            raise AttributeError("You must specify a target Uniprot ID!")

        # if input is a str, convert to a list
        if isinstance(uniprot_id, str):
            uniprot_id = [uniprot_id]

        id_dict = {}
        for uni_id in tqdm(uniprot_id, desc=f'Getting Target Gene ID', disable=not pbar):
            # query uniprot rest
            url = uniprot_query + f"{uni_id}"
            response = requests.get(url)

            # pul data
            if response.status_code == 200:
                data = response.json()
                # get gene name
                gene_name = data.get("genes", [{}])[0].get("geneName", {}).get("value", None)
                id_dict[uni_id] = gene_name
            elif response.status_code == 400:
                print(f"Error: Failed to get data for Uniprot ID: {uni_id}!!")
        return id_dict

    """Support functions"""

    def _get_target_id_by_uniprot_id(self, uniprot_id):
        """
        Pull data from Guide to Pharmacology API using Uniprot ID
        """
        # default database is UniProt, so we can query by UniProt ID like this
        url = f"{self.GTOPDB}/targets?accession={uniprot_id}"
        response = requests.get(url)
        status_code = response.status_code
        target_data = response.json()  # target_data is list

        if status_code == 200 and len(target_data) > 0:
            only_item = target_data[0]
            target_id = only_item["targetId"]
            target_type = only_item["type"]
            target_name = only_item["abbreviation"]
            return target_id, target_type, target_name

        return None

    def _get_data_by_target_id(self, target_id, target_type, target_name):
        """
        Get data from Guide to Pharmacology API and place it in a dataframe.
        """
        url = f"{self.GTOPDB}/targets/{target_id}/databaseLinks?species=Human"
        response = requests.get(url)
        status_code = response.status_code
        db_data = response.json()

        if status_code == 200:
            # convert JSON to dataframe
            df = pd.DataFrame(db_data)
            df["target_id"] = target_id
            df["protein_type"] = target_type
            df["protein_target"] = target_name
            df.drop(columns=["url", "species"], inplace=True)
            df.rename(columns={"database": "source_database"}, inplace=True)
            return df

        return None


if __name__ == "__main__":
    import doctest

    doctest.testmod()
