import requests
import time


def Qsearch(id_: str):
    try:
        time.sleep(1)
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

    # Si los datos no se extraen de ROR, se extraen de wikidata
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

        # Administrative territorial entity
        elif 'P131' in claims:
            P131 = claims['P131'][0]['mainsnak']['datavalue']['value']['id']
            city_data = Qsearch(P131)
            city = {'city': city_data[0],
                    'geonames_ids': city_data[1]}

            return country, city, coordinates

    return None, None, None
