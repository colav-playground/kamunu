import unittest
from kamunu.local_search import local_search
from kamunu.extract_data import extract_data
from kamunu.enrichment import location_enrichment, categories_enrichment
from kamunu.cat_scrapper import categories
from bson.objectid import ObjectId


class TestProject(unittest.TestCase):

    def test_local_search(self):
        # Test local_search function
        organization = "Universidad de Antioquia"
        result = local_search(organization)
        self.assertIsNotNone(result)
        _id, record = result
        self.assertIsNotNone(_id)
        self.assertIsNotNone(record)

    def test_extract_data(self):
        # Test extract_data function
        record = {
            '_id': ObjectId('64ff7070898c0b6eb8359614'),
            'raw_name': [{'source': 'test_kamunu', 'name': 'Universidad de Antioquia'}],
            'ids': {'wikidata': 'https://www.wikidata.org/wiki/Q1258413', 'ror': 'https://ror.org/03bp5hc83'}
        }
        updated_record = extract_data(record)
        self.assertIsNotNone(updated_record)

    def test_location_enrichment(self):
        # Test location_enrichment function
        record = {
            'records': {
                'wikidata': {
                    'claims': {
                        # Colombia
                        'P17': [{'mainsnak': {'datavalue': {'value': {'id': 'Q739'}}}}],
                        'P159': [{'mainsnak': {'datavalue': {'value': {'id': 'Q48278'}}},  # Medellín
                                 'qualifiers': {'P625': [{'datavalue': {'value': {'latitude': 6.26742, 'longitude': -75.5684}}}]}}]
                    }
                },
                'ror': {
                    'country': {'country_name': 'Colombia'},
                    'addresses': [{
                        'lat': 6.267417,
                        'lng': -75.568389,
                        'state': None,
                        'state_code': None,
                        'city': 'Medellín',
                        'geonames_city': {'id': 3674962,
                                          'city': 'Medellín',
                                          'geonames_admin1': {'name': 'Antioquia',
                                                              'id': 3689815,
                                                              'ascii_name': 'Antioquia'},
                                          'geonames_admin2': {'name': 'Medellín',
                                                              'id': 3674954,
                                                              'ascii_name': 'Medellin'}},
                        'country_geonames_id': 3686110}]}
            }
        }

        country, city, coordinates = location_enrichment(record)
        self.assertIsNotNone(country)
        self.assertIsNotNone(city)
        self.assertIsNotNone(coordinates)

    def test_categories_enrichment(self):
        # Test categories_enrichment function
        record = {
            'records': {
                'wikidata': {
                    'claims': {
                        # Public university
                        'P31': [{'mainsnak': {'datavalue': {'value': {'id': 'Q875538'}}}}],
                    }
                },
                'ror': {
                    'types': ['Public Organization']
                }
            }
        }
        wikidata_categories, ror_categories = categories_enrichment(record)
        self.assertIsNotNone(wikidata_categories)
        self.assertIsNotNone(ror_categories)

    def test_categories(self):
        # Test categories function
        data = "Universidad de Antioquia"
        result = categories(data)
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()
