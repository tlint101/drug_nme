from typing import Optional
from tqdm import tqdm
import requests
import re
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
import tabula

__all__ = ["FDAScraper"]


class FDAScraper:
    def __init__(self, url: Optional[str] = None, compilation_link: Optional[str] = None,
                 latest_link: Optional[str] = None):
        """
        Initialize Scrape class. Input requires link to Novel Drug Approvals at FDA.
        :param url: Optional[str]
            Input FDA site to scrape data from.
        :param compilation_link: Optional[str]
            Input FDA link that contains a link to the FDA compilation data.
        :param latest_link: Optional[str]
            Scrap from FDA NME data from the latest (i.e. current) year.
        """

        if url is None:
            self.url = 'https://www.fda.gov/drugs/nda-and-bla-approvals/new-molecular-entity-nme-drug-and-new-biologic-approvals'
        else:
            self.url = url

        if compilation_link is None:
            self.compilation_link = 'https://www.fda.gov/drugs/drug-approvals-and-databases/compilation-cder-new-molecular-entity-nme-drug-and-new-biologic-approvals'
        else:
            self.compilation_link = compilation_link

        if latest_link is None:
            self.latest_link = 'https://www.fda.gov/drugs/development-approval-process-drugs/novel-drug-approvals-fda'
        else:
            self.latest_link = latest_link

        # Set instance variable
        self.link_dict = None

    def get_compilation(self, url: Optional[str] = None):
        """
        Get compilation of CDER NME and New Biologic Approvals. Currently, as early as 1985 and as recent as 2023.

        :param url: Optional[str]
            Link to the FDA page with Compilation Data. This is optional. By default, it should point to the following
            link:
            https://www.fda.gov/drugs/drug-approvals-and-databases/compilation-cder-new-molecular-entity-nme-drug-and-new-biologic-approvals
        """

        if url is None:
            url = self.compilation_link

        # extract link to compilation dataset
        site = requests.get(url)
        soup = BeautifulSoup(site.content, 'html.parser')

        # get all links
        links = soup.find_all('a', href=True)

        # set target link for filtering links
        compilation_pattern = 'Compilation Of CDER NME And New Biologic Approvals'
        compilation_link = None

        # search for compilation_patter in links
        for link in links:
            href = link.get('href')
            text = link.get('title', link.text).strip()  # get title or text and remove whitespace
            # if a match found, extract link and break loop
            if compilation_pattern in text:
                compilation_link = href
                break

        # add fda url to compilation link
        full_link = 'https://www.fda.gov' + compilation_link

        # download and convert link into dataframe
        fda_df = pd.read_csv(full_link)

        return fda_df

    def get_current_year(self, url: Optional[str] = None):
        """
        Get approvals for current year. Information will scrape drug approvals from a table on a website.
        :param url: Optional[str]
            Link to the FDA page with Compilation Data. This is optional. By default, it should point to the following
            link:
        https://www.fda.gov/drugs/development-approval-process-drugs/novel-drug-approvals-fda
        :return:
        """

        if url is None:
            url = self.latest_link

        site = requests.get(url)
        soup = BeautifulSoup(site.content, 'html.parser')

        # get current year
        latest_year = str(datetime.now().year)

        pattern = 'Novel Drug Approvals for ' + latest_year

        latest_link = None

        # Find all links in the webpage
        links = soup.find_all('a', href=True)

        for link in links:
            href = link.get('href')
            text = link.get('title', link.text).strip()  # get title or text and remove whitespace
            # if a match found, extract link and break loop
            if pattern in text:
                latest_link = href
                break

        # build full link for latest year
        latest_link = 'https://www.fda.gov' + latest_link

        df = _latest_nme_table(latest_link)

        return df

    def get_pdf_links(self, url: Optional[str] = None):
        """
        Obtain pdf links from CDER.
        :param url: Optional[str]
            Link to the FDA pages containing PDF links to FDA NME data. By default, it should point to the following:
            link:
            https://www.fda.gov/drugs/nda-and-bla-approvals/new-molecular-entity-nme-drug-and-new-biologic-approvals
        :return: dict
            A dictionary containing pdf links to FDA CDER NME data.
        """
        if url is None:
            url = self.url
        else:
            self.url = url

        site = requests.get(url)
        soup = BeautifulSoup(site.content, 'html.parser')

        # Find all links in the webpage
        links = soup.find_all('a', href=True)

        # Regular expression pattern to find years
        year_pattern = re.compile(r'\b\d{4}\b')

        # Initialize lists to store links and years
        pdf_links = []
        years = []

        # Get and label links by year
        for link in links:
            href = link.get('href', '')
            title = link.get('title', link.text)  # Use title if available, otherwise use the link text

            # Construct full URL
            full_link = href if href.startswith('http') else 'https://www.fda.gov' + href

            # Find years in the title
            identified_years = year_pattern.findall(title)

            # Add link and corresponding year(s)
            if identified_years:
                pdf_links.append(full_link)
                years.append(identified_years[0])

        # Generate dictionary for each pdf link and respective year
        link_year_dict = dict(zip(years, pdf_links))

        # set instance variable
        self.link_dict = link_year_dict

        return link_year_dict

    """
    Extracted information is given as a list of tables. This is because the table is split across multiple pages. 
    The information needs to be concat together. 

    **NOTE:** The first row table will be page headers and start dates. This is not needed and can be removed. 
    """

    def extract_table(self, links: dict = None, year: str = None):
        """
        Convert pdf tables into pd.Dataframe
        :param links: dict
            Input a dictionary containing the year:link for information from the U.S. FDA.
        :param year: str
            String indicating year to extract information from.
        :return:
        """
        # The information is organized across multiple pages. Tables will need to be generated, processed, and concated.

        if links is None:
            links = self.link_dict

        url = links.get(year)

        # conditional check to get obtain tables from all years
        if year == "all":
            # Empty list to hold pd.DataFrame
            tables = []

            # Extract table for all years in dictionary
            scrape = FDAScraper()
            for specific_year, table in tqdm(links.items(), desc='Extracting tables'):
                # get link for specific_year
                link = links.get(specific_year)
                data = scrape._extract_nme_table(url=link)
                tables.append(data)

            # Combine tables into a single pd.DataFrame
            table = pd.concat(tables, ignore_index=True)

            # convert the 'date' column to datetime
            # remove possible extra spaces
            table['APPROVAL DATE'] = table['APPROVAL DATE'].str.replace(r'\s+', '', regex=True)
            table['APPROVAL DATE'] = pd.to_datetime(table['APPROVAL DATE'], format='%m/%d/%Y', errors='coerce')

            return table

        # get table from specific year
        else:
            scrape_data = self._extract_nme_table(url)

            # convert the 'date' column to datetime
            scrape_data['APPROVAL DATE'] = pd.to_datetime(scrape_data['APPROVAL DATE'], format='%m/%d/%Y')

            return scrape_data

    @staticmethod
    def _extract_nme_table(url):
        """
        Support function for extracting FDA NME data from pdf link.
        """
        try:
            tables = tabula.read_pdf(url, pages='all', lattice=True, pandas_options={"header": [0, 1]},
                                     multiple_tables=True)

            df = pd.concat(tables[1:], ignore_index=True)  # Do not use table[0] because it is junk
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


"""Future code?"""


class FDAArchiveScraper:
    def __init__(self):
        self.url = None

    wayback_links = 'https://wayback.archive-it.org/7993/20170404174205/https://www.fda.gov/Drugs/DevelopmentApprovalProcess/HowDrugsareDevelopedandApproved/DrugandBiologicApprovalReports/NDAandBLAApprovalReports/ucm373420.htm'

    def _get_archive_pdf_links(self, url: str = None):
        """
        Obtain pdf links for archived years.
        :param url:
        :return:
        """

        if url is None:
            url = self.url

        site = requests.get(url)
        soup = BeautifulSoup(site.content, 'html.parser')

        # Get archive link
        # Find all links in the webpage
        links = soup.find_all('a', href=True)
        archive_link = [link['href'] for link in links if 'wayback' in link['href']]

        return archive_link

    def _wayback_pdf_links(url: str = None):
        # scrape wayback link
        site = requests.get(url)
        soup = BeautifulSoup(site.content, 'html.parser')

        # unwanted_text = "Comparison of NMEs approved in 2010 to previous years"
        pdf_links_years = []
        links = []
        years = []

        # Extract relevant data
        for a_tag in soup.find_all('a'):
            href = a_tag.get('href', '')
            if '.pdf' in href:
                text = a_tag.get_text()
                # Extract year from the text
                year = None
                for part in text.split():
                    if part.isdigit() and len(part) == 4:  # Simple year check
                        year = part
                        break
                # Add to list if year is found
                if year:
                    full_link = f"https://www.fda.gov{href}"
                    pdf_links_years.append((full_link, year))

        # Print the results
        for link, year in pdf_links_years:
            links.append(link)
            years.append(year)

        result_dict = dict(zip(years, links))

        return result_dict

    def _get_archive_tables(self, url: str = None):
        """
        Obtain tables from archived years.
        :param url:
        :return:
        """
        pass


"""
Support functions
"""


def _latest_nme_table(latest_link):
    """
    Get Novel Drug Approvals for specific year. Function typically for latest year.
    """
    # From site
    response = requests.get(latest_link)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the table on the webpage
    table = soup.find('table')

    # Extract headers
    headers = [header.text.strip() for header in table.find_all('th')]

    # Extract rows
    rows = []
    for row in table.find_all('tr')[1:]:  # Skip the header row
        cells = row.find_all('td')
        rows.append([cell.text.strip() for cell in cells])

    # Create DataFrame
    df = pd.DataFrame(rows, columns=headers)
    df = df.drop(columns=['No.'])

    return df


if __name__ == "__main__":
    import doctest

    doctest.testmod()
