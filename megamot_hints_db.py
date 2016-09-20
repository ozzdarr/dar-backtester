import csv
from io import StringIO
import urllib.request
import pymongo
import datetime


def default_stop(hint):
    if hint['position'] == 'long':
        return hint['price'] - ((hint['price'] * 0.0033) + 0.05)
    elif hint['position'] == 'short':
        return hint['price'] + ((hint['price'] * 0.0033) + 0.05)



def hints_import():
    mongo = pymongo.MongoClient("139.59.211.215", 27017)
    db = mongo.db_production
    hints = db.hints
    all_hints = hints.find({})
    #all_hints = hints.find({
    #    "refTime": {
    #        "$gt": datetime.datetime(2016,7,12,14,31,0,0),
    #        "$lt": datetime.datetime(2016,7,12,14,32,0,0)
    #}})

    current_hint = None
    hints_list = list()
    for doc in all_hints:
        doc['refTime'] = doc['refTime'].replace(microsecond=0)
        #if doc["source"] != "simple_trade":
         #   continue

        if doc["source"] != "megamot":
            continue

        if (current_hint and (doc["sym"] != current_hint["sym"])) or (doc["position"] != "stop"):
            if current_hint:
                hints_list.append({
                    "position": current_hint["position"],
                    "sym": current_hint["sym"],
                    "price": current_hint["price"],
                    "stop": default_stop(current_hint),
                    "time": current_hint["refTime"]
                })
            current_hint = None

        if not current_hint:
            if doc["position"] not in ["long", "short", "cancel"]:
                continue
            current_hint = doc
            continue

        hints_list.append({
            "sym": current_hint["sym"],
            "position": current_hint["position"],
            "price": current_hint["price"],
            "stop": doc["price"],
            "time": current_hint["refTime"]
        })

        current_hint = None
    return hints_list


def add_cancel(hints_list):
    mongo = pymongo.MongoClient("139.59.211.215", 27017)
    db = mongo.db_production
    hints = db.hints
    all_hints = hints.find({})
    '''all_hints = hints.find({
        "refTime": {
            "$gt": datetime.datetime(2016,8,21,10,0,0,0)
        }
    })'''
    for doc in all_hints:
        if doc["source"] != "megamot":
            continue
        if doc["position"] == "cancel":
            for hint in hints_list:
                if hint["sym"] == doc["sym"]:
                    if hint["time"].strftime("%Y-%m-%d") == doc["refTime"].strftime("%Y-%m-%d"):
                        if hint['time'] < doc['refTime']:
                            hint["position"] = "cancel"

    return hints_list


def make_hints_list():
    hints_list = hints_import()
    #hints_list = add_cancel(hints_list)
    # hints_list = add_changes(hints_list)
    return hints_list


# Todo: add exporting functions
def hints_to_csv(source='megamot'):
    mongo = pymongo.MongoClient("139.59.211.215", 27017)
    db = mongo.db_production
    hints = db.hints
    all_hints = hints.find({})
    print(all_hints)
    for doc in all_hints:
        if doc['source'] != source:
            del doc
    print(all_hints)









    csv_keys = [
        'refTime',
        'createdAt',
        'sym',
        'position',
        'price',
        'source',
        '_id,'
        'ref'
    ]
    with open(r"hints from DB.csv", "w") as output:
        writer = csv.DictWriter(output, csv_keys)
        writer.writeheader()
        writer.writerows(all_hints)


