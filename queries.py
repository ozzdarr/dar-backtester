

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


def omega_query(hint, bar, omega=0):
    if hint['position'] == 'long':
        if not omega:
            omega = bar['low']
        elif bar['low'] < omega:
            omega = bar['low']
    elif hint['position'] == 'short':
        if not omega:
            omega = bar['high']
        if bar['high'] > omega:
            omega = bar['high']
    return omega


def alpha_qury(hint, bar, alpha=0):
    if hint['position'] == 'long':
        if not alpha:
            alpha = bar['high']
        if bar['high'] > alpha:
            alpha = bar['high']
    elif hint['position'] == 'short':
        if not alpha:
            alpha = bar['low']
        if bar['low'] < alpha:
            alpha = bar['low']
    return alpha

def potential_query(hint, bar, potential_price, potential_time):
    if hint['position'] == 'long':
        if not potential_price:
            potential_price = bar['high']
            potential_time = bar['date']
        if bar['high'] > potential_price:
            potential_price = bar['high']
            potential_time = bar['date']
    elif hint['position'] == 'short':
        if not potential_price:
            potential_price = bar['low']
            potential_time = bar['date']
        if bar['low'] < potential_price:
            potential_price = bar['low']
            potential_time = bar['date']
    return potential_price, potential_time