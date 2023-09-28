from kamunu.enrichment import location_enrichment, categories_enrichment
from kamunu.local_search import local_search
from kamunu.extract_data import extract_data
from kamunu.cat_scrapper import categories
from bson.objectid import ObjectId
from nltk.corpus import stopwords
from kamunu.Kamunu import Kamunu
from kamunu.db import mongodb
import nltk
import json
import time

records_collection, not_inserted = mongodb()
nltk.download('stopwords')


def insert_organization_record(record, collection, function):
    """
    Insert or update an organization record in the MongoDB collection.

    Args:
        record (dict): The record to be inserted or updated.
        collection (str): The target collection name ('records_collection' or 'not_inserted').
        function (str): The action to perform ('insert' or 'update').

    Returns:
        bool: True if the operation is successful, False otherwise.
    """

    if function == 'insert':
        if collection == 'records_collection':

            insert = records_collection.insert_one(record)
            if insert:
                print(
                    f"'{record['raw_name'][0]['name']}' inserted in the DB at ObjectId({record['_id']})")
                update = extract_data(record)
                if update:
                    _id = (record['_id'])
                    location_update = location_enrichment(update)
                    if location_update:
                        location = {
                            'country': location_update[0],
                            'city': location_update[1],
                            'coordinates': location_update[2]
                        }
                        update['location'] = location

                    nameskesy = update['names'].keys()
                    if 'wikidata' in nameskesy:
                        categories_key = categories(
                            update['names']['wikidata'])
                    else:
                        categories_key = categories(update['names']['ror'])

                    if categories_key:
                        update['categories'] = categories_key

                    wikidata_categories, ror_categories = categories_enrichment(
                        update)
                    if wikidata_categories or ror_categories:
                        update['categories']['wikidata'] = wikidata_categories
                        update['categories']['ror'] = ror_categories

                    record_update = records_collection.find_one_and_update(
                        {'_id': _id},
                        {"$set": update})

                    if record_update:
                        print("The record was successfully updated.")
                        return record_update
                    else:
                        print("The record was NOT updated.")
                else:
                    print("The record data was NOT extracted.")

            time.sleep(0.02)
            return record

        elif collection == 'not_inserted':
            print(f"'{record['organization']}' NOT inserted in the DB")
            insert = not_inserted.insert_one(record)
            return record

    elif function == 'update':
        if collection == 'records_collection':
            _id = record['_id']
            update = record['new_name']

            document = records_collection.find_one({'_id': _id})
            raw_name = document.get('raw_name', [])
            if any(item == update for item in raw_name):
                return False
            else:
                record_update = records_collection.update_one(
                    {'_id': _id}, {'$push': {'raw_name': update}})
                if record_update:
                    return True


def single_organization(organization_name, source, country=None):
    """
    Insert a single organization record into the database.

    Args:
        organization_name (str): The name of the organization.
        source (str): Source of the organization data

    Returns:
        bool: True if the operation is successful, False otherwise.
    """
    print(f'a single_organization ingresó el país {country}')

    def input_evaluation(organization_name: str):

        excluded_words = ['organ', 'comp', 'companhia', 'empr', 'socie', 'societa', 'corp', 'corp', 'coop', 'limit', 'gmbh', 'sarl', 'inc', 'ltd',
                          'group', 'grupo', 'gruppo', 'association', 'asocia', 'univ', 'coll', 'inst', 'acad', 'school', 'escue', 'depar']

        input_ = organization_name.lower().strip().split()
        len_input = len(input_)
        for word in excluded_words:
            if len_input <= 1 and word in input_[0]:
                return None

        if len_input == 2:
            stopwords_list = stopwords.words()
            for term in input_:
                if term in stopwords_list:
                    return None

        return organization_name

    organization_name = input_evaluation(organization_name)

    if organization_name is None:
        return None

    local_record = local_search(organization_name, country)

    if local_record:
        full_record = local_record[1]
        print(
            f"'{organization_name}' is already in the DB at ObjectId({local_record[0]}) with IDs: {full_record['ids']}")
        _id = ObjectId(local_record[0])
        new_name = {'source': source, 'name': organization_name}
        record = {'_id': _id, 'new_name': new_name}
        inserted = insert_organization_record(
            record, 'records_collection', 'update')
        if inserted:
            print(
                "The new name and the data source were added to the corresponding record")
        else:
            print("The new name and data source already exist in the record.")
        return full_record
    else:
        kamunu, search_results = Kamunu(organization_name)
        print(search_results)

        if kamunu and (kamunu['wikidata'] or kamunu['ror']):
            record = {
                '_id': ObjectId(),
                'raw_name': [{
                    'source': source,
                    'name': organization_name
                }],
                'names': '',
                'ids': kamunu,
            }
            inserted = insert_organization_record(
                record, 'records_collection', 'insert')
            if inserted:
                return inserted
        else:
            record = {
                '_id': ObjectId(),
                'source': source,
                'organization': organization_name
            }
            inserted = insert_organization_record(
                record, 'not_inserted', 'insert')
            return inserted


def multiple_organizations(json_file_path):
    """
    Insert or update multiple organization records from a JSON file.

    Args:
        json_file_path (str): The path to the JSON file containing organization data.

    Returns:
        bool: True if the operation is successful, False otherwise.
    """

    def load_data(file_path):
        """
        Load JSON data from a file.

        Args:
            file_path (str): The path to the JSON file.

        Returns:
            dict: The loaded JSON data as a dictionary.
        """
        try:
            with open(file_path, encoding="utf8") as f:
                data = json.load(f)
            return data

        except Exception as e:
            return e

    data = load_data(json_file_path)
    if data and data['organizations'] and data['source']:
        source = data['source']
        rds = 0

        for organization_name in data['organizations']:
            local_record = local_search(organization_name)

            if local_record:
                print(
                    f"'{organization_name}' is already in the DB at ObjectId({local_record[0]}) with IDs: {local_record[1]}")
                _id = ObjectId(local_record[0])
                new_name = {'source': source, 'name': organization_name}
                record = {'_id': _id, 'new_name': new_name}
                inserted = insert_organization_record(
                    record, 'records_collection', 'update')
                if inserted:
                    print(
                        "The new name and the data source were added to the corresponding record")
                else:
                    print("The new name and data source already exist in the record.")
                time.sleep(0.02)
                return True
            else:
                kamunu, search_results = Kamunu(organization_name)[0]
                # print(kamunu)

                if kamunu and (kamunu['wikidata'] or kamunu['ror']):
                    record = {
                        '_id': ObjectId(),
                        'raw_name': [{
                            'source': source,
                            'name': organization_name
                        }],
                        'names': '',
                        'ids': kamunu,
                    }
                    inserted = insert_organization_record(
                        record, 'records_collection', 'insert')
                    time.sleep(0.02)
                    if inserted:
                        rds += 1

                        if rds == 50:
                            print('Waiting 1 minute')
                            time.sleep(60)
                            rds = 0
                else:
                    not_i = {
                        '_id': ObjectId(),
                        'source': source,
                        'organization': organization_name
                    }
                    inserted = insert_organization_record(
                        not_i, 'not_inserted', 'insert')
                    if inserted:
                        return False
