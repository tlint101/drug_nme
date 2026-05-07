import pytest
import pandas as pd
from drug_nme import FDADataFetcher, PharmacologyDataFetcher


def test_fda_download():
    # verify FDA info
    extract = FDADataFetcher()
    df = extract.get_data()

    # confirm df
    assert isinstance(df, pd.DataFrame), "FDA download did not return a DataFrame"
    assert not df.empty, "FDA download returned an empty DataFrame"
    assert 'Active Ingredient' in df.columns, "FDA DataFrame is missing expected columns"


def test_gtp_download():
    # verify Guide to Pharmacology
    extract = PharmacologyDataFetcher()
    data = extract.get_data()

    # ASSERTIONS:
    assert isinstance(data, pd.DataFrame), "GTP download did not return a DataFrame"
    assert not data.empty, "GTP download returned an empty DataFrame"
    assert 'type' in data.columns, "GTP DataFrame is missing the 'type' column"


if __name__ == "__main__":
    # This allows you to run the file directly with 'python tests/test_integration.py'
    pytest.main([__file__])
