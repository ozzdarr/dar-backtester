from collections import namedtuple

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

    def __getitem__(self, key):
        if key in self._fields:
            return getattr(self, key)
        return super(Bar, self).__getitem__(key)

    def isAfterHintTime(self, hint, hint_timeScale=None):
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
        if self.isAfterHintTime(hint,hint_timeScale):
            return (self.isTriggerPriceReach(hint, entry_trigger) and self.isNotAgressive(hint, entry_trigger, options))
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
                #Todo: continue
'''
