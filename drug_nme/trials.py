"""
Script to obtain clinical trial information using the ClinicalTrials.gov API (v2)
Additional information on their API can be found here: https://clinicaltrials.gov/data-api/api
"""

import requests
import pandas as pd
from tqdm import tqdm
from typing import Union, Optional
from drug_nme.utils import (CTGOV, CTGOV_PAGE_SIZE, TRIAL_FIELDS, TRIAL_STATUS, TRIAL_PHASES, TRIAL_TYPES,
                            clean_drug_name)

__all__ = ["TrialsFetcher"]


class TrialsFetcher:
    def __init__(self, url: str = None):
        """
        :param url: str
            Base URL for the ClinicalTrials.gov API. If None, will default to the v2 API link set in utils.py.
        """
        # set link to ClinicalTrials.gov
        if url is None:
            self.url = CTGOV
        else:
            self.url = url

        self.data = None

    def get_data(self, condition: str = None, intervention: str = None, sponsor: str = None, term: str = None,
                 status: Union[str, list] = None, phase: Union[str, list] = None, study_type: str = None,
                 max_studies: int = 1000, pbar: bool = True) -> pd.DataFrame:
        """
        Search ClinicalTrials.gov and convert the matching studies into a pd.DataFrame. Search terms are combined,
        so giving both a condition and an intervention will only return trials matching both.

        :param condition: str
            Search by disease or condition, i.e. "non-small cell lung cancer".
        :param intervention: str
            Search by intervention or drug name, i.e. "pembrolizumab".
        :param sponsor: str
            Search by the sponsor or collaborator name, i.e. "Merck".
        :param term: str
            Free text search across all study fields. Also accepts an NCT ID.
        :param status: str or list
            Filter by recruitment status, i.e. "RECRUITING" or ['RECRUITING', 'COMPLETED']. Valid values are listed
            in TRIAL_STATUS in utils.py.
        :param phase: str or list
            Filter by trial phase, i.e. "PHASE3" or ['PHASE2', 'PHASE3']. Valid values are listed in TRIAL_PHASES in
            utils.py.
        :param study_type: str
            Filter by study type, i.e. "INTERVENTIONAL". Valid values are listed in TRIAL_TYPES in utils.py.
        :param max_studies: int
            Maximum number of studies to pull. Set to None to pull every match. The API caps each page at 1000
            studies, so larger requests are paginated automatically.
        :param pbar: bool
            Set progress bar.
        """

        # build query params
        params = {'fields': ','.join(TRIAL_FIELDS), 'countTotal': 'true',
                  'pageSize': min(CTGOV_PAGE_SIZE, max_studies) if max_studies else CTGOV_PAGE_SIZE}

        # search areas. Empty terms are dropped so they are not sent as blank queries
        search = {'query.cond': condition, 'query.intr': intervention, 'query.spons': sponsor, 'query.term': term}
        params.update({key: value for key, value in search.items() if value})

        # status is filtered directly, as a pipe separated list
        if status:
            status = _check_enum_input(status, TRIAL_STATUS, 'status')
            params['filter.overallStatus'] = '|'.join(status)

        # phase and study type have no dedicated filter, so they go through the advanced query syntax
        advanced = []
        if phase:
            phase = _check_enum_input(phase, TRIAL_PHASES, 'phase')
            advanced.append(f"AREA[Phase]({' OR '.join(phase)})")
        if study_type:
            study_type = _check_enum_input(study_type, TRIAL_TYPES, 'study_type')
            advanced.append(f"AREA[StudyType]({' OR '.join(study_type)})")
        if advanced:
            params['filter.advanced'] = ' AND '.join(advanced)

        # pull studies
        studies = self._paginate(params, max_studies=max_studies, pbar=pbar)

        if not studies:
            print("No trials found for the given search!")
            return pd.DataFrame()

        # flatten nested json into a table
        data = _build_table(studies)
        self.data = data

        return data

    def get_by_drug(self, drug: Union[str, list, pd.DataFrame] = None, col: str = 'Active Ingredient',
                    per_drug: int = 100, clean: bool = True, pbar: bool = True, **kwargs) -> pd.DataFrame:
        """
        Pull trials for one or more drugs and label each row with the drug that was searched. This is intended to
        chain off the FDADataFetcher, so a DataFrame from FDADataFetcher.get_data() can be passed directly and its
        active ingredients will be queried.

        :param drug: str, list, or pd.DataFrame
            Drug name, list of drug names, or a DataFrame from FDADataFetcher.get_data().
        :param col: str
            The column holding drug names, used when a pd.DataFrame is given. Defaults to 'Active Ingredient'.
        :param per_drug: int
            Maximum number of trials to pull for each drug.
        :param clean: bool
            Strip biologic suffixes, salts, and combination products from the drug name before searching. FDA active
            ingredient names rarely match ClinicalTrials.gov as written, i.e. "tarlatamab-dlle" returns 1 trial while
            "tarlatamab" returns 41. Set to False to search the names exactly as given.
        :param pbar: bool
            Set progress bar.
        :param kwargs:
            Any remaining filters accepted by get_data(), i.e. status, phase, or study_type.
        """
        if drug is None:
            raise AttributeError("You must specify a drug name, a list of drug names, or a pd.DataFrame!")

        # pull names out of a DataFrame from the FDADataFetcher
        if isinstance(drug, pd.DataFrame):
            if col not in drug.columns:
                raise KeyError(f"Column '{col}' not found in the given pd.DataFrame!")
            drug = drug[col].dropna().unique().tolist()

        # if input is a str, convert to a list
        if isinstance(drug, str):
            drug = [drug]

        dfs = []
        for name in tqdm(drug, desc='Getting Trial Data', disable=not pbar):
            # FDA names carry suffixes and salts that will not match, so search on the cleaned name
            query_name = clean_drug_name(name) if clean else name
            if not query_name:
                continue

            # the progress bar above already tracks overall progress, so the per drug bar is off
            trials = self.get_data(intervention=query_name, max_studies=per_drug, pbar=False, **kwargs)

            if trials.empty:
                continue

            # label the rows with the original name, keeping the table joinable back to the FDA data
            trials.insert(0, 'Drug', name)
            dfs.append(trials)

        if not dfs:
            print("No trials found for the given drugs!")
            return pd.DataFrame()

        data = pd.concat(dfs, ignore_index=True)
        self.data = data

        return data

    def get_study(self, nct_id: Union[str, list] = None, pbar: bool = False) -> pd.DataFrame:
        """
        Get a single trial, or a list of trials, by their NCT ID.

        :param nct_id: str or list
            The NCT ID of the trial, i.e. "NCT04041310".
        :param pbar: bool
            Set progress bar.
        """
        if nct_id is None:
            raise AttributeError("You must specify an NCT ID!")

        # if input is a str, convert to a list
        if isinstance(nct_id, str):
            nct_id = [nct_id]

        studies = []
        for study_id in tqdm(nct_id, desc='Getting Trial Data', disable=not pbar):
            url = f"{self.url.rstrip('/')}/studies/{study_id}"
            response = requests.get(url, params={'fields': ','.join(TRIAL_FIELDS)})

            if response.status_code != 200:
                print(f"Error: Failed to get data for NCT ID: {study_id}!!")
                continue

            studies.append(response.json())

        if not studies:
            return pd.DataFrame()

        data = _build_table(studies)
        self.data = data

        return data

    def _paginate(self, params: dict, max_studies: int = None, pbar: bool = True):
        """
        Support function to walk the paginated study endpoint. ClinicalTrials.gov returns a nextPageToken whenever
        more results are available, so pages are pulled until the token runs out or max_studies is reached.
        """
        url = f"{self.url.rstrip('/')}/studies"

        studies, token, progress = [], None, None
        while True:
            page_params = dict(params)
            if token:
                page_params['pageToken'] = token
                # countTotal is only valid on the first page
                page_params.pop('countTotal', None)

            response = requests.get(url, params=page_params)
            if response.status_code != 200:
                print(f"Error: ClinicalTrials.gov returned status code {response.status_code}!!")
                break

            page = response.json()
            studies.extend(page.get('studies', []))

            # set up the progress bar once the total is known
            if progress is None:
                total = page.get('totalCount', 0)
                if max_studies:
                    total = min(total, max_studies)
                progress = tqdm(total=total, desc='Downloading Data From ClinicalTrials.gov', disable=not pbar)
            progress.update(len(page.get('studies', [])))

            # stop when the requested number is reached or there are no more pages
            token = page.get('nextPageToken')
            if not token or (max_studies and len(studies) >= max_studies):
                break

        if progress is not None:
            progress.close()

        # a final page can overshoot the request, so trim the extras
        if max_studies:
            studies = studies[:max_studies]

        return studies


"""Support functions for the Trials data fetcher"""


def _build_table(studies: list):
    """
    Support function to flatten a list of studies into a pd.DataFrame and fix the numeric dtypes. Trials without a
    start date or an enrollment count hold a pd.NA, which would otherwise leave the column as an object dtype and
    break grouping and plotting. Int64 is the nullable integer, so the missing values survive the cast.
    """
    data = pd.DataFrame([_flatten_study(study) for study in studies])

    for col in ['Start Year', 'Enrollment']:
        data[col] = pd.to_numeric(data[col], errors='coerce').astype('Int64')

    return data


def _check_enum_input(value: Union[str, list], valid: list, name: str):
    """
    Conditional check that an enum filter matches the values ClinicalTrials.gov accepts. Input is uppercased, so
    'phase3' and 'PHASE3' both work.
    """
    if isinstance(value, str):
        value = [value]

    checked = [str(item).upper().strip() for item in value]

    for item in checked:
        if item not in valid:
            raise ValueError(f"'{item}' is not a valid {name}! Valid options are: {', '.join(valid)}")

    return checked


def _flatten_study(study: dict):
    """
    Support function to flatten the nested ClinicalTrials.gov json into a single row. Repeated fields, such as
    conditions and interventions, are joined into a delimited string so each trial stays one row.
    """
    protocol = study.get('protocolSection', {})

    # modules holding the fields of interest
    ident = protocol.get('identificationModule', {})
    status = protocol.get('statusModule', {})
    design = protocol.get('designModule', {})
    arms = protocol.get('armsInterventionsModule', {})
    sponsor = protocol.get('sponsorCollaboratorsModule', {})
    conditions = protocol.get('conditionsModule', {})

    # dates are nested one level deeper and can be a year, a year-month, or a full date
    start_date = status.get('startDateStruct', {}).get('date')
    completion_date = status.get('completionDateStruct', {}).get('date')

    return {
        'NCT ID': ident.get('nctId'),
        'Title': ident.get('briefTitle'),
        'Status': status.get('overallStatus'),
        'Phase': '|'.join(design.get('phases', [])) or None,
        'Study Type': design.get('studyType'),
        'Condition': '|'.join(conditions.get('conditions', [])) or None,
        'Intervention': '|'.join(item.get('name', '') for item in arms.get('interventions', [])) or None,
        'Intervention Type': '|'.join(sorted({item.get('type', '') for item in arms.get('interventions', [])})) or None,
        'Sponsor': sponsor.get('leadSponsor', {}).get('name'),
        'Enrollment': design.get('enrollmentInfo', {}).get('count'),
        'Start Date': start_date,
        'Start Year': _extract_year(start_date),
        'Completion Date': completion_date,
    }


def _extract_year(date: Optional[str]):
    """
    Support function to pull the year out of a ClinicalTrials.gov date. Dates are not a fixed width, so the leading
    four digits are taken. Returns a pd.NA if there is no date, keeping the column an Int64.
    """
    if not date:
        return pd.NA

    year = str(date)[:4]

    return int(year) if year.isdigit() else pd.NA


if __name__ == "__main__":
    import doctest

    doctest.testmod()
