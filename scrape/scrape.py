import camelot
from typing import Optional

__all__ = ["Scaper"]


class Scaper:
    def __init__(self, pdf: Optional[str] = None):
        """
        Input filepath to a pdf
        """
        self.pdf = pdf

    def scrape(self, page: Optional[str]=None, headers: Optional[list]=None, drop_last:bool=False):
        """
        Scrape table from PDF.
        :param page: Optional[str]
            PDF page containing the table to scrape.
        :param headers: Optional[list]
            A list of table headers to add to the table.
        :param drop_last: bool
            Whether to drop teh last row of the table.
        """
        tables = camelot.read_pdf(self.pdf, pages=page)
        df = tables[0].df

        if headers:
            # drop header row
            df = df[1:]
        # copy first row of string headers
        df = df[1:]  # drop header row

        # set column headers
        df.columns = headers

        # drop last row
        if drop_last:
            df = df.iloc[:-1]

        return df

if __name__ == "__main__":
    import doctest

    doctest.testmod()
