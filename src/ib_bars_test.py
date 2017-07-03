from ib.opt import ibConnection, message
from ib.ext.Contract import Contract
from time import sleep, strftime
from datetime import datetime
from rx.subjects import ReplaySubject
import threading
import logging
import sys
import pytz
import tzlocal
from datetime import timedelta

# Lower logger level
log = logging.getLogger("Rx")
log.setLevel(logging.INFO)
CONNECTED = False
TICKER_ID = 1
CONN = ibConnection(host="localhost", port=7497, clientId=666)
CONN.connect()
# Sleep for 1 second.
sleep(1)

print("Connected to IB")
CONNECTED = True

def make_contract(symbol):
    contract = Contract()
    contract.m_symbol = symbol
    contract.m_secType = 'STK'
    contract.m_exchange = 'SMART'
    contract.m_primaryExch = 'SMART'
    contract.m_currency = 'USD'
    contract.m_localSymbol = symbol
    return contract

def ib_bars_import(hint_date, hint_sym, bar_size="1 min", verbose=False):
    if bar_size == 5:
        bar_size=='5 mins'
    """ Hint_date => YYYYMMD format """

    # Generate Event to wait for
    e = threading.Event()

    # Generate Observable for results
    retObservable = ReplaySubject()

    # Connect To IB
    global CONN, TICKER_ID
    conn = CONN

    # Register input processing function
    def processInput(x):
        tz = tzlocal.get_localzone()
        if isinstance(x, conn.messageTypes['historicalData']):
            if x.date.startswith("finished"):
                retObservable.on_completed()
            else:
                nextValue = dict([(k, getattr(x, k)) for k in x.keys() if k !=
                             "reqId"])
                nextValue['date'] = tz.localize(datetime.strptime(nextValue['date'], '%Y%m%d %H:%M:%S'))
                nextValue['date'] = nextValue['date'].astimezone(pytz.utc).replace(tzinfo=None)
                retObservable.on_next(nextValue)
        elif isinstance(x, conn.messageTypes['error']):
            if "data farm connection is OK" in x.errorMsg:
                return

            print (x, file=sys.stderr)
            if x.errorCode != None:
                retObservable.on_error(Exception(x.errorMsg));
        elif verbose:
            print (x)

    # Register it and connect
    conn.registerAll(processInput)

    # Request data from server
    endtime = "%s 17:20:00" % hint_date
    conn.reqHistoricalData(
        tickerId=TICKER_ID,
        contract=make_contract(hint_sym),
        endDateTime=endtime,
        durationStr='1800 S',
        barSizeSetting=bar_size,
        whatToShow='TRADES',
        useRTH=1,
        formatDate=1)
    TICKER_ID += 1

    def on_complete(err=None):
        e.set()

    # Register on observable to hear "Complete" event.
    retObservable.subscribe(None, on_complete, on_complete)

    # Wait until data completed
    e.wait()

    return retObservable.as_observable()

def disconnect():
    global CONNECTED
    if CONNECTED:
        global CONN
        CONN.disconnect()
        print("Disconnected from IB")
        CONNECTED = False

def ib_bars_list(hint,bar_size="1 min"):
    try:
        return _ib_bars_list(hint, bar_size)
    except Exception as e:
        print ("failed to obtain bars for %s: %s" % (hint["sym"], e))
        return list()

def _ib_bars_list(hint,bar_size):
    # bar_size "1 m" or "5 m"
    # hint_date YYMMDD
    if bar_size == 5:
        bar_size = '5 mins'
    hint_date, hint_sym = hint_datesym_import(hint)
    bars_obs = ib_bars_import(hint_date,hint_sym,bar_size)
    if not bars_obs:
        return None
    arr_bars = list()
    bars_obs.subscribe(arr_bars.append, raiseExcp)
    return arr_bars

def raiseExcp(error):
    raise error

def hint_datesym_import(hint):
    hint_date = hint['time'].strftime("%Y%m%d")
    hint_sym  = hint['sym']
    return (hint_date, hint_sym)

def convert_bars_size(bars_toconvert, size):
    current_bar = bars_toconvert[0].copy()
    newBars = list()
    for i, boo in enumerate(bars_toconvert[1:]):
        # do we need to open a new bar?
        if (boo["date"] - current_bar["date"]) == timedelta(minutes=size):
            current_bar["close"] = boo["close"]
            newBars.append(current_bar)
            current_bar = boo.copy()
            continue

        # Update Max
        if boo["high"] > current_bar["high"]:
            current_bar["high"] = boo["high"]

        # Update Min
        if boo["low"] < current_bar["low"]:
            current_bar["low"] = boo["low"]
    # Save last item
    current_bar["close"] = bars_toconvert[-1]["close"]
    newBars.append(current_bar)

    return newBars