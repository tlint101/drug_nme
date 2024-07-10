import requests
import pandas as pd
from bs4 import BeautifulSoup
import tabula


class Extract:
    def __init__(self, url):
        self.url = url

    def get_pdf_links(self, url: str = None):
        """
        Obtain pdf links from CDER.
        https://www.fda.gov/drugs/nda-and-bla-approvals/new-molecular-entity-nme-drug-and-new-biologic-approvals
        :param url:
        :return:
        """
        if url is None:
            url = self.url

        site = requests.get(self.url)
        soup = BeautifulSoup(site.content, 'html.parser')

        # Find all links in the webpage
        links = soup.find_all('a', href=True)

        # Filter out links that end with .pdf
        pages = [link['href'] for link in links if 'download' in link['href']]

        # Handle relative URLs
        pdf_links = [link if link.startswith('http') else 'https://www.fda.gov' + link for link in pages]

        return pdf_links

    def get_archive_links(self, url: str = None):
        """
        Obtain pdf links for archived years.
        :param url:
        :return:
        """

        if url is None:
            url = self.url

        site = requests.get(url)
        soup = BeautifulSoup(site.content, 'html.parser')

        # Find all links in the webpage
        links = soup.find_all('a', href=True)

        # Filter out links that end with .pdf
        pages = [link['href'] for link in links if 'download' in link['href']]

        # Handle relative URLs
        pdf_links = [link if link.startswith('http') else 'https://wayback.archive-it.org' + link for link in pages]

        return pdf_links

    def extract_table(self, url: str = None):
        """
        Convert pdf tables into pd.Dataframe
        :param url:
        :return:
        """
        # The information is organized across multiple pages. Tables will need to be generated, processed, and concated.
        tables = tabula.read_pdf(url, pages='all', lattice=True, pandas_options={"header": [0, 1]},
                                 multiple_tables=True)

        df = pd.concat(tables[1:], ignore_index=True)  # Do not use table[0] becuase it is junk
        data_df = df.replace(to_replace=r'\r', value=' ', regex=True)  # replace the '\r' string with a space

        header = data_df.iloc[0]  # Grab the first row for the header
        data_df = data_df[1:]  # drop header column
        data_df.columns = header

        # Drop row for BLA header
        data_df = data_df.drop(data_df[data_df['APPLICATION NUMBER'] == 'BLA NUMBER'].index)

        data_df = data_df.dropna()

        return data_df