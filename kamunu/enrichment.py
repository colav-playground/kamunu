from fuzzywuzzy import process, fuzz
from kamunu.utils import wiki_ids
import requests
import time


def Qsearch(id_: str):
    try:
        time.sleep(0.05)
        r = requests.get(
            f'https://www.wikidata.org/wiki/Special:EntityData/{id_}.json').json()
    except Exception as e:
        return e

    if r:
        data_name = r['entities'][id_]['labels']['en']['value']
        data_code = r['entities'][id_]['claims']['P1566'][0]['mainsnak'][
            'datavalue']['value'] if 'P1566' in r['entities'][id_]['claims'] else None
        return data_name, data_code


def location_enrichment(record):
    country = None
    city = None
    country_name = None
    coordinates = None

    # Revisar si hay datos de ROR
    ror = record['records']['ror']
    if ror and 'country' in ror:
        # Extraer el país desde ROR
        country_name = ror['country']['country_name']

        # Revisar si hay addresses en los datos de ROR
        if 'addresses' in ror:
            city_name = ror['addresses'][0]['city']
            geonames_city = [ror['addresses'][0]['geonames_city']['id'],
                             ror['addresses'][0]['geonames_city']['geonames_admin1']['id'] if ror[
                                 'addresses'][0]['geonames_city']['geonames_admin1'] else None,
                             ror['addresses'][0]['geonames_city']['geonames_admin2']['id'] if ror['addresses'][0]['geonames_city']['geonames_admin2'] else None]

            city = {'city': city_name,
                    'geonames_ids': geonames_city}

            country_code = ror['addresses'][0]['country_geonames_id']

            coordinates = {
                'latitude': ror['addresses'][0]['lat'], 'longitude': ror['addresses'][0]['lng']}

            country = {'country_name': country_name,
                       'geonames_id': country_code}

            if country['country_name'] and city['city'] and coordinates['latitude']:
                return country, city, coordinates

    # If the data are not found in ROR, an attempt is made to extract them from wikidata.
    wikidata = record['records']['wikidata']
    if wikidata and 'claims' in wikidata:
        claims = record['records']['wikidata']['claims']

        # Country
        if 'P17' in claims:
            P17 = claims['P17'][0]['mainsnak']['datavalue']['value']['id']
            country_data = Qsearch(P17)
            country = {
                'country_name': country_data[0], 'country_code': country_data[1]}

        # Location of an organization's head office - headquarters (incluyen coordenadas)
        if 'P159' in claims and 'qualifiers' in claims['P159'][0]:
            latitude = claims['P159'][0]['qualifiers']['P625'][0]['datavalue'][
                'value']['latitude'] if 'P625' in claims['P159'][0]['qualifiers'] else 0
            longitude = claims['P159'][0]['qualifiers']['P625'][0]['datavalue'][
                'value']['longitude'] if 'P625' in claims['P159'][0]['qualifiers'] else 0
            coordinates = {'latitude': latitude, 'longitude': longitude}
            P159 = claims['P159'][0]['mainsnak']['datavalue']['value']['id']
            city_data = Qsearch(P159)
            city = {'city': city_data[0],
                    'geonames_ids': city_data[1]}
            return country, city, coordinates

        elif 'P36' in claims and 'datavalue' in claims['P36'][0]['mainsnak']:
            P36 = claims['P36'][0]['mainsnak']['datavalue']['value']['id']
            city_data = Qsearch(P36)
            city = {'city': city_data[0],
                    'geonames_ids': city_data[1]}

        if 'P625' in claims and 'datavalue' in claims['P625'][0]['mainsnak']:
            latitude = claims['P625'][0]['mainsnak']['datavalue']['value']['latitude']
            longitude = claims['P625'][0]['mainsnak']['datavalue']['value']['longitude']
            coordinates = {
                'latitude': latitude,
                'longitude': longitude}

        # Administrative territorial entity
        if not city and 'P131' in claims:
            P131 = claims['P131'][0]['mainsnak']['datavalue']['value']['id']
            city_data = Qsearch(P131)
            city = {'city': city_data[0],
                    'geonames_ids': city_data[1]}

    return country, city, coordinates


def categories_enrichment(record):
    types_words = ['nonprofit', 'forprofit', 'private', 'public',
                   'mixed', 'hybrid', 'non-profit', 'for-profit', 'non-for-profit']
    claims = None
    wikidata_categories = None
    ror_categories = None

    wikidata_ids = wiki_ids.wiki_types()
    if record['records']['wikidata'] and 'claims' in record['records']['wikidata']:
        if 'P31' in record['records']['wikidata']['claims']:
            claims = [claim for claim in record['records']
                      ['wikidata']['claims']['P31']]

    try:
        cat_ids = [cid['mainsnak']['datavalue']['value']['id']
                   for cid in claims]
    except Exception:
        cat_ids = None

    if cat_ids:
        wikidata_categories = []

        for wid in wikidata_ids:
            wiki_cat = wid[0]
            if wiki_cat in cat_ids:
                wikidata_categories.append(wid[2])

        if not wikidata_categories:
            for cat_id in cat_ids:
                id_search = Qsearch(cat_id)
                if id_search:
                    label = id_search[0]
                    for word in types_words:
                        fu = fuzz.token_set_ratio(word, label)
                        if fu == 100:
                            wikidata_categories.append(word)

    if record['records']['ror'] and record['records']['ror']['types']:
        ror_types = record['records']['ror']['types']

        ror_categories = []

        for ror_type in ror_types:
            fuzzy = process.extractOne(ror_type.lower(), types_words)
            if fuzzy and fuzzy[1] >= 80:
                ror_categories.append(fuzzy[0])

        if not ror_categories:
            ror_categories = None

    return wikidata_categories, ror_categories
