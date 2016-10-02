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

    def __str__(self):
        return str(dict(self._asdict()))
