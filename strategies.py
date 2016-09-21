
from queries import *
from ib_bars import convert_bars_size
from csv_templates import *




def current_bot_strategy(hint, bars, options):
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
        if hint['position'] == 'long':
            if (bars[entry_index]['low'] - entry_price) > 0.05:
                entry_bar = None
        elif hint['position'] == 'short':
            if (entry_price - bars[entry_index]['high']) > 0.05:
                entry_bar = None

    if not entry_bar:
        processed_hint = processed_hint_template(hint,options)
        processed_hint['comment'] = 'Unreasonable hint price'
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
                processed_hint = processed_hint_template(hint,options,entry_bar, entry_price, exit_bar, exit_price,bars)

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

def one_to_one(hint, bars, options):
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
        processed_hint = processed_hint_template(hint,options)
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
        processed_hint = processed_hint_template(hint,options)
        processed_hint['comment'] = 'Unreasonable hint price'
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