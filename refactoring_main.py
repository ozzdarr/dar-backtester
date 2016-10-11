#!/usr/bin/python3

from csv_templates import processed_hint_template, csv_writer
from strategies import one_to_one
from ib_bars import BarsService
from db_collector import make_hints_list
from processedHint import ProcessedHint
from hint import Hint

OPTIONS = {
    "entry_var": 0.01,
    "stop_var": 0.01,
    "agressive_var": 0.05,
    "exit1to1_var": 0,
    "bar_size": 5,
    "exit_var": 0.01,
    "slippage": 0.02,
    'commission': 0,
    'max_defend_size': 1.00,
    'kill_trade_time': 10, # 10 minutes before EOD
    'output_file_name': r'backtester_results.csv',
    'unreasonable_defend': None,
    'has_no_defend': None
}

CSV_KEYS = ProcessedHint._fields

def process_raw_hints(raw_hints, options):
    processed_hints = list()
    for raw_hint in raw_hints:
        # Validation test for hint
        invalid_processed_hint = validation_test(raw_hint, options, processed_hints)
        if invalid_processed_hint:
            processed_hints.append(invalid_processed_hint)
            continue
        else:
            # Continue process valid hints
            processed_hint = process_valid_hint(raw_hint, options)
            processed_hints.append(processed_hint)
            if len(processed_hints) > 20:
                return processed_hints
            continue
    return processed_hints

def validation_test(hint, options, processed_hints):
    ignored_hint = None
    invalid_processed_hint = None

    if hint.hasNoDefend:
        if not options['has_no_defend']:
            invalid_processed_hint = processed_hint_template(hint, options, error='No stop input from admin')
    elif hint.hasUnreasonableUserDefend(options):
        if not options['unreasonable_defend']:
            invalid_processed_hint = processed_hint_template(hint, options, error='Unreasonable stop')
    elif not hint.isCancel and hint.hasBigUserDefend(options):
        if not options['max_defend_size']:
            invalid_processed_hint = processed_hint_template(hint, options, error='Unreasonable stop - too big')
    if len(processed_hints):
        ignored_hint = hint.returningHints(processed_hints, options)
    if ignored_hint:
        invalid_processed_hint = ignored_hint
    if hint.isCancel:
        invalid_processed_hint = processed_hint_template(hint, options)

    if invalid_processed_hint:
        return invalid_processed_hint
    else:
        return  None

def process_valid_hint(hint, options):
    # Create "Hint" object


    # Import bars
    bars, error_processed_hint = hint.importBars(options=options)

    # If there was an error in importing
    if error_processed_hint:
        return error_processed_hint
    # Continue Processing valid hint
    else:
        # Execute strategy
        processed_hint = one_to_one(hint, bars, options)
        return processed_hint

def main(options):
    processed_hints = process_raw_hints(make_hints_list(), options)
    if not len(processed_hints):
        print("No results - No output")
        return

    csv_writer(options['output_file_name'],
               [i.asDict for i in processed_hints],
               CSV_KEYS)

if __name__ == "__main__":
    try:
        BarsService.init()
        main(OPTIONS)
    finally:
        BarsService.deinit()
