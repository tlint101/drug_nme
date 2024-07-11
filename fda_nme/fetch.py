"""
Script to obtain information using GuideToPharmacology API
Additional information on their API can be found here: https://www.guidetopharmacology.org/webServices.jsp
"""

import requests
import pandas as pd
from tqdm import tqdm
import json

class PharmacologyDataFetcher:
    def __init__(self, url: str = None):
        # set link to Guide To Pharmacology
        if url is None:
            self.url = "https://www.guidetopharmacology.org/services/ligands?type=Approved"

    def get_data(self, url: str = None):
        """

        :param url:
        :return:
        """
        # # Fetch the data
        url = self.url
        # response = requests.get(url)
        # data = response.json()
        #
        # # Convert to DataFrame
        # df = pd.DataFrame(data['ligands'])

        json_data = self._download_json_with_progress(url)
        df = pd.DataFrame(json_data)

        return df

    @staticmethod
    def _download_json_with_progress(url):
        # Send a GET request to the URL
        response = requests.get(url, stream=True)

        # Get the total file size from the headers
        total_size = int(response.headers.get('content-length', 0))

        # Initialize an empty byte string to accumulate the data
        data = b''

        # Use tqdm to display the progress bar
        for chunk in tqdm(response.iter_content(1024), total=total_size // 1024, unit='KB'):
            # Accumulate the data chunks
            data += chunk

        # Decode the accumulated byte string to a JSON object
        json_data = json.loads(data.decode('utf-8'))

        return json_data