import argparse
import json

import gspread
from oauth2client.client import SignedJwtAssertionCredentials
from pyzillow.pyzillow import ZillowWrapper
from pyzillow.pyzillow import GetDeepSearchResults


ADDRESS_COLUMN_NAME = 'Address'
ZIP_COLUMN_NAME = 'Zip'
SHEET_COL_NAME_TO_ZILLOW_NAME_MAPPING_TO_UPDATE = {
    'Beds': 'bedrooms'
}


class ZillowSheetsFiller(object):

    def __init__(self, worksheet, zillow_client):
        self._worksheet = worksheet
        self._zillow_client = zillow_client

    def fill(self):
        col_name_to_number_map = self._get_column_name_to_column_number()

        # Start at row 2 because the first row is the header row
        for row in range(2, self._worksheet.row_count + 1):
            self._update_row(row, col_name_to_number_map)

    def _update_row(self, row, col_name_to_number_map):
        cells = self._get_cells_in_row(row)
        search_results = self._get_search_results(
            cells,
            col_name_to_number_map
        )

        for column, column_number in col_name_to_number_map.iteritems():
            if column not in SHEET_COL_NAME_TO_ZILLOW_NAME_MAPPING_TO_UPDATE:
                continue
            zillow_key = SHEET_COL_NAME_TO_ZILLOW_NAME_MAPPING_TO_UPDATE[
                column
            ]
            cells[column_number].value = search_results[zillow_key]

        self._worksheet.update_cells(cells)

    def _get_cells_in_row(self, row):
        start = self._worksheet.get_addr_int(row, 1)
        end = self._worksheet.get_addr_int(row, self._worksheet.col_count)
        return self._worksheet.range('%s:%s' % (start, end))

    def _get_search_results(self, cells, col_name_to_number_map):
        return self._zillow_client.get_search_results(
            cells[col_name_to_number_map[ADDRESS_COLUMN_NAME]].value,
            cells[col_name_to_number_map[ZIP_COLUMN_NAME]].value
        )

    def _get_column_name_to_column_number(self):
        column_names = self._worksheet.row_values(1)
        return dict(
            (column_name, column_number)
            for column_number, column_name in enumerate(column_names)
        )


class ZillowClient(object):

    def __init__(self, zillow_wrapper, zillow_results_class):
        self._zillow_wrapper = zillow_wrapper
        self._zillow_results_class = zillow_results_class

    def get_search_results(self, address, zipcode):
        raw_results = self._zillow_wrapper.get_deep_search_results(
            address,
            zipcode
        )
        parsed_zillow_results = self._zillow_results_class(raw_results)
        return {
            'home_type': parsed_zillow_results.home_type,
            'year_built': parsed_zillow_results.year_built,
            'bedrooms': parsed_zillow_results.bedrooms,
            'bathrooms': parsed_zillow_results.bathrooms,
            'property_size': parsed_zillow_results.property_size,
            'home_size': parsed_zillow_results.home_size,
            'zestimate_amount': parsed_zillow_results.zestimate_amount,
            'home_detail_link': parsed_zillow_results.home_detail_link,
        }


def load_worksheet(credentials_filename, sheet_url):
    with open(credentials_filename) as cred_file:
        credentials_json = json.load(cred_file.read())
    credentials = SignedJwtAssertionCredentials(
        credentials_json['client_email'],
        credentials_json['private_key'],
        ['https://spreadsheets.google.com/feeds']
    )
    google_client = gspread.authorize(credentials)
    return google_client.open_by_url(sheet_url).sheet1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Pull data from zillow and fill in a google doc'
    )
    parser.add_argument('zillow_api_key')
    parser.add_argument('client_credentials_file')
    parser.add_argument('sheet_url')
    args = parser.parse_args()

    worksheet = load_worksheet(args.credentials_filename, args.sheet_url)

    zillow_client = ZillowClient(
        ZillowWrapper(args.zillow_api_key),
        GetDeepSearchResults
    )

    print ZillowSheetsFiller(worksheet, zillow_client).fill()
