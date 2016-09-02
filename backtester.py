import csv
from io import StringIO
import urllib.request
import pymongo
import datetime
import progressbar
from ib_bars import ib_bars_import,disconnect,ib_bars_list,convert_bars_size,hint_datesym_import
from megamot_hints_db import make_hints_list

from time import sleep
#from ipdb import set_trace as bp
OPTIONS = {
    "entry_var": 0.01,
    "stop_var": 0,
    "exit1to1_var": 0,
    "bar_size": 5,
    "exit_var":0.01,
    "slippage":0.04
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
            return None, None, None, list()

    elif hint['position'] == "short":
        entry_price = hint['price'] - options["entry_var"]
        for i, bar in enumerate(bars):
            if bar['date'] >= hint['time'].replace(second = 0, microsecond = 0) and bar['low'] <= entry_price:
                if bar['date'] < hint['time'].replace(hour=(hint['time'].hour+1),second = 0, microsecond = 0):
                    return i, bar, entry_price, bars[i:]
        if not entry_bar:
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
                processed_hint = processed_hint_template(hint,entry_bar,entry_price,exit_bar,exit_price,options['slippage'])
                return processed_hint
        for i in range(6,len(bars_5m)):
            stop = defensive_query(hint,bars_5m,i,stop)
            exit_bar,exit_price = exit_query(hint['position'],stop,bars_5m[i],options)
            if exit_bar:
                processed_hint = processed_hint_template(hint,entry_bar,entry_price,exit_bar,exit_price,options['slippage'])
                return processed_hint

    elif entry_index > 29:
        for i in range((int(entry_index/5)),len(bars_5m)):
            stop = defensive_query(hint,bars_5m,i,stop)
            exit_bar, exit_price = exit_query(hint['position'],stop,bars_5m[i],options)
            if exit_bar:
                processed_hint = processed_hint_template(hint,entry_bar,entry_price,exit_bar,exit_price,options['slippage'])
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

def processed_hint_template(hint,entry_bar,entry_price,exit_bar,exit_price,slippage):
    if hint['position'] == 'long':
        processed_hint = {
            'entryTime': entry_bar['date'],
            'entryPrice': entry_price,
            'exitTime': exit_bar['date'],
            'exitPrice': exit_price,
            'revenue': (exit_price - entry_price)-slippage,
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hint stop': hint['stop'],
            'slippage': slippage,
            'comment': '-'
        }
    elif hint['position'] == 'short':
        processed_hint = {
            'entryTime': entry_bar['date'],
            'entryPrice': entry_price,
            'exitTime': exit_bar['date'],
            'exitPrice': exit_price,
            'revenue': (entry_price - exit_price)-slippage,
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hint stop': hint['stop'],
            'slippage': slippage,
            'comment': '-'
        }
    return processed_hint


def process_hint(hint, options, general, counter):
    try:
        ### is the hint valid?
        if(hint["position"] == "long") or (hint["position"] == "short"):

            ### create a day of one minute bars of one hint.
            if counter != 0 and (counter % 60) == 0:
                print('sleeping 10 minutes')
                sleep(600)
            bars = ib_bars_list(hint)
            counter = counter + 1
            print (counter)
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
        return processed_hint, counter

    except Exception as e:
        print("Failed to process hint: %s: %s" % (hint, e))
        return None, counter

def main(options):


    hints_list = make_hints_list()


    # make empty list of processed hints, eventually will go to csv file
    processed_hints = list()
    counter = 0
    ### loop through hints and execute trading strategy
    for hint in hints_list:
        processed_hint = None
        for i,h in enumerate(processed_hints):
            if h['hintDirection'] == 'long' or h['hintDirection'] == 'short':
                if (h['symbol'] == hint['sym']) and (h['hintTime'].date() == hint['time'].date()):
                    if h['entryTime'] is "did not enter":
                        continue
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
            'hint stop' : hint['stop'],
            'slippage': '-',
            'comment': '-'

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
            'hint stop' : hint['stop'],
            'slippage': '-',
            'comment': '-'
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
            'hint stop' : hint['stop'],
            'slippage': '-',
            'comment': '-'
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
            'hint stop' : hint['stop'],
            'slippage': '-',
            'comment':'-'
        }
    }

        """
        execute strategy on hint.
        output: see example in one of the dicts in general list above
        """
        processed_hint, counter = process_hint(hint, options, general,counter)

        if not processed_hint:
            print("failed process_hint")
            continue

        processed_hints.append(processed_hint)
        #if len(processed_hints) > 40:
         #   break

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

    finally:
        disconnect()

