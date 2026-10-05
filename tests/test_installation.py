import os
import pytest
import pandas as pd
from drug_nme import FDADataFetcher, PharmacologyDataFetcher, TrialsFetcher
from drug_nme.utils import clean_drug_name, gtop_headers


def test_fda_download():
    # verify FDA info
    extract = FDADataFetcher()
    df = extract.get_data()

    # confirm df
    assert isinstance(df, pd.DataFrame), "FDA download did not return a DataFrame"
    assert not df.empty, "FDA download returned an empty DataFrame"
    assert 'Active Ingredient' in df.columns, "FDA DataFrame is missing expected columns"


@pytest.mark.skipif(not os.environ.get('GTOP_API_KEY'), reason='GTOP_API_KEY is not set')
def test_gtp_download():
    # verify Guide to Pharmacology
    extract = PharmacologyDataFetcher()
    data = extract.get_data()

    # ASSERTIONS:
    assert isinstance(data, pd.DataFrame), "GTP download did not return a DataFrame"
    assert not data.empty, "GTP download returned an empty DataFrame"
    assert 'type' in data.columns, "GTP DataFrame is missing the 'type' column"


def test_trials_download():
    # verify ClinicalTrials.gov
    extract = TrialsFetcher()
    data = extract.get_data(condition='non-small cell lung cancer', phase='PHASE3', max_studies=25, pbar=False)

    # ASSERTIONS:
    assert isinstance(data, pd.DataFrame), "Trials download did not return a DataFrame"
    assert not data.empty, "Trials download returned an empty DataFrame"
    assert 'NCT ID' in data.columns, "Trials DataFrame is missing the 'NCT ID' column"

    # confirm max_studies is respected and the filter was applied
    assert len(data) <= 25, "Trials download returned more studies than requested"
    assert data['Phase'].str.contains('PHASE3').all(), "Trials DataFrame contains trials outside the phase filter"


def test_trials_by_drug():
    # verify trials can be pulled from an FDA style table of active ingredients
    extract = TrialsFetcher()
    fda = pd.DataFrame({'Active Ingredient': ['imatinib mesylate', 'tarlatamab-dlle']})
    data = extract.get_by_drug(fda, per_drug=10, pbar=False)

    # ASSERTIONS:
    assert not data.empty, "Trials by drug returned an empty DataFrame"
    assert 'Drug' in data.columns, "Trials DataFrame is missing the 'Drug' column"

    # the original FDA name is kept so the table can be joined back to the approval data
    assert set(data['Drug'].unique()) == {'imatinib mesylate', 'tarlatamab-dlle'}, "Original drug names were not kept"


def test_trials_bad_filter():
    # verify invalid enum values are rejected before a request is sent
    extract = TrialsFetcher()

    with pytest.raises(ValueError):
        extract.get_data(intervention='aspirin', phase='PHASE9')

    with pytest.raises(ValueError):
        extract.get_data(intervention='aspirin', status='NOT_A_STATUS')


def test_clean_drug_name():
    # verify FDA active ingredient names are cleaned for querying external databases
    assert clean_drug_name('tarlatamab-dlle') == 'tarlatamab'
    assert clean_drug_name('imatinib mesylate') == 'imatinib'
    assert clean_drug_name('nirmatrelvir; ritonavir (co-packaged)') == 'nirmatrelvir'
    assert clean_drug_name('calcitonin (human)') == 'calcitonin'
    assert clean_drug_name('florquinitau F 18') == 'florquinitau'
    assert clean_drug_name('technetium Tc 99m') == 'technetium'
    assert clean_drug_name(None) is None


def test_gtop_headers(monkeypatch):
    # verify the Guide to Pharmacology key is taken from the class first, then the environment
    monkeypatch.setenv('GTOP_API_KEY', 'env-key')
    assert gtop_headers('class-key') == {'GTP-API-Key': 'class-key'}
    assert gtop_headers() == {'GTP-API-Key': 'env-key'}

    monkeypatch.delenv('GTOP_API_KEY')
    with pytest.raises(ValueError):
        gtop_headers()


def test_kinase_label():
    # verify kinase inhibitors are labeled from their ChEMBL mechanism, not their name
    kinase = ['imatinib mesylate', 'tofacitinib citrate', 'alpelisib', 'sirolimus', 'netarsudil', 'zongertinib']
    other = ['vorasidenib', 'lonafarnib', 'pembrolizumab', 'trastuzumab', 'insulin icodec-abae']
    df = pd.DataFrame({'Active Ingredient': kinase + other, 'Type': 'Small molecule'})
    data = FDADataFetcher().make_kinase_label(data=df, pbar=False)

    # ASSERTIONS:
    labels = dict(zip(data['Active Ingredient'], data['Type']))
    assert all(labels[name] == 'Kinase' for name in kinase), f"Kinase inhibitors were missed: {labels}"
    assert all(labels[name] == 'Small molecule' for name in other), f"Non-kinase drugs were relabeled: {labels}"


if __name__ == "__main__":
    # This allows you to run the file directly with 'python tests/test_integration.py'
    pytest.main([__file__])
