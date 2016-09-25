#!/usr/bin/python3
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
from collections import namedtuple
import pickle
import os

__all__ = ["BarsOptions",
           "BarsService",
           "convert_bars_size"]

# Lower logger level
log = logging.getLogger("Rx")
log.setLevel(logging.INFO)

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

def _make_contract(symbol):
    contract = Contract()
    contract.m_symbol = symbol
    contract.m_secType = 'STK'
    contract.m_exchange = 'SMART'
    contract.m_primaryExch = 'SMART'
    contract.m_currency = 'USD'
    contract.m_localSymbol = symbol
    return contract

BarsOptions = namedtuple("BarsOptions", [
    "twsHost",
    "twsPort",
    "twsClientId",
    "cacheFile",
])

class BarsService(object):
    def __init__(self, options=BarsOptions(**{
        "twsHost": "localhost",
        "twsPort": 7497,
        "twsClientId": 666,
        "cacheFile": "bars.cache"
        })):

        self._opts = options
        self._connected = False
        self._ticker_id = 1
        self._conn = None
        self._cache = {}

        if os.path.isfile(options.cacheFile):
            with open(options.cacheFile, "rb") as f:
                self._cache = pickle.load(f)

    def disconnect(self):
        self._connected
        if self._connected:
            self._conn.disconnect()
            print("Disconnected from IB")
            self._connected = False
            self._conn = None

    def get_bars_list(self, hint, bar_size="1 min"):
        hint_date, hint_sym = self._hint_datesym_import(hint)
        if hint_sym not in self._cache:
            self._cache[hint_sym] = {}

        if hint_date not in self._cache[hint_sym]:
            try:
                self._cache[hint_sym][hint_date] = self._ib_bars_list(hint_date, hint_sym, bar_size)
                self._save_cache()
            except Exception as e:
                print ("failed to obtain bars for %s: %s" % (hint["sym"], e))
                return e.args[0]

        return self._cache[hint_sym][hint_date]

    def _connect(self):
        self._conn = ibConnection(host=self._opts.twsHost,
                                  port=self._opts.twsPort,
                                  clientId=self._opts.twsClientId)
        self._conn.connect()
        # Sleep for 1 second.
        sleep(1)

        print("Connected to IB")
        self._connected = True

    def _ib_bars_import(self, hint_date, hint_sym, bar_size="1 min",durationStr='1 D', verbose=False):
        """ Hint_date => YYYYMMD format """
        if bar_size == 5:
            bar_size=='5 mins'

        # Generate Event to wait for
        e = threading.Event()

        # Generate Observable for results
        retObservable = ReplaySubject()

        if (self._ticker_id % 60) == 0:
            print('sleeping 10 minutes')
            #sleep(600)

        # Connect To IB
        if not self._connected:
            self._connect()

        # Register input processing function
        def processInput(x):
            tz = tzlocal.get_localzone()
            if isinstance(x, self._conn.messageTypes['historicalData']):
                if x.date.startswith("finished"):
                    retObservable.on_completed()
                else:
                    nextValue = dict([(k, getattr(x, k)) for k in x.keys() if k !=
                                 "reqId"])
                    nextValue['date'] = tz.localize(datetime.strptime(nextValue['date'], '%Y%m%d %H:%M:%S'))
                    nextValue['date'] = nextValue['date'].astimezone(pytz.utc).replace(tzinfo=None)
                    retObservable.on_next(nextValue)
            elif isinstance(x, self._conn.messageTypes['error']):
                if "data farm connection is OK" in x.errorMsg:
                    return

                print (x, file=sys.stderr)
                if x.errorCode not in [None, 2103]:
                    retObservable.on_error(Exception(x.errorMsg));
            elif verbose:
                print (x)

        # Register it and connect
        self._conn.registerAll(processInput)

        # Request data from server
        endtime = "%s 23:00:00" % hint_date
        self._conn.reqHistoricalData(
            tickerId=self._ticker_id,
            contract=_make_contract(hint_sym),
            endDateTime=endtime,
            durationStr=durationStr,
            barSizeSetting=bar_size,
            whatToShow='TRADES',
            useRTH=1,
            formatDate=1)
        self._ticker_id += 1

        def on_complete(err=None):
            e.set()

        # Register on observable to hear "Complete" event.
        retObservable.subscribe(None, on_complete, on_complete)

        # Wait until data completed
        e.wait()

        return retObservable.as_observable()

    def _ib_bars_list(self, hint_date, hint_sym, bar_size):
        # bar_size "1 m" or "5 m"
        # hint_date YYMMDD
        if bar_size == 5:
            bar_size = '5 mins'
        bars_obs = self._ib_bars_import(hint_date,hint_sym,bar_size)
        if not bars_obs:
            return None
        arr_bars = list()
        bars_obs.subscribe(arr_bars.append, self._raiseExcp)
        return arr_bars

    def _raiseExcp(self, error):
        raise error

    def _hint_datesym_import(self, hint):
        hint_date = hint['time'].strftime("%Y%m%d")
        hint_sym  = hint['sym']
        return (hint_date, hint_sym)

    def _save_cache(self):
        with open(self._opts.cacheFile, "wb") as f:
            pickle.dump(self._cache, f)

    def __del__(self):
        self.disconnect()
        self._save_cache()
