"""
Script to obtain information using GuideToPharmacology API
Additional information on their API can be found here: https://www.guidetopharmacology.org/webServices.jsp
"""

import re
import requests
import pandas as pd
from tqdm import tqdm
import zipfile
from io import BytesIO
import json


class PharmacologyDataFetcher:
    def __init__(self, url: str = None):
        """
        :param url: str
            Can be a URL link to the JSON file or file path to JSON file on hard disk. If None, will default to Guide to
            Pharmacology json link.
        """
        # set link to Guide To Pharmacology
        if url is None:
            self.url = "https://www.guidetopharmacology.org/services/ligands?type=Approved"

    def get_data(self, url: str = None, agency: str = 'all'):
        """
        Get data from Guide to Pharmacology API and convert into pd.DataFrame.
        :param url: str
            Input string to get data from. If None, it will default to Guide to Pharmacology json link set in the
            __init__.
        :return:
        """

        # Fetch data
        if url is None:
            url = self.url

        json_data = _download_json_with_progress(url, type='guide')
        json_df = pd.DataFrame(json_data)

        approval_df = json_df['approvalSource'].apply(self._split_agency, args=(agency,))

        data_df = pd.concat([json_df, approval_df], axis=1)

        # drop columns by name
        col_to_drop = ['abbreviation', 'inn', 'species', 'radioactive', 'labelled', 'immuno', 'malaria',
                       'antibacterial', 'subunitIds', 'complexIds', 'prodrugIds', 'activeDrugIds']
        processed_df = data_df.drop(columns=col_to_drop)

        return data_df

    def _split_agency(self, text, agency: str or list = 'all'):
        """
        Process string data from Guide to Pharmacology API JSON file. This will take the approvalSource column and split
        it by indicated year. By default, information will be split by FDA, EMA, Japan, and China.
        :param text:
            Guide to Pharmacology API JSON file format.
        :param agency: str
            Set the country agency of interest as output.
        :return:
        """

        # Split by parentheses
        parts = re.split(r'\(|\)', text)
        # Clean and strip parts
        parts = [part.strip(', ') for part in parts if part]

        #todo add caps for agency or cap for countries only?
        # # ensure agency is all caps
        # agency = agency.upper()
        # Full caps on agency, single cap on country if/else statement

        download_result = {}

        # Process each part
        for i in range(0, len(parts), 2):
            if i + 1 < len(parts):  # Ensure there's a year part
                entities = parts[i]
                year = parts[i + 1]

                # Default uses large markets. If not, change countries
                if agency == 'all':
                    if 'FDA' in entities:
                        download_result['FDA'] = entities
                        download_result['FDA_year'] = year
                    if 'EMA' in entities:
                        download_result['EMA'] = entities
                        download_result['EMA_year'] = year
                    if 'Japan' in entities:
                        download_result['Japan'] = entities
                        download_result['Japan_year'] = year
                    if 'China' in entities:
                        download_result['China'] = entities
                        download_result['China_year'] = year
                else:
                    if agency in entities:
                        download_result[agency] = entities
                        download_result[f'{agency}_year'] = year

        result_df = pd.Series(download_result)

        return result_df


class FDADataFetcher:
    def __init__(self, url: str = None):
        """
        :param url: str
            Can be a URL link to the JSON file or file path to JSON file on hard disk. If None, will default to openFDA
            json.zip link.
        """

        # set link to openFDA
        if url is None:
            self.url = "https://download.open.fda.gov/drug/drugsfda/drug-drugsfda-0001-of-0001.json.zip"

    def get_data(self, url: str = None):
        """

        :param url: str
            Input string to get data from. If None, it will default to openFDA json link set in the __init__.
        :return:
        """

        # Fetch data
        if url is None:
            url = self.url

        json_data = _download_json_with_progress(url, type='fda')

        # Initialize an empty list to store the flattened data
        flattened_data = []

        # Iterate through the 'results' list
        for result in json_data['results']:
            application_number = result.get('application_number')

            # Check if the application number starts with "NDA" or "BLA"
            if application_number.startswith('NDA') or application_number.startswith('BLA'):
                # Extract the sponsor name
                sponsor_name = result.get('sponsor_name')

                # Iterate through the 'products' list within each 'result'
                for product in result.get('products', []):
                    brand_name = product.get('brand_name', [])
                    active_ingredients = product.get('active_ingredients', [])

                    # Extract active ingredients names
                    for ingredient in active_ingredients:
                        ingredient_name = ingredient.get('name')

                        # Extract submission information
                        for submission in result.get('submissions', []):
                            flattened_item = {
                                'application_number': application_number,
                                'sponsor_name': sponsor_name,
                                'active_ingredient': ingredient_name,
                                'brand_name': brand_name,
                                'submission_type': submission.get('submission_type'),
                                'submission_number': submission.get('submission_number'),
                                'submission_status': submission.get('submission_status'),
                                'submission_status_date': submission.get('submission_status_date'),
                                'review_priority': submission.get('review_priority'),
                                'submission_class_code': submission.get('submission_class_code'),
                                'submission_class_code_description': submission.get('submission_class_code_description')
                            }
                            flattened_data.append(flattened_item)

        # Create a DataFrame from the flattened data
        df = pd.DataFrame(flattened_data)

        # Filter the DataFrame for new molecular entities (e.g., based on submission_class_code or description)
        nme_df = df[df['submission_class_code_description'].str.contains('New Molecular Entity', na=False, case=False)]

        # Remove duplicate rows based on 'active_ingredient'
        nme_df = nme_df.drop_duplicates(subset=['active_ingredient'])

        return nme_df


def _download_json_with_progress(url, type: str = None):
    """
    Support function to download the json file and add a progress bar.
    :param url: str
        Link to download the json file.
    :param type: str
        Describe information source. Can be "guide" (Guide to Pharmacology) or "fda" (openFDA).
    :return: json_data
    """

    if type == 'guide':
        # Send a GET request to the URL
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

    elif type == 'fda':
        # Send a GET request to the URL
        response = requests.get(url, stream=True)

        # Get the total file size from the headers
        total_size = int(response.headers.get('content-length', 0))

        # Initialize an empty byte string to accumulate the data
        data_zip = b''

        # Use tqdm to display the progress bar
        for chunk in tqdm(response.iter_content(1024), total=total_size // 1024, unit='KB',
                          desc='Downloading Data From openFDA'):
            # Accumulate the data chunks
            data_zip += chunk

        data = BytesIO(data_zip)

        # Create a ZipFile object from the downloaded content
        with zipfile.ZipFile(data) as z:
            # Extract the JSON file
            json_filename = z.namelist()[0]  # Assuming there's only one file in the zip
            with z.open(json_filename) as json_file:
                # Read and decode the JSON data
                json_data = json_file.read().decode('utf-8')
                fda_data = json.loads(json_data)

        return fda_data
