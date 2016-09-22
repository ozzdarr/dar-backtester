#!/usr/bin/python3

from ib_bars import *
from db_collector import *
from strategies import *




OPTIONS = {
    "entry_var": 0.0,
    "stop_var": 0.0,
    "exit1to1_var": 0,
    "bar_size": 5,
    "exit_var": 0.0,
    "slippage": 0.0,
    'commission': 0

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

CSV_VALUE_CHECK = [
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
    'alpha',
    'omega',
    "slippage",
    "comment"

]


def raiseExcp(error):
    raise error




def process_hint(hint, options, counter, bars_service):
    try:
        if (hint["position"] == "long") or (hint["position"] == "short"):
            bars = bars_service.get_bars_list(hint)
            counter = counter + 1
            print("%d - %s" % (counter, hint["time"]))

            # Check if error in importing bars
            #Todo: add the eror to comment
            if type(bars) is str:
                print('ERROR' + bars)
                processed_hint = processed_hint_template(hint,options)
            else:
                processed_hint = value_check(hint, bars, options)

        elif hint["position"] == "cancel":
            processed_hint = processed_hint_template(hint,options)
        return processed_hint, counter

    except Exception as e:
        print("Failed to process hint: %s: %s" % (hint, e))
        return None, counter








def main(options, bars_service):

    hints_list = make_hints_list()
    processed_hints = list()
    counter = 0

    #Todo: make this function - "check_hint() add comments to changed hints"
    for hint in hints_list:
        # Unreasonable stop
        if hint['position'] == 'long':
            if hint['stop'] > hint['price'] :
                processed_hint = processed_hint_template(hint,options)
                processed_hint['comment'] = 'Stop is unreasonable'
                processed_hints.append(processed_hint)
                continue
        elif hint['position'] == 'short':
            if hint['stop'] < hint['price']:
                processed_hint = processed_hint_template(hint,options)
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
                        processed_hint = processed_hint_template(hint,options)
                        processed_hints.append(processed_hint)
        if processed_hint:
            continue



        processed_hint, counter = process_hint(hint, options,
                                               counter, bars_service)
        #Todo: add failed to process hint to processed_hints
        if not processed_hint:
            print("failed process_hint")
            continue

        processed_hints.append(processed_hint)
        # if len(processed_hints) > 3:
        #   break

    csv_writer(processed_hints,CSV_VALUE_CHECK)


if __name__ == "__main__":
    try:
        bars_service = BarsService()
        main(OPTIONS, bars_service)
    finally:
        del bars_service
        # TODO: make sure it disconnects
