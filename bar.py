from collections import namedtuple
from ib_bars import BarsService
bars_service = BarsService()
from csv_templates import *
from refactoring_main import OPTIONS

class Bar(namedtuple("Bar", [
    "open",
    "close",
    "high",
    "low",
    "date",
    "volume"
])):
    def __init__(self, *args, **kargs):
        super(Hint, self).__init__()

    def __getitem__(self, key):
        if key in self._fields:
            return getattr(self, key)
        return super(Hint, self).__getitem__(key)

    def isDefensivePattern(self, hint, bars, defend, OPTIONS):
        i  = self.index
        scale = options['num_of_bars_to_peak']
        lowOrHigh = hint.position
        if bars[i-sacle].isPeak(hint,bars,scale):
            if lowOrHigh * (bars[i-scale][lowOrhigh] - defend) > 0:
                defend = bars[i-scale]
        return defend

    def isPeak(self,hint,bars,scale,OPTIONS):
        i = self.index
        if hint.isLong:
            if self.low < #list of bars. deafault example: [bars[i-1],bars[i+1]]
