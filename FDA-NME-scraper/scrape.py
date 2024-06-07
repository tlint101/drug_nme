import requests
import pandas as pd
from bs4 import BeautifulSoup


def _extract_links(table_provided):
    """
    Extract the hyperlinks and drug names from the HTML table.

    :param table_provided: HTML table containing drug information
    :return:
        links (list): List of hyperlinks
        name (list): List of drug names
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


def scrape_fda_drug_approvals(start_year: int = None, end_year: int = None):
    """
    Scrape FDA drug approvals using specified years
    :param start_year: int
        The starting year for scraping.
    :param end_year: int
        The ending year for scraping.
    :return:
        Pandas DataFrame containing drug approval information.
    """

    # Initialize an empty list to store DataFrames
    tables = []

    # Iterate through each year in the specified range
    for year in range(start_year, end_year + 1):
        print(f"Scraping data for year {year}")

        # Construct the URL for the FDA drug approvals page for the current year
        url = f'https://www.fda.gov/drugs/new-drugs-fda-cders-new-molecular-entities-and-new-therapeutic-biological-products/novel-drug-approvals-{year}'

        # Make a request to the URL and get the HTML content
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code != 200:
            print(f"Failed to retrieve content for year {year}. Status code: {response.status_code}")
            continue  # Skip to the next iteration

        # Extract the table from the HTML content
        df_list = pd.read_html(response.content)

        # Check if any tables were found
        if not df_list:
            print(f"No tables found for year {year}.")
            continue  # Skip to the next iteration

        # Use the first table found
        df = df_list[0]

        # Rename columns for consistency
        df.rename(columns={'Date': 'Approval Date', 'Drug  Name': 'Drug Name'}, inplace=True)

        # Extract links and names from the drug names in the table
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')

        # Check if the table is found
        if table is None:
            print(f"No table found for year {year}.")
            continue  # Skip to the next iteration

        links, names = _extract_links(table)

        # Add links and names as new columns in the DataFrame
        df['links'], df['check_names'] = links, names

        # Append the DataFrame to the list of tables
        tables.append(df)

    df_final = pd.concat(tables, ignore_index=True)
    return df_final
