
# adapted from http://stackoverflow.com/a/3603824/6285007
class FrozenClass(object):
    '''FrozenClass: prevents adding new attributes to class outside of __init__'''
    __isfrozen = False
    def __setattr__(self, key, value):
        if self.__isfrozen and not hasattr(self, key):
            raise TypeError( "{cls} has no attribute {attr}".format(cls= self.__class__.__name__, attr= key) )
        object.__setattr__(self, key, value)

    def _freeze(self):
        self.__isfrozen = True

    def _unfreeze(self):
        self.__isfrozen = False
