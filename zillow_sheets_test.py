import unittest

import mock
import zillow_sheets


class ZillowSheetsFillerTest(unittest.TestCase):

    def test_zillow_sheets_pulls_info_from_zillow(self):
        zillow_client = mock.Mock()
        filler = zillow_sheets.ZillowSheetsFiller(zillow_client)
        filler.fill()
        zillow_client.get_search_results.assert_called_once_with('data')


class ZillowClientTest(unittest.TestCase):

    def test_get_search_results_pulls_things_correctly_from_zillow(self):
        zillow_wrapper = mock.Mock()
        zillow_results_class = mock.Mock()
        client = zillow_sheets.ZillowClient(
            zillow_wrapper,
            zillow_results_class
        )

        address = 'address'
        zipcode = 'zipcode'

        client_results = client.get_search_results(address, zipcode)

        zillow_wrapper.get_deep_search_results.assert_called_once_with(
            address,
            zipcode
        )
        raw_zillow_results = (
            zillow_wrapper.get_deep_search_results.return_value
        )
        zillow_results_class.assert_called_once_with(raw_zillow_results)
        parsed_zillow_results = zillow_results_class.return_value
        self.assertEqual(
            {
                'home_type': parsed_zillow_results.home_type,
                'year_built': parsed_zillow_results.year_built,
                'bedrooms': parsed_zillow_results.bedrooms,
                'bathrooms': parsed_zillow_results.bathrooms,
                'property_size': parsed_zillow_results.property_size,
                'home_size': parsed_zillow_results.home_size,
                'zestimate_amount': parsed_zillow_results.zestimate_amount,
                'home_detail_link': parsed_zillow_results.home_detail_link,
            },
            client_results
        )


if __name__ == '__main__':
    unittest.main()
