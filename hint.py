from collections import namedtuple
from ib_bars import BarsService
bars_service = BarsService()
from csv_templates import *
from refactoring_main import OPTIONS


class Hint(namedtuple("Hint", [
    "sym",
    "position",
    "price",
    "stop",
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
    def hasDirection(self):
        return self.isLong or self.isShort

    @property
    def hasUnreasonableStop(self):
        if self.isLong:
            return self.stop > self.price
        elif self.isShort:
            return self.stop < self.price
        return False

    def entryQuery(self,bars,entry_trigger,bars_service=bars_service):
        error_processed_hint = None
        entry_bar = self._entryQuery(self,bars,entry_trigger)
        if entry_bar:
            seconds_bar = bars_service.expand_bar(entry_bar.date, self.sym, QueryDuration(minutes=1))
            entry_bar = self._entryQuery(self,seconds_bar,entry_trigger,bars_service)
        else:
            error_processed_hint = processed_hint_template(self,options)
        return entry_bar, error_processed_hint

    def _entryQuery(self,bars,entry_trigger):
        entry_bar = None
        if len(bars) == 60:
            hint_timeScale = 'second'
        else:
            hint_timeScale = 0
            for bar in bars:
                 if bar.isTriggerReach(self,entry_trigger,hint_timeScale):
                     entry_bar = bar
            return entry_bar

    def returningHintsTest(hint, processed_hints, options):
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

    def importBars(hint, bars_service, counter):
        bars = bars_service.get_bars_list(hint)
        counter = counter + 1
        print("%d - %s" % (counter, hint['time']))
        # Check if error in importing bars
        if type(bars) is str:
            processed_hint = processed_hint_template(hint, options, bars=bars)
            return bars, processed_hint, counter
        else:
            return bars, None, counter

    def __str__(self):
        return str(dict(self._asdict()))
