import unittest

import mock
import zillow_sheets


class ZillowSheetsFillerTest(unittest.TestCase):

    def test_zillow_sheets_pulls_info_from_zillow(self):
        zillow_client = mock.Mock()
        worksheet = mock.Mock(row_count=2)
        worksheet.row_values.return_value = [
            'Address',
            'Zip',
            'Beds'
        ]

        def mock_get_addr_int(row, column):
            if column == 1:
                return 'A2'
            else:
                return 'C2'

        worksheet.get_addr_int.side_effect = mock_get_addr_int

        beds_cell = mock.Mock()
        worksheet.range.return_value = [
            mock.Mock(value='515 APPIAN WAY NE'),
            mock.Mock(value='33704'),
            beds_cell
        ]

        zillow_client.get_search_results.return_value = {
            'bedrooms': '4'
        }

        filler = zillow_sheets.ZillowSheetsFiller(worksheet, zillow_client)
        filler.fill()

        zillow_client.get_search_results.assert_called_once_with(
            '515 APPIAN WAY NE',
            '33704'
        )

        self.assertEqual(beds_cell.value, '4')
        worksheet.update_cells.assert_called_once_with(
            worksheet.range.return_value
        )


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
