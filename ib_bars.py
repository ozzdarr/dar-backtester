#!/usr/bin/python3
from ib.opt import ibConnection, message
from ib.ext.Contract import Contract
from time import sleep, strftime
from rx.subjects import ReplaySubject
import threading
import logging
import sys
import pytz
import tzlocal
from datetime import timedelta, datetime
from collections import namedtuple
import pickle
import os
import moment
from time import mktime
from bar import Bar

__all__ = ["QueryDuration",
           "BarsOptions",
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

class QueryDuration(namedtuple("QueryDuration",
    ["years", "months", "weeks", "days", "hours", "minutes", "seconds"]
)):
    @staticmethod
    def __new__ (cls, *args, **kargs):
        if len(kargs) > 1:
            raise Exception("Duration support only 1 unit")
        if len(args) > 0:
            raise Exception("Duration support only named arguments")

        new_kargs = dict([(key, 0) for key in cls._fields])
        provided = list(kargs.keys())[0]
        new_kargs[provided] = kargs[provided]

        return super(QueryDuration, cls).__new__(cls, *args, **new_kargs)

    def __init__(self, *args, **kargs):
        super(QueryDuration, self).__init__()
        self._as_string = self._to_string()

    @property
    def fields(self):
        return dict([(key, getattr(self, key)) for key in self._fields])

    @staticmethod
    def _format_value(value, unit):
        return ({
            "years": value,
            "months": value,
            "weeks": value,
            "days": value,
            "hours": value * 60 * 60,
            "minutes": value * 60,
            "seconds": value,
        }[unit])

    @staticmethod
    def _format_string(value, unit):
        value = QueryDuration._format_value(value, unit)
        return "%d %s" % (value, {
            "years": "Y",
            "months": "M",
            "weeks": "W",
            "days": "D",
            "hours": "S",
            "minutes": "S",
            "seconds": "S"
        }[unit])

    def _to_string(self):
        for field in self._fields:
            value = getattr(self, field)
            if value == 0:
                continue
            return QueryDuration._format_string(value, field)

    def get_relative_formatted(self, date):
        """ Date should be either date or string YYYYMMDD """

        tz = tzlocal.get_localzone()

        if type(date) is str:
            date = datetime.strptime("%s 13:30" % date, "%Y%m%d %H:%M").replace(tzinfo=pytz.utc)
            date = date.astimezone(tz)

        if type(date) is datetime:
            # Make sure timezone fits
            if not date.tzinfo:
                date = date.replace(tzinfo=pytz.utc)

            if date.tzinfo != tz:
                date = date.astimezone(tz)

        m = moment.unix(mktime(date.replace(tzinfo=None).timetuple()))
        return m.add(**self.fields).format("YYYYMMDD HH:mm:ss")

    @property
    def as_string(self):
        return self._as_string

class BarsService(object):
    _INSTANCE = None

    def __init__(self, options=None):

        if self._INSTANCE:
            raise Exception("BarsService is already initialized")

        if not options:
            options = BarsOptions(**{
                "twsHost": "localhost",
                "twsPort": 7497,
                "twsClientId": 666,
                "cacheFile": "bars.cache"
            })

        self._opts = options
        self._connected = False
        self._ticker_id = 1
        self._pacing_counter = 0
        self._conn = None
        self._cache_dirty = False
        self._cache = {
            'bars': {},
            'expanded_bars': {},
        }

        if os.path.isfile(options.cacheFile):
            with open(options.cacheFile, "rb") as f:
                self._cache = pickle.load(f)

        # Upgrading bars cache from bars only to bars + expanded.
        if 'bars' not in self._cache:
            self._cache = {
                'bars': self._cache,
                'expanded_bars': {},
            }

    @classmethod
    def init(cls, options=None):
        cls._INSTANCE = BarsService()

    @classmethod
    def deinit(cls):
        if cls._INSTANCE:
            del cls._INSTANCE
        cls._INSTANCE = None

    @classmethod
    def instance(cls):
        return cls._INSTANCE

    def disconnect(self):
        self._connected
        if self._connected:
            self._conn.disconnect()
            print("Disconnected from IB")
            self._connected = False
            self._conn = None

    def _query(self, query_type, hint_date, hint_sym, fetcher=None):
        if hint_sym not in self._cache[query_type]:
            self._cache[query_type][hint_sym] = {}

        if hint_date not in self._cache[query_type][hint_sym]:
            try:
                self._cache[query_type][hint_sym][hint_date] = fetcher(hint_date, hint_sym)
                self._cache_dirty = True
                self._save_cache()
            except Exception as e:
                print ("failed to obtain bars for %s: %s" % (hint_sym, e))
                return e.args[0]

        return list(map(lambda x: Bar(**x),
                        self._cache[query_type][hint_sym][hint_date]))

    def expand_bar(self, hint_date, hint_sym, duration=None):
        return self._query('expanded_bars',
                           hint_date,
                           hint_sym,
                           lambda x, y: self._ib_bars_list(x, y, "1 secs", duration))

    def get_bars_list(self, hint, bar_size="1 min"):
        hint_date, hint_sym = self._hint_datesym_import(hint)
        return self._query('bars',
                           hint_date,
                           hint_sym,
                           lambda x, y: self._ib_bars_list(x, y, bar_size))
    def _connect(self):
        self._conn = ibConnection(host=self._opts.twsHost,
                                  port=self._opts.twsPort,
                                  clientId=self._opts.twsClientId)
        self._conn.connect()
        # Sleep for 1 second.
        sleep(1)

        print("Connected to IB")
        self._connected = True

    def _ib_bars_import(self, hint_date, hint_sym, bar_size="1 min",
                        duration=None, verbose=False):
        tz = tzlocal.get_localzone()
        """ Hint_date => YYYYMMD format """
        if bar_size == 5:
            bar_size=='5 mins'

        if not duration:
            duration = QueryDuration(days=1)

        # Generate Event to wait for
        e = threading.Event()

        # Generate Observable for results
        retObservable = ReplaySubject()

        # Connect To IB
        if not self._connected:
            self._connect()

        if self._pacing_counter != 0 and self._pacing_counter % 60 == 0:
            print('sleeping 10 minutes')
            sleep(600)

        # Register input processing function
        def processInput(x):
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
        endtime = duration.get_relative_formatted(hint_date)

        self._conn.reqHistoricalData(
            tickerId=self._ticker_id,
            contract=_make_contract(hint_sym),
            endDateTime=endtime,
            durationStr=duration.as_string,
            barSizeSetting=bar_size,
            whatToShow='TRADES',
            useRTH=1,
            formatDate=1)
        self._ticker_id += 1

        def on_complete(err=None):
            if not err:
                self._pacing_counter += 1
            e.set()

        # Register on observable to hear "Complete" event.
        retObservable.subscribe(None, on_complete, on_complete)

        # Wait until data completed
        e.wait()

        return retObservable.as_observable()

    def _ib_bars_list(self, hint_date, hint_sym, bar_size, duration=None):
        # bar_size "1 m" or "5 m"
        # hint_date YYMMDD
        if bar_size == 5:
            bar_size = '5 mins'

        bars_obs = self._ib_bars_import(hint_date,hint_sym,bar_size,duration)
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
        if not self._cache_dirty:
            return

        with open(self._opts.cacheFile, "wb") as f:
            pickle.dump(self._cache, f)
            self._cache_dirty = False

    def __del__(self):
        self.disconnect()
        self._save_cache()
