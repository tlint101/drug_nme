"""
Get target-specific information. Information is assessed from the Guide to Pharmacology API
"""

import requests
import pandas as pd
from tqdm import tqdm
from typing import Union, Optional

__all__ = ["Target"]


class Target:
    def __init__(self, uniprot_id: Optional[Union[str, list]] = None):
        """
        uniprot_id: Union[str, list]
            Set the UniprotID for target query.
        """
        # set link to Guide To Pharmacology
        self.GTOPDB = 'https://www.guidetopharmacology.org/services/'
        self.uniprot = uniprot_id

    def get_data(self, uniprot_id: Optional[Union[str, list]] = None):

        # check instance variable
        if uniprot_id is None:
            uniprot_id = self.uniprot
        if self.uniprot is None and uniprot_id is None:
            raise AttributeError("You must specify a target Uniprot ID!")

        # if input is a list, loop
        if isinstance(uniprot_id, list):
            dfs = []
            for id in tqdm(uniprot_id, desc=f'Getting data'):
                target_id, target_type, target_name = self._get_target_id_by_uniprot_id(id)
                pull_data = self._get_data_by_target_id(target_id, target_type, target_name)
                dfs.append(pull_data)

            # combine dataframes
            data = pd.concat(dfs, ignore_index=True)

        else:
            target_id, target_type, target_name = self._get_target_id_by_uniprot_id(uniprot_id)
            print(f"target_id {target_id}, \ntarget_type {target_type}, \ntarget_name {target_name}")
            pull_data = self._get_data_by_target_id(target_id, target_type, target_name)
            data = pull_data

        return data

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
        else:
            target_id = target_data["targetId"]
            target_type = target_data["type"]
            target_name = target_data["abbreviation"]

        return target_id, target_type, target_name

    def _get_data_by_target_id(self, target_id, target_type, target_name):
        """
        
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
