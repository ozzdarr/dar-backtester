#!/usr/bin/python3

import csv
from io import StringIO
from math import fabs
import pymongo
import datetime
import progressbar
from ib_bars import BarsService, convert_bars_size
from db_collector import make_hints_list

from time import sleep

# from ipdb import set_trace as bp
OPTIONS = {
    "entry_var": 0,
    "stop_var": 0,
    "exit1to1_var": 0,
    "bar_size": 5,
    "exit_var": 0,
    "slippage": 0.0311,
    'commission': 0.012

}

CSV_KEYS = [
    "hintTime",
    "symbol",
    "hintTrigger",
    "hintDirection",
    "hintStop",
    "entryTime",
    "entryPrice",
    "exitTime",
    "exitPrice",
    "Net revenue",
    "slippage",
    "comment"
]

def raiseExcp(error):
    raise error

def csv_writer(listOfDicts, csv_keys):
    if len(listOfDicts):
        with open(r"one to one.csv", "w") as output:
            writer = csv.DictWriter(output, csv_keys)
            writer.writeheader()
            writer.writerows(listOfDicts)

def entry_query(hint, bars, options):
    # Todo: add 0.05 interval
    # did the hint entered a position?


    entry_bar = None

    if hint['position'] == "long":
        entry_price = hint['price'] + options["entry_var"]
        entry_price = round(entry_price, 2)
        for i, bar in enumerate(bars):
            if bar['date'] >= hint['time'].replace(second=0, microsecond=0) and bar['high'] >= entry_price:
                if bar['date'] < hint['time'].replace(hour=(hint['time'].hour + 1), second=0, microsecond=0):
                    return i, bar, entry_price, bars[i:]
        if not entry_bar:
            return None, None, None, list()

    elif hint['position'] == "short":
        entry_price = hint['price'] - options["entry_var"]
        entry_price = round(entry_price, 2)
        for i, bar in enumerate(bars):
            if bar['date'] >= hint['time'].replace(second=0, microsecond=0) and bar['low'] <= entry_price:
                if bar['date'] < hint['time'].replace(hour=(hint['time'].hour + 1), second=0, microsecond=0):
                    return i, bar, entry_price, bars[i:]
        if not entry_bar:
            return None, None, None, list()


def exit_query(direction, stop, bar, options):
    #Todo: change "stop" argument to "exit price". (the function will get  exit price after reducing entry_var)
    #Todo: replace argiment "direction" with hint
    if direction == "long":
        if bar["low"] <= (stop - options['exit_var']):
            exit_bar = bar
            exit_price = (stop - options['exit_var'])
        else:
            exit_bar = None
            exit_price = None
    elif direction == "short":
        if bar['high'] >= (stop + options['exit_var']):
            exit_bar = bar
            exit_price = (stop + options['exit_var'])
        else:
            exit_bar = None
            exit_price = None
    return exit_bar, exit_price

def target_query(bar,target,direction,options):

    if direction == 'long':
        if bar['high'] >= (target + options['exit_var']):
            return bar, target
        else:
            return  None,None
    elif direction == 'short':
        if bar['low'] <= (target - options['exit_var']):
            return bar, target
        else:
            return None, None

def defensive_query(hint, bars, i, stop):
    if hint['position'] == 'long':
        if (bars[i - 3]['low'] > bars[i - 2]['low']) and (bars[i - 1]['low'] > bars[i - 2]['low']):
            if bars[i - 2]['low'] > stop:
                if bars[i - 2]['low'] >= 100:
                    stop = bars[i - 2]['low'] - 0.01
                else:
                    stop = bars[i - 2]['low']
    elif hint['position'] == 'short':
        if (bars[i - 3]['high'] < bars[i - 2]['high']) and (bars[i - 1]['high'] < bars[i - 2]['high']):
            if bars[i - 2]['high'] < stop:
                if bars[i - 2]['high'] > 100:
                    stop = bars[i - 2]['high'] + 0.01
                else:
                    stop = bars[i - 2]['high']

    return stop



def processed_hint_template(hint, entry_bar, entry_price, exit_bar, exit_price, options):
    slippage = options['slippage']
    commission = options['commission']
    if hint['position'] == 'long':
        processed_hint = {
            'entryTime': entry_bar['date'],
            'entryPrice': entry_price,
            'exitTime': exit_bar['date'],
            'exitPrice': exit_price,
            'Net revenue': (exit_price - entry_price) - 2*slippage - commission,
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hintStop': hint['stop'],
            'slippage': slippage,
            'comment': '-'
        }
    elif hint['position'] == 'short':
        processed_hint = {
            'entryTime': entry_bar['date'],
            'entryPrice': entry_price,
            'exitTime': exit_bar['date'],
            'exitPrice': exit_price,
            'Net revenue': (entry_price - exit_price) - 2*slippage - commission,
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hintStop': hint['stop'],
            'slippage': slippage,
            'comment': '-'
        }
    return processed_hint


def process_hint(hint, options, general, counter, bars_service):
    try:
        if (hint["position"] == "long") or (hint["position"] == "short"):
            bars = bars_service.get_bars_list(hint)

            counter = counter + 1
            print("%d - %s" % (counter, hint["time"]))

            # Check if error in importing bars
            #Todo: add the eror to comment
            if type(bars) is str:
                print('ERORO' + bars)
                processed_hint = general["no bars"]

            else:
                processed_hint = one_to_one(hint, bars, options, general)

        #Todo: change this to more
        elif hint["position"] == "changed":
            processed_hint = general["changed"]
        elif hint["position"] == "cancel":
            processed_hint = general["canceled"]
        return processed_hint, counter

    except Exception as e:
        print("Failed to process hint: %s: %s" % (hint, e))
        return None, counter





def current_bot_strategy(hint, bars, options, general):
    processed_hint = None
    stop = hint['stop']
    bars_5m = convert_bars_size(bars, 5)

    # Check entrance in one minute bars
    entry_index, entry_bar, entry_price, left_bars = entry_query(hint, bars, options)
    if not entry_bar:
        processed_hint = general["did not enter"]
        return processed_hint

    # Unreasonable hint trigger
    if entry_bar:
        if hint['position'] == 'long':
            if (bars[entry_index]['low'] - entry_price) > 0.05:
                entry_bar = None
        elif hint['position'] == 'short':
            if (entry_price - bars[entry_index]['high']) > 0.05:
                entry_bar = None

    if not entry_bar:
        processed_hint = general["did not enter"]
        processed_hint['comment'] = 'Unreasonable hint price'
        return processed_hint

    # Before 10:00
    if entry_index <= 29:
        for i in range(entry_index + 1, 29):
            stop = defensive_query(hint, bars, i, stop)
            exit_bar, exit_price = exit_query(hint['position'], stop, bars[i], options)
            if exit_bar:
                processed_hint = processed_hint_template(hint, entry_bar, entry_price, exit_bar, exit_price,
                                                         options)
                return processed_hint
        for i in range(6, len(bars_5m)):
            stop = defensive_query(hint, bars_5m, i, stop)
            exit_bar, exit_price = exit_query(hint['position'], stop, bars_5m[i], options)
            if exit_bar:
                processed_hint = processed_hint_template(hint, entry_bar, entry_price, exit_bar, exit_price,
                                                         options)
                return processed_hint
    # After 10:00
    elif entry_index > 29:

        # defensive pattern in 3 bars before entrance?
        # stop = defensive_query(hint,bars_5m,int(entry_index/5),stop)

        # Start checking exit from one bar after entrance and on
        for i in range(int(entry_index / 5) + 1, len(bars_5m)):

            # Stop checking 10 minutes before end of day
            if i + 1 == 78:
                break

            stop = defensive_query(hint, bars_5m, i, stop)
            exit_bar, exit_price = exit_query(hint['position'], stop, bars_5m[i], options)
            if exit_bar:
                processed_hint = processed_hint_template(hint, entry_bar, entry_price, exit_bar, exit_price,
                                                         options)
                return processed_hint

    # Define processed hint 10 min before end of day
    if not processed_hint:
        if hint['position'] == 'long':
            processed_hint = {
                'entryTime': entry_bar['date'],
                'entryPrice': entry_price,
                'exitTime': bars[-10]['date'],
                'exitPrice': bars[-10]['close'],
                'Net revenue': bars[-10]['close'] - entry_price,
                'symbol': hint['sym'],
                'hintTime': hint['time'],
                'hintTrigger': hint['price'],
                'hintDirection': hint['position'],
                'hintStop': hint['stop']
            }
        elif hint['position'] == 'short':
            processed_hint = {
                'entryTime': entry_bar['date'],
                'entryPrice': entry_price,
                'exitTime': bars[-10]['date'],
                'exitPrice': bars[-10]['close'],
                'Net revenue': entry_price - bars[-10]['close'],
                'symbol': hint['sym'],
                'hintTime': hint['time'],
                'hintTrigger': hint['price'],
                'hintDirection': hint['position'],
                'hintStop': hint['stop']
            }

    return processed_hint

def one_to_one(hint, bars, options, general):
    processed_hint = None
    stop = hint['stop']
    slippage = options['slippage']
    commission = options['commission']

    # Stop delta
    if hint['position'] == 'long':
        stop_delta = (hint['price'] - hint['stop'])
    elif hint['position'] == 'short':
        stop_delta =  hint['stop']- hint['price']

    # Target
    if hint['position'] == 'long':
        target = stop_delta + hint['price'] + options['exit_var'] + 2*slippage + commission
    elif hint['position'] == 'short':
        target = hint['price'] - stop_delta - options['exit_var'] - 2*slippage - commission


    # Check entrance in one minute bars
    entry_index, entry_bar, entry_price, left_bars = entry_query(hint, bars, options)
    if not entry_bar:
        processed_hint = general["did not enter"]
        return processed_hint

    # Unreasonable hint trigger
    # Todo: put this inside entry_query()
    if entry_bar:
        if hint['position'] == 'long':
            if (bars[entry_index]['low'] - entry_price) > 0.05:
                entry_bar = None
        elif hint['position'] == 'short':
            if (entry_price - bars[entry_index]['high']) > 0.05:
                entry_bar = None
    if not entry_bar:
        processed_hint = general["did not enter"]
        processed_hint['comment'] = 'Unreasonable hint price'
        return processed_hint

    for bar in left_bars[1:]:
        exit_bar, exit_price = exit_query(hint['position'], stop, bar, options)
        if exit_bar:
            processed_hint = processed_hint_template(hint, entry_bar, entry_price, exit_bar, exit_price,
                                                     options)
            return processed_hint

        exit_bar, exit_price = target_query(bar, target, hint['position'],options)
        if exit_bar:
            processed_hint = processed_hint_template(hint, entry_bar, entry_price, exit_bar, exit_price,
                                                     options)
            return processed_hint

    # Define processed hint 10 min before end of day
    if not processed_hint:
        if hint['position'] == 'long':
            processed_hint = {
                'entryTime': entry_bar['date'],
                'entryPrice': entry_price,
                'exitTime': bars[-1]['date'],
                'exitPrice': bars[-1]['close'],
                'Net revenue': -0.0742,
                'symbol': hint['sym'],
                'hintTime': hint['time'],
                'hintTrigger': hint['price'],
                'hintDirection': hint['position'],
                'hintStop': hint['stop'],
                'comment': '-'
            }
        elif hint['position'] == 'short':
            processed_hint = {
                'entryTime': entry_bar['date'],
                'entryPrice': entry_price,
                'exitTime': bars[-1]['date'],
                'exitPrice': bars[-1]['close'],
                'Net revenue': -0.0742,
                'symbol': hint['sym'],
                'hintTime': hint['time'],
                'hintTrigger': hint['price'],
                'hintDirection': hint['position'],
                'hintStop': hint['stop'],
                'comment': '-'
            }

    return processed_hint

def main(options, bars_service):

    hints_list = make_hints_list()
    processed_hints = list()
    counter = 0

    #Todo: make this function - "check_hint()"
    for hint in hints_list:
        general = {
            "did not enter": {
                'entryTime': 'did not enter',
                'entryPrice': 'did not enter',
                'exitTime': 'did not enter',
                'exitPrice': 'did not enter',
                'Net revenue': 'did not enter',
                'symbol': hint['sym'],
                'hintTime': hint['time'],
                'hintTrigger': hint['price'],
                'hintDirection': hint['position'],
                'hintStop': hint['stop'],
                'slippage': '-',
                'comment': '-'

            },
            "no bars": {
                'entryTime': 'no bars',
                'entryPrice': 'no bars',
                'exitTime': 'no bars',
                'exitPrice': 'no bars',
                'Net revenue': 'no bars',
                'symbol': hint['sym'],
                'hintTime': hint['time'],
                'hintTrigger': hint['price'],
                'hintDirection': hint['position'],
                'hintStop': hint['stop'],
                'slippage': '-',
                'comment': '-'
            },
            "changed": {
                'entryTime': hint['position'],
                'entryPrice': hint['position'],
                'exitTime': hint['position'],
                'exitPrice': hint['position'],
                'Net revenue': hint['position'],
                'symbol': hint['sym'],
                'hintTime': hint['time'],
                'hintTrigger': hint['price'],
                'hintDirection': hint['position'],
                'hintStop': hint['stop'],
                'slippage': '-',
                'comment': '-'
            },
            "canceled": {
                'entryTime': hint['position'],
                'entryPrice': hint['position'],
                'exitTime': hint['position'],
                'exitPrice': hint['position'],
                'Net revenue': hint['position'],
                'symbol': hint['sym'],
                'hintTime': hint['time'],
                'hintTrigger': hint['price'],
                'hintDirection': hint['position'],
                'hintStop': hint['stop'],
                'slippage': '-',
                'comment': '-'
            }
        }

        # Unreasonable stop
        if hint['position'] == 'long':
            if hint['stop'] > hint['price'] :
                processed_hint = general['did not enter']
                processed_hint['comment'] = 'Stop is unreasonable'
                processed_hints.append(processed_hint)
                continue
        elif hint['position'] == 'short':
            if hint['stop'] < hint['price']:
                processed_hint = general['did not enter']
                processed_hint['comment'] = 'Stop is unreasonable'
                processed_hints.append(processed_hint)
                continue

        # Changed hints
        processed_hint = None
        for i, h in enumerate(processed_hints):
            if h['hintDirection'] == 'long' or h['hintDirection'] == 'short':
                if (h['symbol'] == hint['sym']) and (h['hintTime'].date() == hint['time'].date()):
                    if type(h['entryTime']) is str:
                        continue
                    if hint['time'] < h['entryTime']:
                        h['entryTime'] = 'did not enter'
                        h['entryPrice'] = 'did not enter'
                        h['exitTime'] = 'did not enter'
                        h['exitPrice'] = 'did not enter'
                        h['Net revenue'] = 'did not enter'
                        continue
                    elif hint['time'] > h['exitTime']:
                        continue
                    else:
                        processed_hint = general["did not enter"]
                        processed_hints.append(processed_hint)
        if processed_hint:
            continue



        processed_hint, counter = process_hint(hint, options, general,
                                               counter, bars_service)
        #Todo: add failed to process hint to processed_hints
        if not processed_hint:
            print("failed process_hint")
            continue

        processed_hints.append(processed_hint)
        # if len(processed_hints) > 3:
        #   break

    csv_writer(processed_hints,CSV_KEYS)


if __name__ == "__main__":
    try:
        bars_service = BarsService()
        main(OPTIONS, bars_service)
    finally:
        del bars_service
        # TODO: make sure it disconnects
