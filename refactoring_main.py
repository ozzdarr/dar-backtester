#!/usr/bin/python3

OPTIONS = {
    "entry_var": 0.01,
    "stop_var": 0.01,
    "exit1to1_var": 0,
    "bar_size": 5,
    "exit_var": 0.01,
    "slippage": 0.02,
    'commission': 0
}

def main(options, bars_service):
    processed_hints = process_hints(make_hints_list(), options, bars_service)
    if not len(processed_hints):
        print("No results - No output")
        return

    csv_writer(options['output_file_name'],
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

def process_hints(raw_hints,options,bar_service):
    processed_hints = list()
    for hint in raw_hints:
        # Validation test for hint
        hint, unvalid_processed_hint = validation_test(hint,options,processed_hints)
        if unvalid_processed_hint:
            processed_hints.append(unvalid_processed_hint)
            continue
        else:
            # Continue process valid hints
            processed_hint = process_valid_hint(hint,options,bar_service,counter)
            processed_hints.append(processed_hint)
            continue
    return processed_hints


def validation_test(hint,options,processed_hints):
    hint = hint.manipulateStop
    if hint.hasUnreasonableStop:
        unvalid_processed_hint = processed_hints_teamplate(hint,options,error='Unreasonable stop')
    if hint.hasBigStop:
        unvalid_processed_hint = processed_hints_teamplate(hint,options,error='Unreasonable stop - too big')
    ignored_hint = hint.returning_hints_test(processed_hints=processed_hints)
    if ignored_hint:
        unvalid_processed_hint = ignored_hint
    if hint.isCancel:
        unvalid_processed_hint = processed_hints_teamplate(hint, options)

    if unvalid_processed_hint:
        return hint, unvalid_processed_hint
    else:
        return hint, None



def process_valid_hint(hint,options,bars_service,counter):
    # Import bars
    bars, error_processed_hint, counter = hint.importBars(counter=counter)
    # If there was an error in importing
    if error_processed_hint:
        return error_processed_hint
    else:
        processed_hint = one_to_one(hint, bars, options, bars_service)
        return processed_hint



