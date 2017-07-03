import csv
from io import StringIO
import urllib.request
import pymongo
import datetime



mongo = pymongo.MongoClient("139.59.211.215", 27017)
db = mongo.db_production
orders = db.megamot_feeds
cursor = orders.find()

cursor_objects = list()
for cursor_doc in cursor:
    doc = cursor_doc.copy()
    if 'duration' in doc:
        del doc['duration']
    cursor_objects.append(doc)

with open(r"ofeeds.csv", "w") as output:
    writer = csv.DictWriter(output, cursor_objects[0].keys())
    writer.writeheader()
    writer.writerows(cursor_objects)