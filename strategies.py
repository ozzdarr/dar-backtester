
from queries import *
from ib_bars import convert_bars_size
from csv_templates import *
from hint import Hint

def current_bot_strategy(hint, bars, options):
    return defensive_strategy(hint, bars, options)

def defensive_strategy(hint, bars, options):
    processed_hint = None
    stop = hint['stop']
    bars_5m = convert_bars_size(bars, 5)

    # Check entrance in one minute bars
    entry_index, entry_bar, entry_price, left_bars = entry_query(hint, bars, options)
    if not entry_bar:
        processed_hint = processed_hint_template(hint,options)
        return processed_hint

    # Unreasonable hint trigger
    if entry_bar:
        if hint.isLong:
            if (bars[entry_index]['low'] - entry_price) > 0.05:
                entry_bar = None
        elif hint.isShort:
            if (entry_price - bars[entry_index]['high']) > 0.05:
                entry_bar = None

    if not entry_bar:
        processed_hint = processed_hint_template(hint, options, error='Unreasonable hint price')
        return processed_hint

    # Before 10:00
    if entry_index <= 29:
        for i in range(entry_index + 1, 29):
            stop = defensive_query(hint, bars, i, stop)
            exit_bar, exit_price = exit_query(hint['position'], stop, bars[i], options)
            if exit_bar:
                processed_hint = processed_hint_template(hint,options,entry_bar, entry_price, exit_bar, exit_price,bars)
                return processed_hint
        for i in range(6, len(bars_5m)):
            stop = defensive_query(hint, bars_5m, i, stop)
            exit_bar, exit_price = exit_query(hint['position'], stop, bars_5m[i], options)
            if exit_bar:
                processed_hint = processed_hint_template(hint,options, entry_bar, entry_price, exit_bar, exit_price,bars)

                return processed_hint
    # After 10:00
    elif entry_index > 29:
        # Start checking exit from one bar after entrance and on
        for i in range(int(entry_index / 5) + 1, len(bars_5m)):

            # Stop checking 10 minutes before end of day
            if i + 1 == 78:
                break

            stop = defensive_query(hint, bars_5m, i, stop)
            exit_bar, exit_price = exit_query(hint['position'], stop, bars_5m[i], options)
            if exit_bar:
                processed_hint = processed_hint_template(hint,options,entry_bar, entry_price, exit_bar, exit_price,bars)

                return processed_hint

    # Define processed hint 10 min before end of day
    if not processed_hint:
        processed_hint = processed_hint_template(hint,options,entry_bar, entry_price, bars[-10], bars[-10]['close'],bars)

    return processed_hint


def one_to_one(hint, bars, options):
    print(hint)
    print(hint.target)
    hint = update_hint(hint)
    print(hint)
    processed_hint = None
    stop = hint['stop']
    print(stop)
    slippage = options['slippage']
    commission = options['commission']


    stop_size = hint.stopSize
    target = hint.target


    # Check entrance in one minute bars
    entry_index, entry_bar, entry_price, left_bars = entry_query(hint, bars, options)
    if not entry_bar:
        processed_hint = processed_hint_template(hint,options)
        return processed_hint

    # Unreasonable hint trigger
    # Todo: put this inside entry_query()
    if entry_bar:
        if hint.isLong:
            if (bars[entry_index]['low'] - entry_price) > 0.05:
                entry_bar = None
        elif hint.isShort:
            if (entry_price - bars[entry_index]['high']) > 0.05:
                entry_bar = None
    if not entry_bar:
        processed_hint = processed_hint_template(hint,options,error='Unreasonable hint price')
        return processed_hint

    for bar in left_bars[1:]:
        exit_bar, exit_price = exit_query(hint['position'], stop, bar, options)
        if exit_bar:
            processed_hint = processed_hint_template(hint,options,entry_bar, entry_price, exit_bar, exit_price,bars)
            return processed_hint

        exit_bar, exit_price = target_query(bar, target, hint['position'],options)
        if exit_bar:
            processed_hint = processed_hint_template(hint,options,entry_bar, entry_price, exit_bar, exit_price,bars)
            return processed_hint

    # Define processed hint 10 min before end of day
    if not processed_hint:
        processed_hint = processed_hint_template(hint,options,entry_bar,
                                                 entry_price, bars[-1], bars[-1]['close'],bars)
    return processed_hint

def update_hint(hint):
    hint = Hint(**{
    'position': hint.position,
    'price': hint.target,
    'stop': hint.price,
    'time': hint.time,
    'sym': hint.sym
    })
    return hint

