from collections import namedtuple
from ib_bars import BarsService, QueryDuration
from raw_hint import RawHint
from datetime import datetime,timedelta
class Bar(namedtuple("Bar", [
    "open",
    "close",
    "high",
    "low",
    "date",
    "volume",
    "count",
    "hasGaps",
    "WAP",
])):
    def __init__(self, *args, **kargs):
        super(Bar, self).__init__()
        self._bars_service = BarsService.instance()

    def __getitem__(self, key):
        if key in self._fields:
            return getattr(self, key)
        return super(Bar, self).__getitem__(key)

    def isAfterHintTime(self, hint, hint_timeScale):
        if hint_timeScale:
            return self.date >= hint.time.replace(second=hint_timeScale, microsecond=0)

        return self.date >= hint.time.replace(microsecond=0)

    def isTriggerPriceReach(self, hint, entry_trigger):
        if hint.isLong:
            return self.high >= entry_trigger
        elif hint.isShort:
            return self.low <= entry_trigger

    def isNotAgressive(self, hint, entry_trigger, options):
        if hint.isShort:
            return entry_trigger - self.high <= options['agressive_var']
        elif hint.isLong:
            return self.low - entry_trigger <= options['agressive_var']

    def isTriggerReach(self, hint, entry_trigger, hint_timeScale, options):
        if self.isInTimeWindow(hint,hint_timeScale):
            return (self.isTriggerPriceReach(hint, entry_trigger) and self.isNotAgressive(hint, entry_trigger, options))

    def isInTimeWindow(self,hint,hint_timeScale):
        return self.isAfterHintTime(hint,hint_timeScale) and self._isInTimeWindow(hint)

    def _isInTimeWindow(self,hint):
        return self.date < hint.time.replace(microsecond=0) + timedelta(hours=1)

    def isTargetReach(self,hint,target):
        if self.targetReach(hint,target):
            seconds_bar = self._bars_service.expand_bar(self.date, hint.sym, QueryDuration(minutes=1))
            for bar in seconds_bar:
                if bar.targetReach(hint,target,seconds_bar):
                    return bar, target
        else:
            return False

    def targetReach(self,hint,target,seconds_bar=None):
        if seconds_bar:
            hint_time = hint.time.replace(microsecond=0)
        else:
            hint_time = hint.time.replace(second=0,microsecond=0)
        if self.date >= hint_time:
            if hint.isLong:
                if self.high >= target:
                    return self
            elif hint.isShort:
                if self.low <= target:
                    return self
        else:
            return False

    def defendReach(self,hint,defend,seconds_bar=None):
        if seconds_bar:
            hint_time = hint.time.replace(microsecond=0)
        else:
            hint_time = hint.time.replace(second=0,microsecond=0)
        if self.date >= hint_time:
            if hint.isLong:
                if self.low <= defend:
                    return self
            elif hint.isShort:
                if self.high >= defend:
                    return self
        else:
            return False

    def isDefendReach(self,hint,defend):
        if self.defendReach(hint,defend):
            seconds_bar = self._bars_service.expand_bar(self.date, hint.sym, QueryDuration(minutes=1))
            for bar in seconds_bar:
                if bar.defendReach(hint,defend,seconds_bar):
                        return bar, defend



'''
    def isDefensivePattern(self, hint, bars, defend, options):
        i  = self.index
        scale = options['num_of_bars_to_peak']
        lowOrHigh = # Todo: continue
        if bars[i-sacle].isPeak(hint,bars,scale):
            if lowOrHigh * (bars[i-scale][lowOrHigh] - defend) > 0:
                defend = bars[i-scale]
        return defend

    def isPeak(self,hint,bars,scale,OPTIONS):
        i = self.index
        if hint.isLong:
            if self.low < #list of bars. deafault example: [bars[i-1],bars[i+1]]

'''