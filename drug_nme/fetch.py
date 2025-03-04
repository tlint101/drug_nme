"""
Script to obtain information using GuideToPharmacology API
Additional information on their API can be found here: https://www.guidetopharmacology.org/webServices.jsp
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
from drug_nme.utils import ligand_url

__all__ = ["FDADataFetcher", "PharmacologyDataFetcher"]


class PharmacologyDataFetcher:
    def __init__(self, url: str = None):
        """
        :param url: str
            Can be a URL link to the JSON file or file path to JSON file on hard disk. If None, will default to Guide to
            Pharmacology json link.
        """
        # set link to Guide To Pharmacology
        if url is None:
            self.url = ligand_url
        else:
            self.url = url

        self.data = None

    def get_data(self, url: str = None, agency: str or list = 'FDA'):
        """
        Get data from Guide to Pharmacology API and convert into pd.DataFrame.
        :param url: str
            Input string to get data from. If None, it will default to Guide to Pharmacology json link set in the
            __init__.
        :param agency: str or list
            Input agency name to get data from. A list can be input or the name of a specific agency, i.e. ['FDA',
            'EMA'].
            Default to FDA.
        :return:
        """

        # Fetch data
        if url is None:
            url = self.url

        # Check agency input type
        if isinstance(agency, str):
            agency = [agency]

        agency_list = [_check_agency_input(x) for x in agency]

        # Download JSON data
        json_data = _download_json_with_progress(url, type='guide')
        json_df = pd.DataFrame(json_data)

        extraction_tables = []

        # Apply the extract_approval_info function for each query
        for query in agency_list:
            # apply the function to each row
            extracted_series = json_df['approvalSource'].apply(_extract_approval_info)

            # convert Series to DataFrame and rename table
            agency_df = extracted_series.to_frame()
            agency_df.columns = [f"{query}_info"]

            # split the 'approval_info' column into two columns
            agency_df[[f'{query}', 'Year']] = agency_df[f"{query}_info"].str.extract(r'([^\(]+)\s*\((\d{4})\)',
                                                                                     expand=True)

            agency_df = agency_df.drop(columns=f"{query}_info")

            # append to list
            extraction_tables.append(agency_df)

        # Combine the results with the original DataFrame
        data_df = pd.concat([json_df] + extraction_tables, axis=1)

        # drop columns by name
        col_to_drop = ['abbreviation', 'inn', 'species', 'radioactive', 'labelled', 'immuno', 'malaria',
                       'antibacterial', 'subunitIds', 'complexIds', 'prodrugIds', 'activeDrugIds']
        processed_df = data_df.drop(columns=col_to_drop).copy()

        # Replace empty strings in approvalSource with "" and drop.
        processed_df.replace("", np.nan, inplace=True)

        # For troubleshooting, remove approvalSource from list above and run or comment this during testing
        # processed_df = processed_df.dropna(subset='approvalSource')
        processed_df = processed_df.drop(columns='approvalSource')

        # if columns after col7 are all None, remove the row
        processed_df = processed_df.loc[~processed_df.iloc[:, 7:].isnull().all(axis=1)]

        # ensure columns are string or int
        processed_df['type'] = processed_df['type'].astype(str)
        processed_df['FDA'] = processed_df['FDA'].astype(str)
        processed_df['Year'] = processed_df['Year'].astype(int)
        self.data = processed_df  # set processed_df to self.df

        return pd.DataFrame(processed_df)

    def make_kinase_label(self, data: pd.DataFrame = None, label: str = 'Kinase'):
        """
        Relabel drugs as Kinase. Function currently tested for sources from GuideToPharmacology. The kinases are labeled
        based on the suffix or unique names. This can be seen under the suffix list.
        :param data: pd.DataFrame
            Input DataFrame obtained from GuidetoPharmacology.
        :param label: str
            New label. By default, it is "Kinase".
        """
        if data is None:
            data = self.data

        # string search
        suffixes = ['nib', 'tib', 'lib', 'belumosudil', 'sirolimus', 'everolimus', 'midostaurin', 'netarsudil']

        # Apply the function to the DataFrame
        data['type'] = data.apply(lambda row: _check_suffix(row, suffixes, label), axis=1)

        return pd.DataFrame(data)


"""Support functions for Pharmacology data fetcher"""


def _check_suffix(row, suffixes, replacement_string):
    if any(row['name'].endswith(suffix) for suffix in suffixes):
        return replacement_string
    return row['type']


def _check_agency_input(agency: str = None):
    """Conditional check for capitalization by agency or country"""

    if agency.lower() == 'fda':
        return 'FDA'
    elif agency.lower() == 'ema':
        return 'EMA'
    elif agency.lower() == 'uk':
        return 'UK'
    else:
        return agency.capitalize()


def _extract_approval_info(text):
    # Regular expression to match 'FDA (year)' with various noise patterns
    match = re.search(r'\bFDA\b[^()]*\(\s*(\d{4})\s*\)', text, re.IGNORECASE)
    if match:
        return f"FDA ({match.group(1)})"

    # Handling cases where the year might be mentioned with some variations
    match_alternative = re.search(r'\bFDA\b[^()]*\(\s*(\d{4})\s*(?:[^)]*)?\)', text, re.IGNORECASE)
    if match_alternative:
        return f"FDA ({match_alternative.group(1)})"

    # Additional cases where 'FDA' might be separated by other characters or words
    match_fallback = re.search(r'\bFDA\b.*\b(\d{4})\b', text, re.IGNORECASE)
    if match_fallback:
        return f"FDA ({match_fallback.group(1)})"

    return None


class FDADataFetcher:
    def __init__(self, path: str = None):
        """
        :param path: str
            Can be a URL link to the JSON file or file path to JSON file on hard disk. If None, will default to openFDA
            json.zip link.
        """

        # set link to openFDA
        if path is None:
            self.path = "https://download.open.fda.gov/drug/drugsfda/drug-drugsfda-0001-of-0001.json.zip"
        else:
            self.path = path

    def get_data(self, path: str = None):
        """

        :param path: str
            Input string to get data from. If None, it will default to openFDA json link set in the __init__.
        :return:
        """

        global url_type, json_data

        # Check input data as url or filepath
        if path is None:
            path = self.path
            url_type = _path_or_url(path=path)
        else:
            url_type = _path_or_url(path=path)

        # Check if input is a url or filepath to json file.
        if url_type == 'url':
            json_data = _download_json_with_progress(path, type='fda')
        elif url_type == 'filepath':
            json_data = _clean_fda_json(filepath=path)

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


"""
The following are support functions for the FDA and Pharmacology Classes above 
"""


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


def _path_or_url(path: str = None):
    """
    Check if input string is a filepath or a url. Output will be a string
    """
    # Check if filepath
    if os.path.isfile(path):
        return "filepath"

    # Check if url
    parsed = urlparse(path)
    if parsed.scheme in ('http', 'https', 'ftp') and bool(parsed.netloc):
        return 'url'


def _clean_fda_json(filepath: str = None):
    """
    If openFDA json is downloaded and manually used, clean the junk headers as follows.
    """
    # Read the file as bytes and decode as utf-8
    with open(filepath, 'rb') as file:
        byte_data = file.read()

    # Decode the byte string to UTF-8
    json_data = json.loads(byte_data.decode('utf-8'))

    return json_data


if __name__ == "__main__":
    import doctest

    doctest.testmod()
