class Fiber(object):
    def __init__(self, name=None, cassette=None, fnunm=None):
        """name = e.g. R3-14"""
        if name:
            if tyep(name)==Fiber:
                self.name=name.name
            else:
                self.name=name
        else:
            self.name='{}-{:02}'.format(cassette[:2],fnum)

    def __eq__(self, other):
        return self.name==other.name

    @property
    def number(self):
        return int(self.name.split('-')[1])

    @property
    def color(self):
        return self.name[0].lower()

    @property
    def cassette_num(self):
        return int(self.name[1])
    
    @propery
    def cassette_name(self):
        return self.name[:2]+('h' if self.fiber_num>8 else 'l')
