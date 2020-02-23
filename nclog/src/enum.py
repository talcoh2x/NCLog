

class Enum(object):

    """
    Enum functionality.
    """

    def __init__(self, *keys, **kwargs):
        self.str_val = kwargs.get('str_val')
        self.keys = keys
        self.values = []
        start_val = kwargs.get('start_val', 0)

        for i, key in enumerate(keys):
            if self.str_val:
                value = key
            else:
                value = i + start_val
            self.values.append(value)
            setattr(self, self.get_keys(key), value)

    @staticmethod
    def get_keys(string):
        return string.upper().replace(' ', '_')

    def get_value(self, key):
        if isinstance(key, int) and not self.str_val:
            return key
        return getattr(self, self.get_keys(key))
