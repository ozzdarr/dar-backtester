import csv
from io import StringIO
import urllib.request
import pymongo
import datetime
import progressbar
#from ipdb import set_trace as bp


OPTIONS = {
    "entry_var": 0.01,
    "stop_var": 0,
    "exit1to1_var": 0,
    "bar_size": 5,
}


def hints_import():
    mongo = pymongo.MongoClient("db.oasis-aws.1f7daa68.svc.dockerapp.io", 27017)
    db = mongo.db_production
    hints = db.hints
    all_hints = hints.find({
        "createdAt": {
            "$gt": datetime.datetime.now() - datetime.timedelta(days=14)
        }
    })
    current_hint = None

    for doc in all_hints:
        if doc["source"] != "megamot":
         continue

        if current_hint and (doc["sym"] != current_hint["sym"]) or (doc["position"] != "stop"):
            current_hint = None

        if not current_hint:
            if doc["position"] not in ["long", "short"]:
                continue
            
            current_hint = doc
            continue

        yield{
            "sym": current_hint["sym"],
            "position": current_hint["position"],
            "price": current_hint["price"],
            "stop": doc["price"],
            "time": current_hint["refTime"]
        }

        current_hint = None

def bar_hints_import():
    bar = progressbar.ProgressBar()
    return bar([i for i in hints_import()])
    
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
            #print(e,hint_date, hint_sym)
            pass
    if not data:
        raise Exception("Stock %s not found" % hint_sym)
    
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
    # Not finished #
    # Input: ticks and bar size
    # Output: bars. {'time':,'open':,close:,'high','low':)

    bars = list()
    current_bar = reset_bar(ticks[0])
    for i, tick in enumerate(ticks[1:]):
        # do we need to open a new bar?
        if (tick["time"] - current_bar["time"]) > datetime.timedelta(minutes=size):
            current_bar["close"] = ticks[i - 1]["price"]
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

def one_strategy_execute(hint, ticks, options):
    # Update needed #
    # Input: hint (fron megamot_hints),ticks
    # Output: append.positions(position): {'ref':,'entryTime':,'entryPrice':,'exitTime':,'exitPrice':,'revenue':}

    #bars = ticks_to_bars(options["bar_size"], ticks)
    #bp()

    #for i in range(3, len(tick)):
    #    bar = bars[i]
        
    entry_tick = None
    if hint["position"] == 'long':
        entry_price = hint['price'] + options["entry_var"]
        for i, tick in enumerate(ticks):
            if tick['time'] >= hint['time']:   
                    if (tick['price'] >= hint['price'] + options["entry_var"]):
                        entry_tick = tick
                        left_ticks = ticks[i:]
                        break
        
        if not entry_tick:
            return {
             'entryTime':'-',
             'entryPrice':'-',
             'exitTime':'-',
             'exitPrice':'-',
             'revenue':'-',
             'symbol':hint['sym'],
             'hintTime':hint['time'],
             'hintTrigger':hint['price'],
             'hintDirection':hint['position']

            }

        for tick in left_ticks:
            if tick['time'] > entry_tick['time']:
                if tick['price'] <= hint['stop'] - options["stop_var"]:
                    exit_price = hint['stop'] - options["stop_var"]
                    exit_tick = tick
                elif tick['price'] >= 2*hint['price'] - hint['stop'] + options["exit1to1_var"]:
                    exit_tick = tick
                    exit_price = 2*hint['price'] - hint['stop'] + options["exit1to1_var"]
                    break
        revenue = exit_price - entry_price
        
    elif hint['position'] == 'short':
        entry_price = hint['price'] - options["entry_var"]
        for i, tick in enumerate(ticks):
            if tick['time'] >= hint['time']: 
               if tick['price'] <= hint['price'] - options["entry_var"]:
                        entry_tick = tick
                        left_ticks = ticks[i:]
                        break
        if not entry_tick:
            return {
             'entryTime':'-',
             'entryPrice':'-',
             'exitTime':'-',
             'exitPrice':'-',
             'revenue':'-',
             'symbol':hint['sym'],
             'hintTime':hint['time'],
             'hintTrigger':hint['price'],
             'hintDirection':hint['position']

            }

        for tick in left_ticks:
            if tick['time'] > entry_tick['time']:
                if tick['price'] >= hint['stop'] + options["stop_var"]:
                   exit_tick = tick
                   exit_price = hint['stop'] + options["stop_var"] 
                elif tick['price'] <= (2 * hint['price']) - hint['stop'] - options["exit1to1_var"]:
                        exit_tick = tick
                        exit_price = (2 * hint['price']) - hint['stop'] - options["exit1to1_var"]
                        break
        revenue = entry_price - exit_price

    return {
             'entryTime':entry_tick['time'],
             'entryPrice':entry_tick['price'],
             'exitTime':exit_tick['time'],
             'exitPrice':exit_tick['price'],
             'revenue':revenue,
             'symbol':hint['sym'],
             'hintTime':hint['time'],
             'hintTrigger':hint['price'],
             'hintDirection':hint['position']
   }

def process_hint(hint, options):
    positions = list()
    try:
        hint_date, hint_sym = hint_datesym_import(hint)
        ticks = netfonds_ticks_import(hint_date, hint_sym)
        if not ticks:
            position = {'entryTime':'no ticks',
             'entryPrice':'no ticks',
             'exitTime':'no ticks',
             'exitPrice':'no ticks',
             'revenue':'no ticks',
             'symbol':hint['sym'],
             'hintTime':hint['time'],
             'hintTrigger':hint['price'],
             'hintDirection':hint['position']
             } 
        else:
            position = one_strategy_execute(hint, ticks, options)
        return position
    except Exception as e:
        print("Failed to process hint: %s: %s" % (hint, e))
        return None

def main(options):
    positions = list()
    #for hint in hints_import():
    for hint in bar_hints_import():
        position = process_hint(hint, options)
        if not position:
            position = {'entryTime':'no ticks',
             'entryPrice':'no ticks',
             'exitTime':'no ticks',
             'exitPrice':'no ticks',
             'revenue':'no ticks',
             'symbol':hint['sym'],
             'hintTime':hint['time'],
             'hintTrigger':hint['price'],
             'hintDirection':hint['position']
             }
        positions.append(position)
        if len(positions) > 5:
            break

    if len(positions):
        with open(r"positions.csv", "w") as output:
            writer = csv.DictWriter(output, positions[0].keys())
            writer.writeheader()
            writer.writerows(positions)


main(OPTIONS)
        
