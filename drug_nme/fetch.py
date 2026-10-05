"""
Script to obtain information using GuideToPharmacology API
Additional information on their API can be found here: https://www.guidetopharmacology.org/webServices.jsp
"""

import re
import os
import requests
import datetime
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm
import zipfile
import json
from io import BytesIO, StringIO
from urllib.parse import urlparse
from typing import Union
from concurrent.futures import ThreadPoolExecutor
from chembl_webresource_client.settings import Settings

# turn off client cache
Settings.Instance().CACHING = False
# set max records to 1_000
Settings.Instance().MAX_LIMIT = 1000
from chembl_webresource_client.new_client import new_client
from drug_nme.utils import (ligand_url, FDA_LANDING, DRUGS_FDA, HEADERS, COL_TO_KEEP, NAMED_COLS, DRUG_OVERRIDE,
                            KINASE_OVERRIDE, KINASE_ACTIONS, KINASE_STEMS, clean_drug_name, gtop_headers)

__all__ = ["FDADataFetcher", "PharmacologyDataFetcher", "_ChemblDataFetcher"]


class _ChemblDataFetcher:  # todo process data pulled from ChEMBL
    def __init__(self):
        # Initialize the ChEMBL molecule client
        self.chembl_client = new_client.molecule
        self.data = None

    def get_approved_drugs(self, year: int = None):
        """
        Pulls approved drugs from ChEMBL.
        If a year is provided, it only pulls drugs first approved in that year.
        """
        # In ChEMBL, max_phase = 4 means it is an approved drug
        query = self.chembl_client.filter(max_phase=4)

        # If you only want a specific year, add it to the filter
        if year:
            query = query.filter(first_approval=year)

        # 1. Ask ChEMBL for the total number of records so tqdm knows where 100% is
        total_records = len(query)

        if total_records == 0:
            print(f"No approved drugs found for year {year}.")
            return pd.DataFrame()

        # 2. Fetch the data one by one to feed the progress bar
        results = []
        for record in tqdm(query, total=total_records, desc="Downloading ChEMBL Data"):
            results.append(record)

        df = pd.DataFrame(results)

        if df.empty:
            print(f"No approved drugs found for year {year}!")
            return df

        # Filter down to the specific columns you care about
        cols_to_keep = [
            'molecule_chembl_id',
            'pref_name',  # The standard name of the drug
            'first_approval',  # The year it was approved
            'molecule_type',  # Small molecule, Antibody, Protein, etc.
            'max_phase',  # Will be 4
            'withdrawn_flag'  # True if it was pulled from the market
        ]

        # Some older drugs might be missing fields, so we only select columns that exist
        existing_cols = [col for col in cols_to_keep if col in df.columns]
        processed_df = df[existing_cols].copy()

        # Remove drugs that have been withdrawn from the market
        if 'withdrawn_flag' in processed_df.columns:
            processed_df = processed_df[processed_df['withdrawn_flag'] == False]
            processed_df = processed_df.drop(columns=['withdrawn_flag'])

        # Clean up missing names or years
        processed_df = processed_df.dropna(subset=['pref_name'])

        if 'first_approval' in processed_df.columns:
            processed_df['first_approval'] = processed_df['first_approval'].astype('Int64')

        # Rename columns to be cleaner
        processed_df = processed_df.rename(columns={
            'molecule_chembl_id': 'ChEMBL_ID',
            'pref_name': 'Name',
            'first_approval': 'Year',
            'molecule_type': 'Type'
        })

        # Keep drugs following CDER like rules
        cder_types = [
            'Small molecule',
            'Antibody',
            'Protein',
            'Oligonucleotide'
        ]
        if 'Type' in processed_df.columns:
            processed_df = processed_df[processed_df['Type'].isin(cder_types)]

        self.data = processed_df
        return self.data


#todo confirm GtP methods
class PharmacologyDataFetcher:
    def __init__(self, url: str = None, api_key: str = None):
        """
        :param url: str
            Can be a URL link to the JSON file or file path to JSON file on hard disk. If None, will default to Guide to
            Pharmacology json link.
        :param api_key: str
            A registered Guide to Pharmacology API key. If None, it is read from the GTOP_API_KEY environment variable.
        """
        self.api_key = api_key

        # set link to Guide To Pharmacology
        if url is None:
            self.url = ligand_url
        else:
            self.url = url

        self.data = None

    def get_data(self, url: str = None, agency: Union[str, list] = 'FDA'):
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
        json_data = _download_json_with_progress(url, type='guide', headers=gtop_headers(self.api_key))
        json_df = pd.DataFrame(json_data)

        extraction_tables = []

        # Apply the extract_approval_info function for each query
        for query in agency_list:
            # apply the function to each row
            extracted_series = json_df['approvalSource'].apply(lambda x: _extract_approval_info(x, query))

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

    def make_kinase_label(self, data: pd.DataFrame = None, label: str = 'Kinase', pbar: bool = True):
        """
        Relabel kinase inhibitors as Kinase. Each drug's mechanism of action is looked up on ChEMBL, and it is relabeled
        if any of its targets is classified as a kinase. Drugs that act on a kinase indirectly are listed in
        KINASE_OVERRIDE in utils.py.
        :param data: pd.DataFrame
            Input DataFrame obtained from GuidetoPharmacology.
        :param label: str
            New label. By default, it is "Kinase".
        :param pbar: bool
            Set progress bar.
        """
        if data is None:
            data = self.data

        mask = _kinase_mask(data['name'], pbar=pbar)
        data['type'] = np.where(mask, label, data['type'])

        return pd.DataFrame(data)


"""Support functions for Pharmacology data fetcher"""


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


def _extract_approval_info(text, agency_name):
    if pd.isna(text) or not str(text).strip():
        return None

    text = str(text)

    # Regular expression to match 'FDA (year)' with various noise patterns
    match = re.search(rf'\b{agency_name}\b[^()]*\(\s*(\d{{4}})\s*\)', text, re.IGNORECASE)
    if match:
        return f"{agency_name} ({match.group(1)})"

    match_alternative = re.search(rf'\b{agency_name}\b[^()]*\(\s*(\d{{4}})\s*(?:[^)]*)?\)', text, re.IGNORECASE)
    if match_alternative:
        return f"{agency_name} ({match_alternative.group(1)})"

    # Handling cases where the year might be mentioned with some variations
    match_alternative = re.search(r'\bFDA\b[^()]*\(\s*(\d{4})\s*(?:[^)]*)?\)', text, re.IGNORECASE)
    if match_alternative:
        return f"FDA ({match_alternative.group(1)})"

    # Fallback to stop at first 4 digits after agency name
    match_fallback = re.search(rf'\b{agency_name}\b.*?\b(\d{{4}})\b', text, re.IGNORECASE)
    if match_fallback:
        return f"{agency_name} ({match_fallback.group(1)})"

    return None


class FDADataFetcher:
    def __init__(self):
        # set link to CDER NME
        self.landing = FDA_LANDING
        self.new_drug_approvals = DRUGS_FDA
        self.data = None

    def get_data(self, path: str = None) -> pd.DataFrame:
        """
        Get data from the US FDA website.
        :param path: str
            Input string to get data from. If None, it will default to openFDA json link set in the __init__.
        :return:
        """

        # Check input data as url or filepath
        if path is None:
            path = self.landing

        # HEADERS to mimic a webpage
        response = requests.get(path, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # look for link to data, from the current year back
        current_year = datetime.date.today().year
        link = None
        for year in [(current_year - year) for year in range(5)]:
            pattern = f"Compilation of CDER NME and New Biologic Approvals 1985-{year}"
            link = soup.find('a', string=pattern)
            if link:
                break

        if link is None:
            raise ConnectionError(f"No 'Compilation of CDER NME and New Biologic Approvals' link found on {path}. "
                                  f"The FDA may have renamed the file.")

        # look for url
        file_url = link.get('href')
        if not file_url.startswith('http'):
            file_url = "https://www.fda.gov" + file_url

        # download file
        file_response = requests.get(file_url, headers=HEADERS)
        file_response.raise_for_status()
        df = pd.read_excel(BytesIO(file_response.content))

        # clean up col headers
        df = df[COL_TO_KEEP]
        df = df.rename(columns=NAMED_COLS)
        df = df.rename(columns={'NDA/BLA': 'NME/BLA'})

        # refactor NDA to NME
        df['NME/BLA'] = df['NME/BLA'].replace('NDA', 'NME')

        # get years after the compilation from Drugs@FDA
        max_year = df['Approval Year'].max()
        missing_years = [(current_year - year) for year in range(current_year - max_year)]
        df2 = self._scrape_fda_drug_approvals(missing_years)

        # combine dfs
        if not df2.empty:
            df = pd.concat([df2, df], ignore_index=True)
        self.data = df
        return df

    def add_types(self, data: pd.DataFrame = None, pbar: bool = True) -> pd.DataFrame:
        """
        Takes the dataframe from the get_data(), cleans the active ingredient names, and queries their data on ChEMBL
        and append a 'Type' column. ChEMBL is queried in batches, not one drug at a time.
        :param data: pd.DataFrame
            A dataframe from the get_data() function.
        :param pbar: bool
            Set progress bar.
        :return:
        """
        if data is None:
            data = self.data
        data = data.copy()
        if 'Active Ingredient' not in data.columns:
            print("Error: 'Active Ingredient' column not found in dataframe.")
            return data

        molecules = _resolve_molecules(data['Active Ingredient'].dropna().unique().tolist(), pbar=pbar)
        data['Type'] = data['Active Ingredient'].map(lambda raw: _molecule_type(raw, molecules))

        self.data = data

        return data

    def make_kinase_label(self, data: pd.DataFrame = None, label: str = 'Kinase', pbar: bool = True):
        """
        Relabel kinase inhibitors as Kinase. Each drug's mechanism of action is looked up on ChEMBL, and it is relabeled
        if any of its targets is classified as a kinase. Drugs that act on a kinase indirectly are listed in
        KINASE_OVERRIDE in utils.py.
        :param data: pd.DataFrame
            Input DataFrame pulled from get_data() function.
        :param label: str
            New label. By default, it is "Kinase".
        :param pbar: bool
            Set progress bar.
        """
        if data is None:
            data = self.data

        # Type only exists after add_types(), so start empty without it
        existing = data['Type'] if 'Type' in data.columns else None
        mask = _kinase_mask(data['Active Ingredient'], pbar=pbar)
        data['Type'] = np.where(mask, label, existing)

        return data

    @staticmethod
    def _extract_links_from_fda_drugname(table_provided):
        """
        Extract hyperlinks and drug names from the HTML table
        """

        # Initialize lists to store links and names
        links, names = [], []

        # Iterate through each row in the provided table, excluding the header (first row)
        for tr in table_provided.select("tr")[1:]:
            try:
                # Try to find the first hyperlink in the row
                trs = tr.find("a")

                # Check if trs is not None before trying to access attributes
                if trs is not None:
                    actual_link, name = trs.get('href', ''), trs.get_text()
                else:
                    actual_link, name = '', ''

            except (AttributeError, IndexError):
                # Handle cases where there's an attribute error or indexing error
                actual_link, name = '', ''

            # Append the extracted link and name to the respective lists
            links.append(actual_link)
            names.append(name)

        return links, names

    def _scrape_fda_drug_approvals(self, missing_years: list):
        """
        Scrapes FDA drug approvals data from a list of given years. Uses the site from Novel Drug Approvals for X, where
        X is the missing year.
        :param missing_years: list
            A list of years to scrape from the FDA site.
        """

        tables = []

        # get data for each year
        for year in missing_years:
            # # for debugging
            # print(f"Scraping data for year {year}")

            # url
            url = f"{self.new_drug_approvals}-{year}"
            # # for debugging
            # print(url)

            # get and check request
            response = requests.get(url, headers=HEADERS)
            if response.status_code != 200:
                print(f"Failed to retrieve content for year {year}. Status code: {response.status_code}")
                continue

            # extract table
            df_list = pd.read_html(StringIO(response.text))

            # table check
            if not df_list:
                print(f"No tables found for year {year}.")
                continue

            # process tables
            df = df_list[0]
            df.rename(columns={'Date': 'Approval Date', 'Drug  Name': 'Drug Name'}, inplace=True)

            # extract links
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')

            # check extracted table
            if table is None:
                print(f"No table found for year {year}.")
                continue  # Skip to the next iteration

            # add links and names to df
            links, names = self._extract_links_from_fda_drugname(table)
            df['links'], df['check_names'] = links, names

            # append to tables list
            tables.append(df)

        # no missing years, or none could be scraped
        if not tables:
            return pd.DataFrame()

        # process df
        df_final = pd.concat(tables, ignore_index=True)

        # drop junk and add additional column info
        df_final['Approval Date'] = pd.to_datetime(df_final['Approval Date'])
        df_final['Approval Year'] = df_final['Approval Date'].dt.year
        df_final['Approval Date'] = df_final['Approval Date'].dt.strftime('%m/%d/%Y')
        df_final['NME/BLA'] = df_final["Active Ingredient"].apply(_infer_ingredient_type)

        df_final = df_final.drop(columns=['No.', 'check_names', 'links', 'FDA-approved use on approval date*'])

        return df_final


"""
The following are support functions for the FDA and Pharmacology Classes above 
"""


def _download_json_with_progress(url, type: str = None, headers: dict = None):
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
        response = requests.get(url, stream=True, headers=headers)
        if response.status_code != 200:
            raise ConnectionError(f"Guide to Pharmacology returned status code {response.status_code}: {response.text}")

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


def _kinase_mask(names: pd.Series, pbar: bool = True):
    """
    Support function to flag small molecule kinase inhibitors in a column of drug names. ChEMBL is queried in batches,
    one request per ~400 drugs, rather than one request per drug. Mechanisms are stored against the parent molecule, so
    a salt form is resolved to its parent first. Drugs ChEMBL has no data on yet fall back to the name stem.
    """
    unique = names.dropna().unique().tolist()
    progress = tqdm(total=4, desc="Fetching Mechanisms From ChEMBL in Batches", disable=not pbar)

    molecules = {raw: row for raw, row in _resolve_molecules(unique, pbar=False).items() if row}
    progress.update()

    # mechanisms of the small molecules
    parents = {key: (row.get('molecule_hierarchy') or {}).get('parent_chembl_id') or row['molecule_chembl_id']
               for key, row in molecules.items() if row.get('molecule_type') == 'Small molecule'}
    mechanisms = {}
    fields = ('parent_molecule_chembl_id', 'target_chembl_id', 'action_type', 'mechanism_of_action')
    for row in _chembl_batch(new_client.mechanism, 'parent_molecule_chembl_id__in', set(parents.values()), fields):
        mechanisms.setdefault(row['parent_molecule_chembl_id'], []).append(row)
    progress.update()

    # targets of the inhibitory mechanisms that are classified as kinases
    target_ids = {row['target_chembl_id'] for rows in mechanisms.values() for row in rows
                  if row.get('action_type') in KINASE_ACTIONS and row.get('target_chembl_id')}
    kinase_targets = _kinase_targets(target_ids)
    progress.update()

    def is_kinase(raw):
        name = clean_drug_name(raw)
        if not name:
            return False
        if name in KINASE_OVERRIDE:
            return True

        # not in ChEMBL yet, fall back to the name stem
        if raw not in molecules:
            return name.endswith(tuple(KINASE_STEMS))

        # biologics are skipped, so antibodies against kinase receptors are not labeled
        if raw not in parents:
            return False

        # in ChEMBL but not curated yet, fall back to the name stem
        rows = mechanisms.get(parents[raw], [])
        if not rows:
            return name.endswith(tuple(KINASE_STEMS))

        # "kinase" in the mechanism text catches PI3K inhibitors, which ChEMBL classifies as a transferase. The target
        # check catches mechanisms named without the word, i.e. "Platelet-derived growth factor receptor beta inhibitor"
        return any(row.get('action_type') in KINASE_ACTIONS and
                   ('kinase' in (row.get('mechanism_of_action') or '').lower() or
                    row.get('target_chembl_id') in kinase_targets) for row in rows)

    results = {raw: is_kinase(raw) for raw in unique}
    progress.update()
    progress.close()

    return names.map(results).fillna(False).astype(bool)


def _kinase_targets(target_ids):
    """
    Support function to find which ChEMBL targets are classified as kinases. Each target's protein classification is
    walked up the tree, one batched request per level, until it reaches the root.
    """
    targets = _chembl_batch(new_client.target, 'target_chembl_id__in', target_ids,
                            ('target_chembl_id', 'target_components'))
    component_ids = {item['component_id'] for target in targets for item in target.get('target_components', [])}
    components = _chembl_batch(new_client.target_component, 'component_id__in', component_ids,
                               ('component_id', 'protein_classifications'))
    leaves = {item['component_id']: [cls['protein_classification_id'] for cls in item.get('protein_classifications', [])]
              for item in components}

    # pull the classification tree, one level per request
    parent_of, kinase_id = {}, None
    todo = {class_id for ids in leaves.values() for class_id in ids}
    seen = set(todo)
    while todo:
        for row in _chembl_batch(new_client.protein_classification, 'protein_class_id__in', todo,
                                 ('protein_class_id', 'parent_id', 'pref_name')):
            parent_of[row['protein_class_id']] = row.get('parent_id')
            if row['pref_name'] == 'Kinase':
                kinase_id = row['protein_class_id']
        todo = {parent for parent in parent_of.values() if parent and parent not in seen}
        seen |= todo

    def under_kinase(class_id):
        while class_id:
            if class_id == kinase_id:
                return True
            class_id = parent_of.get(class_id)
        return False

    return {target['target_chembl_id'] for target in targets
            if any(under_kinase(class_id) for item in target.get('target_components', [])
                   for class_id in leaves.get(item['component_id'], []))}


def _chembl_batch(resource, field: str, values, fields: tuple, size: int = 400):
    """
    Support function to query a ChEMBL resource for many values at once, i.e. pref_name__in, in chunks of 400. A failed
    chunk is skipped and printed, so its drugs fall back to the name stem rather than stopping the whole run.
    """
    values = sorted(values)
    rows = []
    for i in range(0, len(values), size):
        try:
            rows += list(resource.filter(**{field: values[i:i + size]}).only(*fields))
        except Exception as e:
            print(f"ChEMBL batch request failed for {field}: {e}")
    return rows


def _resolve_molecules(raw_names: list, pbar: bool = True):
    """
    Support function to match drug names to ChEMBL molecules, shared by add_types() and make_kinase_label() so both
    agree on which record a drug is. Names are cleaned, matched in batches on the ChEMBL preferred name (uppercase),
    and the misses are tried one at a time by synonym, then by partial name.
    :return: dict of raw name to the ChEMBL molecule record, or None if not found.
    """
    keys = {raw: (clean_drug_name(raw) or '').upper() for raw in raw_names}
    wanted = sorted({key for key in keys.values() if key})

    fields = ('molecule_chembl_id', 'pref_name', 'molecule_type', 'molecule_hierarchy')
    found = {row['pref_name']: row for row in _chembl_batch(new_client.molecule, 'pref_name__in', wanted, fields)}

    missing = [key for key in wanted if key not in found]
    with ThreadPoolExecutor(max_workers=10) as executor:
        rows = tqdm(executor.map(_find_molecule, missing), total=len(missing),
                    desc="Fetching Drug Types From ChEMBL in Batches", disable=not pbar)
        for key, row in zip(missing, rows):
            if row:
                found[key] = row

    return {raw: found.get(key) for raw, key in keys.items()}


def _find_molecule(name):
    """
    Support function to match one drug name that is not a ChEMBL preferred name, by synonym, then by partial name
    (i.e. a salt form).
    """
    fields = ('molecule_chembl_id', 'pref_name', 'molecule_type', 'molecule_hierarchy')
    try:
        for lookup in ('molecule_synonyms__molecule_synonym__iexact', 'pref_name__icontains'):
            res = new_client.molecule.filter(**{lookup: name}).only(*fields)
            if len(res) > 0:
                return res[0]
    except Exception as e:
        print(f"Error matching {name} on ChEMBL: {e}")
    return None


def _molecule_type(raw_name, molecules: dict):
    """
    Support function to get the molecule type of a drug. Manual overrides are checked on the raw name, before any
    cleaning.
    """
    if not isinstance(raw_name, str):
        return "Unknown"

    raw_key = raw_name.replace('\xa0', ' ').strip().lower()
    if raw_key in DRUG_OVERRIDE:
        return DRUG_OVERRIDE[raw_key]

    row = molecules.get(raw_name)
    if row is None:
        return "Not Found in ChEMBL"

    return row.get('molecule_type') or 'Unknown'


def _infer_ingredient_type(ingredient):
    """
    Classify active ingredient as 'BLA' or 'NME'. Will look for specific string patters in active ingredients.
    """
    text = str(ingredient).lower().strip()

    # BLA pattern
    biologic_patterns = [
        r'mab(\b|-[a-z]{4})',  # antibodies
        r'cept\b',  # fusion proteins (e.g., etanercept)
        r'cel\b',  # cell therapies (e.g., vicleucel)
        r'vec\b',  # vectors
        r'gene\b',  # gene therapies
        r'ase(\b|-[a-z]{4})',  # enzymes (e.g., hyaluronidase, asfotase)
        r'toxin\b',  # toxins
        r'globulin\b',  # blood products
    ]

    # check pattern
    for pattern in biologic_patterns:
        if re.search(pattern, text):
            return "BLA"

    # default to 'NME'
    return "NME"


if __name__ == "__main__":
    import doctest

    doctest.testmod()
