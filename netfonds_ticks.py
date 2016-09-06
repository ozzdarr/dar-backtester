import csv
from io import StringIO
import urllib.request
import pymongo
import datetime
def hint_datesym_import(hint):
    hint_date = hint['time'].strftime("%Y%m%d")
    hint_sym  = hint['sym']
    return (hint_date, hint_sym)

def netfonds_ticks_import(hint_date, hint_sym):
    # input: hint_date,hint_sym(as strings)
    # output: list of ticks of one day and stock. {'time':,'price'}
    # ToDo: 1.change to time format  2.add volume

    convert_time = lambda x: datetime.datetime.strptime(x, "%Y%m%dT%H%M%S") - datetime.timedelta(hours=2)
    tries = ["N", "O", "A"]

    data = None
    for i in tries:
        try:
            url = 'http://hopey.netfonds.no/tradedump.php?date=%s&paper=%s.%s&csv_format=csv' % (hint_date, hint_sym, i)
            csvv = urllib.request.urlopen(url).read() # returns type 'bytes'
            data = StringIO(csvv.decode(encoding='UTF-8'))
            break
        except Exception as e:
            print(e,hint_date, hint_sym)
            pass
    if not data:
        print("Stock %s not found" % hint_sym)
        ticks = None

    else:
        reader = csv.reader(data)
        rows = list(reader)
        ticks = [{rows[0][1]: float(col[1]), rows[0][0]: convert_time(col[0])} for col in rows[1:]]
    return ticks

def reset_bar(tick):
    return {
        "time": tick["time"].replace(second=0),
        "open": tick["price"],
        "close": 0,
        "high": tick["price"],
        "low": tick["price"],
    }

def ticks_to_bars(size, ticks):
    bars = list()
    current_bar = reset_bar(ticks[0])
    for i, tick in enumerate(ticks[1:]):
        # do we need to open a new bar?
        if (tick["time"] - current_bar["time"]) > datetime.timedelta(minutes=size):
            current_bar["close"] = ticks[i]["price"]
            bars.append(current_bar)
            current_bar = reset_bar(tick)
            continue

        # Update Max
        if tick["price"] > current_bar["high"]:
            current_bar["high"] = tick["price"]

        # Update Min
        if tick["price"] < current_bar["low"]:
            current_bar["low"] = tick["price"]

    # Save last item
    current_bar["close"] = ticks[-1]["price"]
    bars.append(current_bar)

    return bars

def process_ticks(hint):
    hint_date, hint_sym = hint_datesym_import(hint)
    ticks = netfonds_ticks_import(hint_date, hint_sym)
    if not ticks:
        return ticks
    else:
        bars = ticks_to_bars(size, ticks)
        return bars