import csv
from math import fabs
from processedHint import ProcessedHint

def csv_writer(fileName, listOfDicts, csv_keys):
    if len(listOfDicts):
        with open(fileName, "w") as output:
            writer = csv.DictWriter(output, csv_keys)
            writer.writeheader()
            writer.writerows(listOfDicts)

def processed_hint_template(hint,options, entry_bar=None, entry_price=None,
                            exit_bar=None, exit_price=None,bars=None,
                            error=None):
    slippage = options['slippage']
    commission = options['commission']

    if error:
        processed_hint = {
            'entryTime': 'error',
            'entryPrice': 'error',
            'exitTime': 'error',
            'exitPrice': 'error',
            'netRevenue': 'error',
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hintStop': hint['defend'],
            'slippage': '-',
            'comment': 'ERROR: %s' % error,
        }
    elif type(bars) is str:
        processed_hint = {
            'entryTime': 'no bars',
            'entryPrice': 'no bars',
            'exitTime': 'no bars',
            'exitPrice': 'no bars',
            'netRevenue': 'no bars',
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hintStop': hint['stop'],
            'slippage': '-',
            'comment': 'ERROR: %s' % bars,
        }
    elif not entry_bar:
        processed_hint = {
            'entryTime': 'did not enter',
            'entryPrice': 'did not enter',
            'exitTime': 'did not enter',
            'exitPrice': 'did not enter',
            'netRevenue': 'did not enter',
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hintStop': hint['stop'],
            'slippage': '-',
            'comment': '-'
        }
    elif hint.isCancel:
        processed_hint = {
        'entryTime': hint['position'],
        'entryPrice': hint['position'],
        'exitTime': hint['position'],
        'exitPrice': hint['position'],
        'netRevenue': hint['position'],
        'symbol': hint['sym'],
        'hintTime': hint['time'],
        'hintTrigger': hint['price'],
        'hintDirection': hint['position'],
        'hintStop': hint['stop'],
        'slippage': '-',
        'comment': '-'
        }
    elif entry_bar and exit_bar:
        if hint.isLong:
            processed_hint = {
                'entryTime': entry_bar['date'],
                'entryPrice': entry_price,
                'exitTime': exit_bar['date'],
                'exitPrice': exit_price,
                'netRevenue': round(exit_price - entry_price - 2*slippage - commission,2),
                'symbol': hint['sym'],
                'hintTime': hint['time'],
                'hintTrigger': hint['price'],
                'hintDirection': hint['position'],
                'hintStop': hint['stop'],
                'slippage': slippage,
                'comment': '-'
            }
        elif hint.isShort:
            processed_hint = {
                'entryTime': entry_bar['date'],
                'entryPrice': entry_price,
                'exitTime': exit_bar['date'],
                'exitPrice': exit_price,
                'netRevenue':  round(entry_price - exit_price - 2*slippage - commission,2),
                'symbol': hint['sym'],
                'hintTime': hint['time'],
                'hintTrigger': hint['price'],
                'hintDirection': hint['position'],
                'hintStop': hint['stop'],
                'slippage': slippage,
                'comment': '-'
            }
    elif entry_bar and not exit_bar:
        if hint.isLong:
            processed_hint = {
            'entryTime': entry_bar['date'],
            'entryPrice': entry_price,
            'exitTime': bars[-10]['date'],
            'exitPrice': bars[-10]['close'],
            'netRevenue': round(bars[-10]['close'] - entry_price - 2*slippage - commission,2),
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hintStop': hint['stop'],
            'slippage': slippage,
            'comment': '-'
            }
        elif hint.isShort:
            processed_hint = {
            'entryTime': entry_bar['date'],
            'entryPrice': entry_price,
            'exitTime': bars[-10]['date'],
            'exitPrice': bars[-10]['close'],
            'netRevenue': round(entry_price - bars[-10]['close'] - 2*slippage - commission,2),
            'symbol': hint['sym'],
            'hintTime': hint['time'],
            'hintTrigger': hint['price'],
            'hintDirection': hint['position'],
            'hintStop': hint['stop'],
            'slippage': slippage,
            'comment': '-'
            }

    return ProcessedHint(**processed_hint)
