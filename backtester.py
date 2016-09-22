#!/usr/bin/python3

from db_collector import *
from strategies import *
from processedHint import ProcessedHint
from ib_bars import BarsService

OPTIONS = {
    "entry_var": 0.01,
    "stop_var": 0.01,
    "exit1to1_var": 0,
    "bar_size": 5,
    "exit_var": 0.01,
    "slippage": 0.02,
    'commission': 0
}

CSV_KEYS = ProcessedHint._fields

def raiseExcp(error):
    raise error

def process_hint(hint, options, counter, bars_service):
    try:
        processed_hint = None
        if hint.hasDirection:
            bars = bars_service.get_bars_list(hint)
            counter = counter + 1
            print("%d - %s" % (counter, hint['time']))

            # Check if error in importing bars
            if type(bars) is str:
                processed_hint = processed_hint_template(hint, options, bars=bars)
            else:
                processed_hint = current_bot_strategy(hint, bars, options, bars_service)
        elif hint.isCancel:
            processed_hint = processed_hint_template(hint, options)

        return processed_hint, counter
    except Exception as e:
        return ("Failed to process hint: %s: %s" % (hint, e), counter)

def process_hints(hints_list, options, bars_service):
    processed_hints = list()
    counter = 0

    for hint in hints_list:
        # Unreasonable stop
        if hint.hasUnreasonableStop:
            processed_hint = processed_hint_template(hint, options, error='Stop is unreasonable')
            processed_hints.append(processed_hint)
            continue

        # Changed hints
        processed_hint = None
        for i, h in enumerate(processed_hints):
            if h.hasDirection and h.isHintMatch(hint):
                if type(h['entryTime']) is str:
                    continue
                if hint['time'] < h['entryTime']:
                    h['entryTime'] = 'did not enter'
                    h['entryPrice'] = 'did not enter'
                    h['exitTime'] = 'did not enter'
                    h['exitPrice'] = 'did not enter'
                    h['netRevenue'] = 'did not enter'
                    continue
                elif hint['time'] > h['exitTime']:
                    continue
                else:
                    processed_hint = processed_hint_template(hint, options)
                    processed_hints.append(processed_hint)

        if processed_hint:
            continue

        processed_hint, counter = process_hint(hint, options,
                                               counter, bars_service)
        # Adding failed hints as errors
        if type(processed_hint) is str:
            processedhint = processed_hint_template(hint,
                                                    options,
                                                    error=processed_hint)
        processed_hints.append(processed_hint)

    return processed_hints

def main(options, bars_service):
    processed_hints = process_hints(make_hints_list(), options, bars_service)
    if not len(processed_hints):
        print("No results - No output")
        return

    csv_writer("backtester-results.csv",
               [i.asDict for i in processed_hints],
               CSV_KEYS)

if __name__ == "__main__":
    bars_service = None
    try:
        bars_service = BarsService()
        main(OPTIONS, bars_service)
    finally:
        if bars_service:
            del bars_service
