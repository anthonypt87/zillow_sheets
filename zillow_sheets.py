import argparse
import json
import logging

import gspread
from oauth2client.client import SignedJwtAssertionCredentials
from pyzillow.pyzillow import ZillowWrapper
from pyzillow.pyzillow import GetDeepSearchResults
from pyzillow.pyzillow import ZillowError

import config


logging.basicConfig(
    format='%(asctime)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


ADDRESS_COLUMN_NAME = 'Address'
ZIP_COLUMN_NAME = 'Zip'
SHEET_COL_NAME_TO_ZILLOW_NAME_MAPPING_TO_UPDATE = {
    'Beds': 'bedrooms',
    'Usecode': 'home_type',
    'Year Built': 'year_built',
    'Baths': 'bathrooms',
    'Living Area (SF)': 'home_size',
    'Zestimate': 'zestimate_amount',
    'Rent Estimate': 'rentzestimate_amount',
    'Tax Assessment': 'tax_value',
    'Comps': 'comparables',
}

# By default, we tart at row 2 because the first row is the header row
DEFAULT_ROW_TO_START_AT = 2

MAX_CONSECUTIVE_FAILURES = 4


class ZillowSheetsFiller(object):

    def __init__(self, worksheet, zillow_client):
        self._worksheet = worksheet
        self._zillow_client = zillow_client

    def fill(self, start_at=DEFAULT_ROW_TO_START_AT):
        col_name_to_number_map = self._get_column_name_to_column_number()

        # If we receive MAX_CONSECUTIVE_FAILURES consecutive_failures, we end
        # the script
        consecutive_failures = 0

        for row in range(start_at, self._worksheet.row_count + 1):
            logger.info('Working on row: %s' % row)
            try:
                self._update_row(row, col_name_to_number_map)
                consecutive_failures = 0
            except ZillowError as error:
                consecutive_failures += 1
                logger.warning(
                    'Had an issue processing row: %s. Got the following '
                    'error %s. Have received %s consecutive failures' % (
                        row,
                        error,
                        consecutive_failures
                    )
                )
                if consecutive_failures == MAX_CONSECUTIVE_FAILURES:
                    logger.warning(
                        'Ending the script since we received %s '
                        'consecutive_failures. Possibly ending because we '
                        'have reached the end of the file.' % (
                            MAX_CONSECUTIVE_FAILURES
                        )
                    )
                    return

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
            value = search_results[zillow_key]
            if value is None:
                cells[column_number].value = ''
            else:
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
            'bathrooms': parsed_zillow_results.bathrooms,
            'bedrooms': parsed_zillow_results.bedrooms,
            'comparables': parsed_zillow_results.comparables,
            'graph_data_link': parsed_zillow_results.graph_data_link,
            'home_detail_link': parsed_zillow_results.home_detail_link,
            'home_size': parsed_zillow_results.home_size,
            'home_type': parsed_zillow_results.home_type,
            'last_sold_date': parsed_zillow_results.last_sold_date,
            'last_sold_price': parsed_zillow_results.last_sold_price,
            'latitude': parsed_zillow_results.latitude,
            'longitude': parsed_zillow_results.longitude,
            'map_this_home_link': parsed_zillow_results.map_this_home_link,
            'property_size': parsed_zillow_results.property_size,
            'rentzestimate_amount': parsed_zillow_results.rentzestimate_amount,
            'tax_value': parsed_zillow_results.tax_value,
            'year_built': parsed_zillow_results.year_built,
            'zestimate_amount': parsed_zillow_results.zestimate_amount,
            'zestimate_last_updated': (
                parsed_zillow_results.zestimate_last_updated
            ),
            'zestimate_percentile': parsed_zillow_results.zestimate_percentile,
            'zestimate_valuation_range_high': (
                parsed_zillow_results.zestimate_valuation_range_high
            ),
            'zestimate_valuation_range_low': (
                parsed_zillow_results.zestimate_valuation_range_low
            ),
            'zestimate_value_change': (
                parsed_zillow_results.zestimate_value_change
            ),
            'zillow_id': parsed_zillow_results.zillow_id,
        }


def load_worksheet(google_credentials_file, sheet_url):
    with open(google_credentials_file) as cred_file:
        credentials_json = json.load(cred_file)
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
    parser.add_argument('--zillow-api-key', default=config.zillow_api_key)
    parser.add_argument(
        '--google-credentials-file',
        default=config.google_credentials_file
    )
    parser.add_argument('--sheet_url', default=config.sheet_url)
    parser.add_argument(
        '--start-at',
        default=DEFAULT_ROW_TO_START_AT,
        help='Row to start at',
        type=int
    )
    args = parser.parse_args()

    worksheet = load_worksheet(args.google_credentials_file, args.sheet_url)

    zillow_client = ZillowClient(
        ZillowWrapper(args.zillow_api_key),
        GetDeepSearchResults
    )

    ZillowSheetsFiller(worksheet, zillow_client).fill(args.start_at)
