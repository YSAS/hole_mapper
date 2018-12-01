class Fiber(object):
    def __init__(self, name=None, cassette=None, fnum=None, target=None):
        """name = e.g. R3-14"""
        self.target=target
        if name:
            if type(name)==Fiber:
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
    def number128(self):
        return self.cassette_num*16+self.number

    @property
    def color(self):
        return self.name[0].lower()
    
    @property
    def side(self):
        return self.color
    
    @property
    def is_r(self):
        return self.color=='r'

    @property
    def is_b(self):
        return self.color=='b'

    @property
    def cassette_num(self):
        return int(self.name[1])
    
    @property
    def cassette_name(self):
        return self.name[:2]+('h' if self.number>8 else 'l')
