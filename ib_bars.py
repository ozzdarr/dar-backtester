#!/usr/bin/python3

from ib.opt import ibConnection, message
from ib.ext.Contract import Contract
from time import sleep, strftime
from datetime import datetime
from rx.subjects import ReplaySubject
import threading
import logging
import sys

# Lower logger level
log = logging.getLogger("Rx")
log.setLevel(logging.INFO)

def make_contract(symbol):
    contract = Contract()
    contract.m_symbol = symbol
    contract.m_secType = 'STK'
    contract.m_exchange = 'SMART'
    contract.m_primaryExch = 'SMART'
    contract.m_currency = 'USD'
    contract.m_localSymbol = symbol
    return contract

def ib_bars_import(hint_date, hint_sym, verbose=False):
    """ Hint_date => YYYYMMD format """

    # Generate Event to wait for
    e = threading.Event()

    # Generate Observable for results
    retObservable = ReplaySubject()

    # Connect To IB
    conn = ibConnection(host="localhost", port=7497, clientId=666)

    # Register input processing function
    def processInput(x):
        if isinstance(x, conn.messageTypes['historicalData']):
            if x.date.startswith("finished"):
                retObservable.on_completed()
            else:
                nextValue = dict([(k, getattr(x, k)) for k in x.keys() if k !=
                             "reqId"])
                nextValue['date'] = datetime.strptime(nextValue['date'], '%Y%m%d %H:%M:%S')
                retObservable.on_next(nextValue)
        elif isinstance(x, conn.messageTypes['error']):
            print (x, file=sys.stderr)
        elif verbose:
            print (x)

    # Register it and connect
    conn.registerAll(processInput)
    conn.connect()

    # Sleep for 1 second.
    sleep(1)

    # Request data from server
    endtime = "%s 20:00:00" % hint_date
    ticker_id = 1
    conn.reqHistoricalData(
        tickerId=ticker_id,
        contract=make_contract(hint_sym),
        endDateTime=endtime,
        durationStr='1 D',
        barSizeSetting='1 min',
        whatToShow='TRADES',
        useRTH=0,
        formatDate=1)

    def on_complete():
        conn.cancelHistoricalData(tickerId=ticker_id)
        conn.disconnect()
        e.set()

    # Register on observable to hear "Complete" event.
    retObservable.subscribe(None, None, on_complete)

    # Wait until data completed
    e.wait()

    return retObservable.as_observable()
