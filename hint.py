from collections import namedtuple


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
        
    def stopSize(self):
        if hint.isLong:
            stop_size = self.price - self.stop
        elif hint.isShort:
            stop_size =  self.stop - self.price
        return stop_size
    
    def target(self):
        if hint.isLong:
            target = self.stop_size + self.price #+ options['exit_var'] + 2*slippage + commission
        elif hint.isShort:
            target = hint.price - stop_size #- options['exit_var'] - 2*slippage - commission
        return target
        
    def __str__(self):
        return str(dict(self._asdict()))
