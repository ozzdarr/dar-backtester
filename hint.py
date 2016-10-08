from collections import namedtuple
from ib_bars import BarsService
from csv_templates import *
from ib_bars import QueryDuration

bars_service = BarsService()
OPTIONS = {
    "entry_var": 0.01,
    "stop_var": 0.01,
    "exit1to1_var": 0,
    "bar_size": 5,
    "exit_var": 0.01,
    "slippage": 0.02,
    'commission': 0,
    'max_defend_size': 1
}


class Hint(namedtuple("Hint", [
    "sym",
    "position",
    "price",
    "defend",
    "time"
])):
    def __init__(self, *args, **kargs):
        super(Hint, self).__init__()

    def __getitem__(self, key):
        if key in self._fields:
            return getattr(self, key)
        return super(Hint, self).__getitem__(key)

    @property
    def isLong(self):
        return self.position == 'long'

    @property
    def isShort(self):
        return self.position == 'short'

    @property
    def isCancel(self):
        return self.position == 'cancel'

    @property
    def defendSize(self):
        if self.isLong:
            return self.price - self.defend
        elif self.isShort:
            return self.defend - self.price

    @property
    def hasDirection(self):
        return self.isLong or self.isShort

    @property
    def hasUnreasonableStop(self):
        if self.isLong:
            return self.defend > self.price
        elif self.isShort:
            return self.defend < self.price
        return False

    @property
    def defaultDefend(self):
        if self.isLong:
            return self.price - ((self.price * 0.0033) + 0.05)
        elif self.isShort:
            return self.price + ((self.price * 0.0033) + 0.05)

    @property
    def hasNoDefend(self):
        return self.defend == 0

    @property
    def manipulateDefend(self):
        if self.hasNoDefend or self.hasBigStop:
            self.defend = self.defaultDefend
            return self

    @property
    def hasBigDefend(self, options=OPTIONS):
        return self.defendSize > options['max_defend_size']

    @property
    def entryQuery(self, bars, entry_trigger, bars_service):
        entry_bar = self._entryQuery(self, bars, entry_trigger)
        if entry_bar:
            seconds_bar = bars_service.expand_bar(entry_bar.date, self.sym, QueryDuration(minutes=1))
            entry_bar = self._entryQuery(self, seconds_bar, entry_trigger)
        return entry_bar

    @property
    def _entryQuery(self, bars, entry_trigger):
        entry_bar = None
        if len(bars) == 60:
            hint_timeScale = 'second'
        else:
            hint_timeScale = 0
        for bar in bars:
            if bar.isTriggerReach(self, entry_trigger, hint_timeScale):
                entry_bar = bar
        return entry_bar

    @property
    def returningHints(hint, processed_hints, options=OPTIONS, ignored_hint=None):

        for h in processed_hints:
            if h.hasDirection and h.isHintMatch(hint):
                if type(h['entryTime']) is str:
                    continue
                if hint['time'] < h['entryTime']:
                    h['entryTime'] = 'did not enter'
                    h['entryPrice'] = 'did not enter'
                    h['exitTime'] = 'did not enter'
                    h['exitPrice'] = 'did not enter'
                    h['netRevenue'] = 'did not enter'
                    if hint.hasDirection:
                        h['comment'] = 'Changed'
                    elif hint.isCancel:
                        h['comment'] = 'Canceled'
                    continue
                elif hint['time'] > h['exitTime']:
                    continue
                else:
                    ignored_hint = processed_hint_template(hint, options, error='Ignored')

        if ignored_hint:
            return ignored_hint
        else:
            return None

    @property
    def importBars(self, counter=0, bars_service=bars_service, options=OPTIONS):
        bars = bars_service.get_bars_list(self)
        counter += 1
        print("%d - %s" % (counter, self['time']))
        # Check if error in importing bars
        if type(bars) is str:
            processed_hint = processed_hint_template(self, options, bars=bars)
            return bars, processed_hint, counter
        else:
            return bars, None, counter

    def __str__(self):
        return str(dict(self._asdict()))
