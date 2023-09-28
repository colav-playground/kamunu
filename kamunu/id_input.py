import kamunu.kamunu_main as kamunu_main
from bson.objectid import ObjectId
import re


def id_as_input(query: str, source: str, country: str = None):

    record = {
        '_id': ObjectId(),
        'raw_name': [{
            'source': source,
            'name': query
        }],
        'names': '',
        'ids': {
            'wikidata': '',
            'ror': ''},
    }

    # Regular expression patterns for different types of inputs
    ror_url_pattern = r'^https:\/\/ror\.org\/\w+$'
    wikidata_url_pattern = r'^https:\/\/www\.wikidata\.org\/wiki\/Q\d+$'
    wikidata_id_pattern = r'^Q\d+$'
    ror_id_pattern = r'^\w+$'

    # Checking patterns
    if re.match(ror_url_pattern, query):
        record['ids']['wikidata'] = None
        record['ids']['ror'] = query
    elif re.match(wikidata_url_pattern, query):
        record['ids']['wikidata'] = query
        record['ids']['ror'] = None
    elif re.match(wikidata_id_pattern, query):
        record['ids']['wikidata'] = "https://www.wikidata.org/wiki/" + query
        record['ids']['ror'] = None
    elif re.match(ror_id_pattern, query):
        record['ids']['wikidata'] = None
        record['ids']['ror'] = "https://ror.org/" + query

    update = kamunu_main.insert_organization_record(
        record, 'records_collection', 'insert')

    return update
