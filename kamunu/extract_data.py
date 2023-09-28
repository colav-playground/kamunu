import requests
from time import time


def extract_data(record):
    """
    Extracts and updates data from Wikidata and ROR for a given record.

    Args:
        record (dict): A dictionary containing document information.

    Returns:
        bool: True if the record was successfully updated, False otherwise.
    """

    wiki_id = None
    ror_id = None

    if record['ids']['wikidata']:
        # Extract Wikidata ID from URL
        wiki_id = record['ids']['wikidata'].split('/')[-1]
        try:
            wr = requests.get(
                f'https://www.wikidata.org/wiki/Special:EntityData/{wiki_id}.json').json()
        except Exception as e:
            raise Exception(f'An error occurred (wikidata request): {e}')

        if wr:
            # Get the name in the available language
            if 'es' in wr['entities'][wiki_id]['labels']:
                wiki_name = wr['entities'][wiki_id]['labels']['es']['value']
            elif 'en' in wr['entities'][wiki_id]['labels']:
                wiki_name = wr['entities'][wiki_id]['labels']['en']['value']
            else:
                for lang in wr['entities'][wiki_id]['labels']:
                    wiki_name = wr['entities'][wiki_id]['labels'][lang]['value']
                    break

        # Extract ROR ID from Wikidata
        wikidata = wr['entities'].get(wiki_id)
        if 'claims' in wikidata:
            P = 'P6782'
            ROR_ID = True if P in wikidata['claims'] else False
            if ROR_ID:
                ror_id = 'https://ror.org/' + \
                    wikidata['claims'][P][0]['mainsnak']['datavalue']['value']

            record['ids']['ror'] = ror_id

    else:
        wr = None
        wiki_name = None

    if record['ids']['ror'] != "ROR ID not found" and type(record['ids']['ror']) is not list and record['ids']['ror'] != "" and record['ids']['ror'] is not None:
        # Extract ROR ID from URL
        ror_id = record['ids']['ror'].split('/')[-1]
        try:
            rr = requests.get(
                f'https://api.ror.org/organizations/{ror_id}').json()
            ror_name = rr['name']
        except Exception as e:
            raise Exception(f'An error occurred (ror request): {e}')
    else:
        rr = None
        ror_name = None

    if wiki_id or ror_id:
        # Update the database record

        record_ = {
            '_id': record['_id'],
            'raw_name': record['raw_name'],
            'names': {
                'wikidata': wiki_name,
                'ror': ror_name
            },
            'ids': record['ids'],
            'categories': '',
            'location': '',
            'records': {
                'wikidata': wr['entities'].get(wiki_id) if wr else '',
                'ror': rr
            },
            'updated': [],
            'validation': {
                'verified': 0,
                'control': 0
            }
        }

        if wiki_id:
            record_["updated"].append(
                {"time": int(time()), "source": "wikidata"})
        if ror_id:
            record_["updated"].append({"time": int(time()), "source": "ror"})

        # Reset temporary variables
        wiki_name = ''
        ror_name = ''
        wr = ''
        rr = ''

        return record_

    return None
