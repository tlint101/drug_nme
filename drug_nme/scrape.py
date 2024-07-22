import requests
import pandas as pd
from bs4 import BeautifulSoup
import tabula

__all__ = ["Scrape"]

class Scrape:
    def __init__(self, url: str = None):
        """
        Initialize Scrape class. Input requires link to Novel Drug Approvals at FDA.
        """
        if url is None:
            self.url = 'https://www.fda.gov/drugs/development-approval-process-drugs/novel-drug-approvals-fda'
        else:
            self.url = url

    def extract(self, url: str = None):
        """
        Obtain links from CDER.
        """
        if url is None:
            url = self.url
        else:
            self.url = url

        site = requests.get(self.url)
        soup = BeautifulSoup(site.content, 'html.parser')

        # Find all links in the webpage
        # links = soup.find_all('a', href=True)

        links = soup.find_all(name = 'iframe',href=True)

        # Filter out links that end with .pdf
        pages = [link['href'] for link in links if 'download' in link['href']]

        # Handle relative URLs
        pdf_links = [link if link.startswith('http') else 'https://www.fda.gov' + link for link in pages]

        return links

    def get_pdf_links(self, url: str = None):
        """
        Obtain pdf links from CDER.
        https://www.fda.gov/drugs/nda-and-bla-approvals/new-molecular-entity-nme-drug-and-new-biologic-approvals
        :param url:
        :return:
        """
        if url is None:
            url = self.url
        else:
            self.url = url

        site = requests.get(url)
        soup = BeautifulSoup(site.content, 'html.parser')

        # Find all links in the webpage
        links = soup.find_all('a', href=True)

        # Filter out links that end with .pdf
        pages = [link['href'] for link in links if 'download' in link['href']]

        # Handle relative URLs
        pdf_links = [link if link.startswith('http') else 'https://www.fda.gov' + link for link in pages]

        return pdf_links, links

    def get_archive_pdf_links(self, url: str = None):
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

        # Obtain links to PDFs, but remove the unwanted junk link
        pdf_links = []
        unwanted_text = "Comparison of NMEs approved in 2010 to previous years"

        for link in links:
            href = link['href']
            if href.endswith('.pdf') and unwanted_text not in link.text:
                # Handle relative URLs
                pdf_link = href if href.startswith('http') else 'https://wayback.archive-it.org' + href
                pdf_links.append(pdf_link)

        if len(pdf_links) == 0:
            raise ValueError("No pdf links found! May be download or archival issues. Try again later.")
        else:
            return pdf_links

    def get_archive_tables(self, url: str = None):
        """
        Obtain tables from archived years.
        :param url:
        :return:
        """
        pass

    """
    Extracted information is given as a list of tables. This is because the table is split across multiple pages. 
    The information needs to be concat together. 

    **NOTE:** The first row table will be page headers and start dates. This is not needed and can be removed. 
    """

    def extract_table(self, url: str = None):
        """
        Convert pdf tables into pd.Dataframe
        :param url:
        :return:
        """
        # The information is organized across multiple pages. Tables will need to be generated, processed, and concated.
        try:
            tables = tabula.read_pdf(url, pages='all', lattice=True, pandas_options={"header": [0, 1]},
                                     multiple_tables=True)

            df = pd.concat(tables[1:], ignore_index=True)  # Do not use table[0] becuase it is junk
            data_df = df.replace(to_replace=r'\r', value=' ', regex=True)  # replace the '\r' string with a space

            header = data_df.iloc[0]  # Grab the first row for the header
            data_df = data_df[1:]  # drop header column
            data_df.columns = header

            # Drop row for BLA header
            data_df = data_df.drop(data_df[data_df['APPLICATION NUMBER'] == 'BLA NUMBER'].index)

            # Drop columns or rows where all elements are NaN
            data_df = data_df.dropna(axis=1, how='all')
            data_df = data_df.dropna(axis=0, how='all')

            return data_df

        # Different year may have different format. Use this exception if issues occur.
        except:
            tables = tabula.read_pdf(url, pages='all', lattice=True, pandas_options={"header": [0, 1]},
                                     multiple_tables=False)

            df = pd.concat(tables, ignore_index=True)  # Do not use table[0] becuase it is junk

            header = df.columns.tolist()  # Grab the first row for the header

            rows = []

            # Iterate through each tuple and create a row
            for header, value in header:
                rows.append({
                    'Header': header,
                    'Value': value
                })

            # Create a dataframe from the list of rows
            df = pd.DataFrame(rows)

            df = df.set_index('Header').transpose().reset_index(drop=True)

            data_df = df.replace(to_replace=r'\r', value=' ', regex=True)  # replace the '\r' string with a space


            return data_df

    def get_current_year(self, url: str = None):
        """
        Get approvals for current year.
        :param url:
        :return:
        """
        pass