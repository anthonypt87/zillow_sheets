import argparse

from pyzillow.pyzillow import ZillowWrapper
from pyzillow.pyzillow import GetDeepSearchResults


class ZillowSheetsFiller(object):

    def __init__(self, zillow_client):
        self._zillow_client = zillow_client

    def fill(self):
        return self._zillow_client.get_search_results(
            '515 APPIAN WAY NE',
            '33704'
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Pull data from zillow and fill in a google doc'
    )
    parser.add_argument('zillow_api_key')
    args = parser.parse_args()

    zillow_client = ZillowClient(
        ZillowWrapper(args.zillow_api_key),
        GetDeepSearchResults
    )

    print ZillowSheetsFiller(zillow_client).fill()
