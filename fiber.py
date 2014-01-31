class Fiber(object):
    def __init__(self, name=None, cassette=None, fnum=None, target=None):
        """name = e.g. R3-14"""
        self.target=target
        if name:
            if tyep(name)==Fiber:
                self.name=name.name
            else:
                self.name=name
        else:
            self.name='{}-{:02}'.format(cassette[:2],fnum)

    def __eq__(self, other):
        return self.name==other.name
    
    def __str__(self):
        return self.name

    @property
    def number(self):
        return int(self.name.split('-')[1])

    @property
    def color(self):
        return self.name[0].lower()

    @property
    def cassette_num(self):
        return int(self.name[1])
    
    @property
    def cassette_name(self):
        return self.name[:2]+('h' if self.number>8 else 'l')
