from ib_bars import QueryDuration


def exit_query(direction, stop, bar, options):
    #Todo: change "stop" argument to "exit price". (the function will get  exit price after reducing entry_var)
    #Todo: replace argiment "direction" with hint
    if direction == "long":
        if bar["low"] <= (stop - options['exit_var']):
            exit_bar = bar
            exit_price = round(stop - options['exit_var'],2)
        else:
            exit_bar = None
            exit_price = None
    elif direction == "short":
        if bar['high'] >= (stop + options['exit_var']):
            exit_bar = bar
            exit_price = round(stop + options['exit_var'],2)
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
    if hint.isLong:
        if (bars[i - 3]['low'] > bars[i - 2]['low']) and (bars[i - 1]['low'] > bars[i - 2]['low']):
            if bars[i - 2]['low'] > stop:
                if bars[i - 2]['low'] >= 100:
                    stop = bars[i - 2]['low'] - 0.01
                else:
                    stop = bars[i - 2]['low']
    elif hint.isShort:
        if (bars[i - 3]['high'] < bars[i - 2]['high']) and (bars[i - 1]['high'] < bars[i - 2]['high']):
            if bars[i - 2]['high'] < stop:
                if bars[i - 2]['high'] > 100:
                    stop = bars[i - 2]['high'] + 0.01
                else:
                    stop = bars[i - 2]['high']

    return stop
