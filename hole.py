import dimensions
import math
class Hole(object):
    def __init__(self, x=0.0,y=0.0,z=0.0,d=0.0, target=None):
        self.x=x
        self.y=y
        self.z=z
        self.d=d
        self.target=target
        assert d != 0.0
    
    def __hash__(self):
        return "{}{}{}{}".format(self.x, self.y, self.z, self.d).__hash__()

    @property
    def info(self):
        ret={'x':'{:.5f}'.format(self.x),
             'y':'{:.5f}'.format(self.y),
             'z':'{:.5f}'.format(self.z),
             'd':'{:.5f}'.format(self.d)}
        if self.target:
            ret.update(self.target.info)
        return ret

    def distance(self,(x,y)):
        return math.hypot(self.x-x,self.y-y)
