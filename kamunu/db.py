from pymongo import MongoClient

def mongodb():

    db_uri="mongodb://localhost:27017/"
    db_name="organizations_ids"
    collection_name="records_collection"
    collection_name_not_inserted="not_inserted"

    dbclient = MongoClient(db_uri)
    db = dbclient[db_name]
    records_collection = db[collection_name]
    not_inserted = db[collection_name_not_inserted]
    
    if records_collection and not_inserted:
        return records_collection, not_inserted