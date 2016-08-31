import csv
from io import StringIO
import urllib.request
import pymongo
import datetime
import progressbar
from ib_bars import ib_bars_import,disconnect,ib_bars_list,convert_bars_size
from megamot_hints_db import make_hints_list
from ib_bars import hint_datesym_import
from time import sleep
#from ipdb import set_trace as bp
OPTIONS = {
    "entry_var": 0.01,
    "stop_var": 0,
    "exit1to1_var": 0,
    "bar_size": 5,
    "exit_var":0.01,
}








def entry_query(hint, bars, options):
    # did the hint entered a position?
    # TODO: add time limit to enter a hint

    entry_bar = None

    if hint['position'] == "long":
        entry_price = hint['price'] + options["entry_var"]
        for i, bar in enumerate(bars):
            if bar['date'] >= hint['time'].replace(second = 0, microsecond = 0) and bar['high'] >= entry_price:
                if bar['date'] < hint['time'].replace(hour=(hint['time'].hour+1),second = 0, microsecond = 0):
                    return i, bar, entry_price, bars[i:]
        if not entry_bar:
            print("did not enter")
            return None, None, None, list()

    elif hint['position'] == "short":
        entry_price = hint['price'] - options["entry_var"]
        for i, bar in enumerate(bars):
            if bar['date'] >= hint['time'].replace(second = 0, microsecond = 0) and bar['low'] <= entry_price:
                if bar['date'] < hint['time'].replace(hour=(hint['time'].hour+1),second = 0, microsecond = 0):
                    return i, bar, entry_price, bars[i:]
        if not entry_bar:
            print("did not enter")
            return None, None, None, list()

def exit_query(direction, stop, bar, options):
    if direction == "long":
        if bar["low"] <= (stop - options['exit_var']):
            exit_bar = bar
            exit_price = stop - options['exit_var']
        else:
            exit_bar = None
            exit_price = None
    elif direction == "short":
        if bar['high'] >= (stop + options['exit_var']):
            exit_bar = bar
            exit_price = stop + options['exit_var']
        else:
            exit_bar = None
            exit_price = None
    return exit_bar,exit_price

def one_strategy_execute(hint, ticks, options):
    #bars = ticks_to_bars(options["bar_size"], ticks)
    #bp()

    #for i in range(3, len(tick)):
    #    bar = bars[i]

    entry_tick = None
    if hint["position"] == 'long':
        entry_price = hint['price'] + options["entry_var"]
        for i, tick in enumerate(ticks):
            if tick['date'] >= hint['time']:
                    if (tick['price'] >= hint['price'] + options["entry_var"]):
                        entry_tick = tick
                        left_ticks = ticks[i:]
                        break

        if not entry_tick:
            return general["did not enter"]

        for tick in left_ticks:
            if tick['date'] > entry_tick['date']:
                if tick['price'] <= (hint['stop'] - options["stop_var"]):
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
            if tick['date'] >= hint['time']:
               if tick['price'] <= hint['price'] - options["entry_var"]:
                        entry_tick = tick
                        left_ticks = ticks[i:]
                        break
        if not entry_tick:
            return general["did not enter"]

        for tick in left_ticks:
            if tick['date'] > entry_tick['date']:
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
             'hintDirection':hint['position'],
             'hint stop' : hint['stop']
   }

def defensive_strategy(hint, bars, options, general):
    # TODO: add time in day in which we change bars scale from 1-minute to 5-minute
    stop = hint['stop']

    ## did we enter the position?
    # returns entrance details and list of bars starting from entry bar
    index, entry_bar, entry_price, left_bars = entry_query(hint, bars, options)
    if not entry_bar:
        processed_hint = general["did not enter"]
        return processed_hint

    ### Changes Needed ###
    ### entry time after 10:00?
    timeInterval = hint['time'].replace(hour=14, minute=00)
    bars_5m = convert_bars_size(bars, 5)
    bars_5m = filter(lambda x: x['date'] >= entry_bar['date'], bars_5m)
    bars_1m = []

    if entry_bar['date'] < timeInterval:
        bars_1m = filter(lambda bar: bar['date'] < timeInterval, left_bars)




    # if hint entered position
    if entry_bar:
        if hint["position"] == 'long':

            ### did the position ended first two bars?:
            for bar in left_bars[0:2]:
                exit_bar = exit_query('long',stop,bar,options)
            if exit_bar:
                processed_hint = {
                    'entryTime': entry_bar['date'],
                    'entryPrice': entry_price,
                    'exitTime': exit_bar['date'],
                    'exitPrice': stop - options['exit_var'],
                    'revenue': stop - options['exit_var'] - entry_price,
                    'symbol': hint['sym'],
                    'hintTime': hint['time'],
                    'hintTrigger': hint['price'],
                    'hintDirection': hint['position'],
                    'hint stop': hint['stop']
                }
                return processed_hint

           ### check if exit and possibly define new stop according to defensive algo:


            else:
                ### did the position ended?
                # checks updated stop
                for i in range(2,len(left_bars)):
                    exit_bar = exit_query('long',stop,left_bars[i],options)
                    if exit_bar:
                        processed_hint = {
                                    'entryTime': entry_bar['date'],
                                    'entryPrice': entry_price,
                                    'exitTime': exit_bar['date'],
                                    'exitPrice': stop - options['exit_var'],
                                    'revenue': stop - options['exit_var'] - entry_price,
                                    'symbol': hint['sym'],
                                    'hintTime': hint['time'],
                                    'hintTrigger': hint['price'],
                                    'hintDirection': hint['position'],
                                    'hint stop' : hint['stop']
                        }
                        return processed_hint

                    ### defensive algorithm:
                    # update stop if defensive pattern materialise
                    else:
                        if (left_bars[i-1]['low'] < left_bars[i-2]['low']) and (left_bars[i-1]['low'] < left_bars[i]['low']):
                            stop = left_bars[i-1]['low']

                ### if positionexit the trade 5 minutes before end of day:
                if not processed_hint:
                    processed_hint = {
                        'entryTime': entry_bar['date'],
                        'entryPrice': entry_price,
                        'exitTime': left_bars[-5]['date'],
                        'exitPrice': left_bars[-5]['close'],
                        'revenue': left_bars[-5]['close'] - entry_price,
                        'symbol': hint['sym'],
                        'hintTime': hint['time'],
                        'hintTrigger': hint['price'],
                        'hintDirection': hint['position'],
                        'hint stop': hint['stop']
                    }
                return processed_hint

        elif hint["position"] == 'short':
            for bar in left_bars[0:2]:
                exit_bar = exit_query(hint["position"],stop,bar,options)
                if exit_bar:
                    processed_hint = {
                    'entryTime': entry_bar['date'],
                    'entryPrice': entry_price,
                    'exitTime': exit_bar['date'],
                    'exitPrice': stop - options['exit_var'],
                    'revenue':  entry_price - stop + options['exit_var'],
                    'symbol': hint['sym'],
                    'hintTime': hint['time'],
                    'hintTrigger': hint['price'],
                    'hintDirection': hint['position'],
                    'hint stop': hint['stop']
                }
                    return processed_hint
            for i in range(2,len(left_bars)):
                exit_bar = exit_query(hint["position"],stop,left_bars[i],options)
                if exit_bar:
                    processed_hint = {
                                'entryTime': entry_bar['date'],
                                'entryPrice': entry_price,
                                'exitTime': exit_bar['date'],
                                'exitPrice': stop - options['exit_var'],
                                'revenue': entry_price - stop + options['exit_var'],
                                'symbol': hint['sym'],
                                'hintTime': hint['time'],
                                'hintTrigger': hint['price'],
                                'hintDirection': hint['position'],
                                'hint stop' : hint['stop']
                    }
                    return processed_hint
                else:
                    if (left_bars[i-1]['high'] > left_bars[i-2]['high']) and (left_bars[i-1]['high'] > left_bars[i]['high']):
                        stop = left_bars[i-1]['low']

        if not processed_hint:
            processed_hint = {
                'entryTime': entry_bar['date'],
                'entryPrice': entry_price,
                'exitTime': bars[-5]['date'],
                'exitPrice': left[-5]['close'],
                'revenue': left[-5]['close'] - entry_price,
                'symbol': hint['sym'],
                'hintTime': hint['time'],
                'hintTrigger': hint['price'],
                'hintDirection': hint['position'],
                'hint stop': hint['stop']
            }
            return processed_hint

def current_bot_strategy(hint, bars, options, general):
    processed_hint = None
    timeInterval = hint['time'].replace(hour=14, minute=00)
    stop = hint['stop']

    bars_5m = convert_bars_size(bars, 5)

    entry_index, entry_bar, entry_price, left_bars = entry_query(hint, bars, options)
    if not entry_bar:
        processed_hint = general["did not enter"]
        return processed_hint


    if entry_index <= 29:
        for i in range(entry_index,29):
            stop = defensive_query(hint,bars,i,stop)
            exit_bar, exit_price = exit_query(hint['position'],stop,bars[i],options)
            if exit_bar:
                processed_hint = processed_hint_template(hint,entry_bar,entry_price,exit_bar,exit_price)
                return processed_hint
        for i in range(6,len(bars_5m)):
            stop = defensive_query(hint,bars_5m,i,stop)
            exit_bar,exit_price = exit_query(hint['position'],stop,bars_5m[i],options)
            if exit_bar:
                processed_hint = processed_hint_template(hint,entry_bar,entry_price,exit_bar,exit_price)
                return processed_hint

    elif entry_index > 29:
        for i in range((int(entry_index/5)),len(bars_5m)):
            stop = defensive_query(hint,bars_5m,i,stop)
            exit_bar, exit_price = exit_query(hint['position'],stop,bars_5m[i],options)
            if exit_bar:
                processed_hint = processed_hint_template(hint,entry_bar,entry_price,exit_bar,exit_price)
                return processed_hint

    if not processed_hint:
        if hint['position'] == 'long':
            processed_hint = {
            'entryTime': entry_bar['date'],
            'entryPrice': entry_price,
            'exitTime': bars[-5]['date'],
            'exitPrice': bars[-5]['close'],
            'revenue': bars[-5]['close'] - entry_price,
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hint stop': hint['stop']
        }
        elif hint['position'] == 'short':
            processed_hint = {
                'entryTime': entry_bar['date'],
                'entryPrice': entry_price,
                'exitTime': bars[-5]['date'],
                'exitPrice': bars[-5]['close'],
                'revenue': entry_price - bars[-5]['close'],
                'symbol': hint['sym'],
                'hintTime': hint['time'],
                'hintTrigger': hint['price'],
                'hintDirection': hint['position'],
                'hint stop': hint['stop']
            }

    return processed_hint


def defensive_query(hint,bars,i,stop):
    if hint['position'] == 'long':
        if (bars[i - 3]['low'] > bars[i - 2]['low']) and (bars[i - 1]['low'] > bars[i - 2]['low']):
            stop = bars[i - 2]['low']
    elif hint['position'] == 'short':
        if (bars[i - 3]['high'] < bars[i - 2]['high']) and (bars[i - 1]['high'] < bars[i - 2]['high']):
            stop = bars[i - 2]['high']

    return stop

def processed_hint_template(hint,entry_bar,entry_price,exit_bar,exit_price):
    if hint['position'] == 'long':
        processed_hint = {
            'entryTime': entry_bar['date'],
            'entryPrice': entry_price,
            'exitTime': exit_bar['date'],
            'exitPrice': exit_price,
            'revenue': exit_price - entry_price,
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hint stop': hint['stop']
        }
    elif hint['position'] == 'short':
        processed_hint = {
            'entryTime': entry_bar['date'],
            'entryPrice': entry_price,
            'exitTime': exit_bar['date'],
            'exitPrice': exit_price,
            'revenue': entry_price - exit_price,
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hint stop': hint['stop']
        }
    return processed_hint


def process_hint(hint, options, general):
    try:
        ### is the hint valid?
        if(hint["position"] == "long") or (hint["position"] == "short"):

            ### create a day of one minute bars of one hint.
            bars = ib_bars_list(hint)
            if not bars:
                processed_hint = general["no bars"]

            ### execute strategy on hint.
            else:
                processed_hint = current_bot_strategy(hint,bars,options,general)

        ### if hint not valid(changed\canceled) return general dict
        elif hint["position"] == "changed":
            processed_hint = general["changed"]
        elif hint["position"] == "cancel":
            processed_hint = general["canceled"]
        return processed_hint

    except Exception as e:
        print("Failed to process hint: %s: %s" % (hint, e))
        return None

def main(options):

    """ make a corrected hints list from Mongo DB
    input: OPTIONS list which contains changeble variables.

     each hint contains:
     {
     sym:
     price:
     stop:
     position: (long\short\canceled\changed)
     time:
     }
     """
    hints_list = make_hints_list()


    ### make empty list of processed hints, eventually will go to csv file
    processed_hints = list()

    ### loop through hints and execute trading strategy
    for hint in hints_list:
        processed_hint = None
        for i,h in enumerate(processed_hints):
            if h['hintDirection'] == 'long' or h['hintDirection'] == 'short':
                if (h['symbol'] == hint['sym']) and (h['hintTime'].date() == hint['time'].date()):
                    if hint['time'] < h['entryTime']:
                        processed_hints[i] = general['did not enter']
                        print('sleeping')
                        sleep(15)
                    elif hint['time'] > h['exitTime']:
                        print('sleeping')
                        sleep(15)
                    else:
                        processed_hint = general["did not enter"]
                        processed_hints.append(processed_hint)
        if processed_hint:
            continue



        # list of general unprocessed hints
        general = {
        "did not enter": {
            'entryTime': 'did not enter',
            'entryPrice': 'did not enter',
            'exitTime': 'did not enter',
            'exitPrice': 'did not enter',
            'revenue': 'did not enter',
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hint stop' : hint['stop']

        },
        "no bars": {
            'entryTime': 'no bars',
            'entryPrice': 'no bars',
            'exitTime': 'no bars',
            'exitPrice': 'no bars',
            'revenue': 'no bars',
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hint stop' : hint['stop']
        },
        "changed": {
            'entryTime': hint['position'],
            'entryPrice': hint['position'],
            'exitTime': hint['position'],
            'exitPrice': hint['position'],
            'revenue': hint['position'],
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hint stop' : hint['stop']
        },
        "canceled": {
            'entryTime': hint['position'],
            'entryPrice': hint['position'],
            'exitTime': hint['position'],
            'exitPrice': hint['position'],
            'revenue': hint['position'],
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hint stop' : hint['stop']
        }
    }

        """
        execute strategy on hint.
        output: see example in one of the dicts in general list above
        """
        processed_hint = process_hint(hint, options, general)

        if not processed_hint:
            print("failed process_hint")
            continue

        processed_hints.append(processed_hint)
        if len(processed_hints) > 40:
            break

    if len(processed_hints):
        with open(r"processed_hints.csv", "w") as output:
            writer = csv.DictWriter(output, processed_hints[0].keys())
            writer.writeheader()
            writer.writerows(processed_hints)

def raiseExcp(error):
    raise error




if __name__ == "__main__":
    try:
        main(OPTIONS)
        #ib_bars_import("20160818","YY").subscribe(print, raiseExcp)

    finally:
        disconnect()
