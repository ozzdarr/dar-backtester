import csv
from io import StringIO
import urllib.request
import pymongo
import datetime

mongo = pymongo.MongoClient("139.59.211.215", 27017)
db = mongo.db_production
orders = db.orders
all_orders = orders.find()





with open(r"orders from mongo.csv", "w") as output:
    writer = csv.DictWriter(output, all_orders[0].keys())
    writer.writeheader()
    writer.writerows(all_orders)