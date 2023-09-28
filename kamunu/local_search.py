from nltk.tokenize import word_tokenize
from fuzzywuzzy import fuzz, process
from bson.objectid import ObjectId
from nltk.corpus import stopwords
from unidecode import unidecode
from kamunu.db import mongodb
import pycountry
import gettext
import nltk
import re


def remove_stopwords(sentence: str):
    """
    Remove stopwords from a sentence in multiple languages and return the smallest filtered list.

    Parameters:
        sentence (str): The input sentence containing stopwords.

    Returns:
        str: The smallest filtered list after removing stopwords or the original sentence splitted.
    """
    filtered_lists = []

    len_sentence = len(sentence.split())

    # Download stopwords data for multiple languages
    nltk.download('stopwords', quiet=True, raise_on_error=True)
    nltk.download('punkt', quiet=True, raise_on_error=True)

    languages = [lang for lang in nltk.corpus.stopwords.fileids()]
    for language in languages:
        stop_words = set(stopwords.words(language))

        # Tokenize the sentence
        words = word_tokenize(sentence)

        # Filter out words that are stopwords
        filtered_sentence = [
            word for word in words if word.lower() not in stop_words]
        if len(filtered_sentence) == len_sentence:
            continue
        filtered_lists.append(filtered_sentence)

    # Find the smallest filtered list among all languages
    if filtered_lists:
        smallest_list = min(filtered_lists, key=lambda x: len(x))
        return smallest_list

    else:
        return filtered_sentence


def remove_words(word_list: list):
    filtered_words = []

    # Define a list of unwanted substrings
    unwanted_words = ["universi", "institu", "hospit",
                      "researc", "investigac", "school", "escuela"]

    # Use list comprehension to filter out words that contain any of the unwanted substrings
    for word in word_list:
        word = word.lower()
        for unwanted in unwanted_words:
            if unwanted in word:
                break
            else:
                if word not in filtered_words:
                    filtered_words.append(word)

    # filtered_words = [word.lower() for word in word_list if not any(word_ in word for word_ in words)]
    return filtered_words


def country_check(country: str):
    """
    Check if the input country name matches a country in the ISO 3166 dataset.

    Parameters:
    country (str): The name of the country to check.

    Returns:
    str: The alpha_3 code of the matching country if found, None otherwise.
    """
    response = None
    translations = {}  # Dictionary to store translations

    # Iterate through the list of alpha_2 codes to fetch translations
    for cod in [country.alpha_2 for country in pycountry.countries]:
        try:
            exp = gettext.translation(
                'iso3166', pycountry.LOCALES_DIR, languages=[cod])
            exp.install()
            translations[cod] = exp.gettext
        except FileNotFoundError:
            continue  # Skip languages without translations

    # Normalize the input country name
    normalized_country = country.lower().strip()

    # Iterate through the list of English country names
    for english_country in pycountry.countries:
        py_country = english_country.name.lower()

        # Check if the input country matches the normalized English name
        if normalized_country == py_country:
            # Retrieve the country entry by alpha_2 code
            entry = pycountry.countries.get(alpha_2=english_country.alpha_2)
            # Set the response to the alpha_3 code of the matching country
            response = entry.alpha_3
            break

    return response


def org_match(_id: str, org: str, country: str = None):
    org = re.sub(r'\s+', ' ', org.strip())
    """
    Check if the given organization (org) matches any of the names in the records collection
    associated with the given _id.

    Args:
        _id (str): The ID of the record to search in the records collection.
        org (str): The name of the organization to be matched.
        country (str): The name of the country to be matched.

    Returns:
        Optional[str]: The _id of the matching record if found, otherwise returns None.

    """

    # Retrieve the record from the records collection based on the given _id
    itms = records_collection.find_one({'_id': ObjectId(_id)})
    threshold = 95

    country_match = None
    if country:
        threshold = 85
        country_exist = itms.get('location').get('country')

        if country_exist:
            country_record = country_exist.get('country_name')

            country_match = True if country_check(
                country) == country_check(country_record) else False

    else:
        country_match = True

    # Extract raw_names and convert them to lowercase
    raw_names = itms.get('raw_name', [])
    raw = [raw_name['name'].lower() for raw_name in raw_names]
    fuzz_raw = process.extractOne(org, raw)

    # Extract wikidata labels and convert them to lowercase
    w_labels = []
    if 'wikidata' in itms.get('records', {}) and type(itms['records']['wikidata']) is dict:
        labels = itms['records']['wikidata'].get('labels', {})
        w_labels = [labels['value'].lower() for labels in labels.values()]
    fuzz_w_l = process.extractOne(org, w_labels)

    # Check if 'ror' exists in records and perform fuzzy matching with its name
    r_name = None

    if 'ror' in itms.get('records', {}):
        if itms['records']['ror']:
            r_name = itms['records']['ror'].get('name')
            fuzz_r_n_r = fuzz.ratio(org, r_name.lower() if r_name else None)
        else:
            fuzz_r_n_r = None

    # Check if any of the fuzzy matches exceed the threshold (95)
    if ((fuzz_raw and fuzz_raw[1] > threshold) or (fuzz_w_l and fuzz_w_l[1] > threshold) or (fuzz_r_n_r and fuzz_r_n_r > threshold)) and country_match:
        # print(f'{itms["_id"]}, raw_name: {fuzz_raw}, wiki_label: {fuzz_w_l}, ror_name: {fuzz_r_n_r}, {country_match}')
        return itms['_id']

    # No match found, return None
    return None


def org_search(key: str, organization: str, country: str = None):
    """
    Search for organizations in the records collection based on the given organization.

    Args:
        key (str): he key of the document where the text will be searched.
        organization (str): The name of the organization to search for.
        country (str): The name of the country to search for.

    Returns:
        Optional[str]: The _id of the matching organization's record if found, otherwise returns None.
    """

    # candidates = []

    # Remove stopwords from the organization name if it has more than two words.
    if len(organization.split()) > 2:
        filtered_org = remove_stopwords(organization)
    else:
        filtered_org = organization.split()

    # Remove specific words from the filtered organization name
    filtered_words = remove_words(filtered_org)

    for word in filtered_words:
        word = unidecode(re.sub(r'\s+', ' ', word.strip()))
        regex_pattern = re.compile(f"\\b{re.escape(word)}\\b", re.IGNORECASE)

        # Search for records with matching raw_name using regex pattern
        results = records_collection.find({key: regex_pattern})

        for result in results:
            _id = result['_id']
            # print(_id, records_collection.find_one({'_id': ObjectId(_id)})['names'])

            # Check if the organization name matches any of the records' names using org_match function
            id_found = org_match(_id, organization, country)
            if id_found:
                record = records_collection.find_one(
                    {'_id': ObjectId(_id)})
                return _id, record

    # No match found, return None
    return None


def local_search(organization: str, country: str = None):

    global records_collection
    records_collection = mongodb()[0]

    main_result = org_search(key='names.wikidata',
                             organization=organization,
                             country=country)

    if not main_result:
        main_result = org_search(key='raw_name.name',
                                 organization=organization,
                                 country=country)

    if not main_result:
        main_result = org_search(key='names.ror',
                                 organization=organization,
                                 country=country)

    if main_result:
        return main_result

    else:
        return print(f'The organization "{organization}" is not in the database.')
