from collections import namedtuple

class ProcessedHint(namedtuple("ProcessedHint", [
    "hintTime",
    "symbol",
    "hintTrigger",
    "hintDirection",
    "hintStop",
    "entryTime",
    "entryPrice",
    "exitTime",
    "exitPrice",
    "netRevenue",
    "slippage",
    "comment"
])):
    def __init__(self, *args, **kargs):
        super(ProcessedHint, self).__init__()
        self._values = dict(self._asdict())

    def __getitem__(self, key):
        if key in self._fields:
            return self._values[key]
        return super(ProcessedHint, self).__getitem__(key)

    def __setitem__(self, key, value):
        if key in self._fields:
            self._values[key] = value
            return
        setattr(self, key, value)

    def isHintMatch(self, hint):
        return (self.symbol == hint['sym']) and \
               (self.hintTime.date() == hint['time'].date())

    @property
    def isLong(self):
        return self.hintDirection == 'long'

    @property
    def isShort(self):
        return self.hintDirection == 'short'

    @property
    def isCancel(self):
        return self.hintDirection == 'cancel'

    @property
    def hasDirection(self):
        return self.isLong or self.isShort

    @property
    def asDict(self):
        return self._values

    def __str__(self):
        return str(self.asDict)
