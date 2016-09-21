import csv
from math import fabs

def csv_writer(listOfDicts, csv_keys):
    if len(listOfDicts):
        with open(r"one to one.csv", "w") as output:
            writer = csv.DictWriter(output, csv_keys)
            writer.writeheader()
            writer.writerows(listOfDicts)

def processed_hint_template(hint,options, entry_bar=None, entry_price=None, exit_bar=None, exit_price=None,bars=None):
    slippage = options['slippage']
    commission = options['commission']

    if type(bars) is str:
        processed_hint = {
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
        }
    if not entry_bar:
        processed_hint = {
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
        }
    if hint['position'] == 'cancel' :
        processed_hint = {
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
    if entry_bar and exit_bar:
        if hint['position'] == 'long':
            processed_hint = {
                'entryTime': entry_bar['date'],
                'entryPrice': entry_price,
                'exitTime': exit_bar['date'],
                'exitPrice': exit_price,
                'Net revenue': exit_price - entry_price - 2*slippage - commission,
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
                'Net revenue':  entry_price - exit_price - 2*slippage - commission,
                'symbol': hint['sym'],
                'hintTime': hint['time'],
                'hintTrigger': hint['price'],
                'hintDirection': hint['position'],
                'hintStop': hint['stop'],
                'slippage': slippage,
                'comment': '-'
            }
    if entry_bar and not exit_bar:
        if hint['position'] == 'long':
            processed_hint = {
            'entryTime': entry_bar['date'],
            'entryPrice': entry_price,
            'exitTime': bars[-10]['date'],
            'exitPrice': bars[-10]['close'],
            'Net revenue': bars[-10]['close'] - entry_price - 2*slippage - commission,
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
            'exitTime': bars[-10]['date'],
            'exitPrice': bars[-10]['close'],
            'Net revenue': entry_price - bars[-10]['close'] - 2*slippage - commission,
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hintStop': hint['stop'],
            'slippage': slippage,
            'comment': '-'
            }

    return processed_hint