from collections import namedtuple
from ib_bars import BarsService
from csv_templates import *
from ib_bars import QueryDuration


class Hint(namedtuple("Hint", [
    "id",
    "sym",
    "position",
    "price",
    "defend",
    "time"
])):
    def __init__(self, *args, **kargs):
        super(RawHint, self).__init__()
        self._bars_service = BarsService.instance()

    def __getitem__(self, key):
        if key in self._fields:
            return getattr(self, key)
        return super(RawHint, self).__getitem__(key)

    def __setitem__(self, key, value):
        if key in self._fields:
            self._values[key] = value
            return
        setattr(self, key, value)


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
    def defaultTarget(self):
        if self.isLong:
            return self.price + self.defendSize
        elif self.isShort:
            return self.price - self.defendSize


    @property
    def hasNoDefend(self):
        return self.defend == 0


    def entryTrigger(self, options):
        if self.isLong:
            return self.price + options['entry_var']
        elif self.isShort:
            return self.price - options['entry_var']


    def manipulateDefend(self, options):
        if self.hasNoDefend or self.hasBigDefend(options):
            self.defend = self.defaultDefend
            return self


    def hasBigDefend(self, options):
        return self.defendSize > options['max_defend_size']


    def entryQuery(self, bars, entry_trigger, options):
        entry_bar = self._entryQuery(bars, entry_trigger, options)
        if entry_bar and type(entry_bar) is not str:
            seconds_bar = self._bars_service.expand_bar(entry_bar.date, self.sym, QueryDuration(minutes=1))
            if type(seconds_bar) is str:
                return seconds_bar

            entry_bar = self._entryQuery(seconds_bar, entry_trigger, options)
        return entry_bar


    def _entryQuery(self, bars, entry_trigger, options):
        entry_bar = None
        if len(bars) == 60:
            hint_timeScale = None
        else:
            hint_timeScale = 0
        for bar in bars:
            if bar.isTriggerReach(self, entry_trigger, hint_timeScale, options):
                entry_bar = bar
        return entry_bar


    def returningHints(hint, processed_hints, options, ignored_hint=None):
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


    def importBars(self, options):
        bars = self._bars_service.get_bars_list(self)
        print("%d - %s" % (self['id'], self['time']))
        # Check if error in importing bars
        if type(bars) is str:
            processed_hint = processed_hint_template(self, options, bars=bars)
            return bars, processed_hint
        else:
            return bars, None


    def __str__(self):
        return str(dict(self._asdict()))