from jbastro.astrolibsimple import sexconvert
class RA(float):
    def __new__(self, value):
        return float.__new__(self, sexconvert(value,dtype=float,ra=True))
    
    @property
    def sexstr(self):
        return sexconvert(float(self),dtype=str,ra=True)

    @property
    def float(self):
        return float(self)

class Dec(float):
    def __new__(self, value):
        return float.__new__(self, sexconvert(value,dtype=float,ra=False))
    
    @property
    def sexstr(self):
        return sexconvert(float(self),dtype=str,ra=False)

    @property
    def float(self):
            return float(self)

