import dimensions

class Hole(object):
    def __init__(self, x=0.0,y=0.0,z=0.0,r=0.0, target=None):
        self.x=x
        self.y=y
        self.z=z
        self.r=r
        self.target=target
        assert r != 0.0
    
    def __hash__(self):
        return "{}{}{}{}".format(self.x, self.y, self.z, self.r).__hash__()


    @property
    def info(self):
        ret={'x':'{:.5f}'.format(self.x),
             'y':'{:.5f}'.format(self.y),
             'z':'{:.5f}'.format(self.z),
             'r':'{:.5f}'.format(self.r)}
        if self.target:
            ret.update(self.target.info)
        return ret

SHACKHARTMAN_HOLE=Hole(r=dimensions.SH_RADIUS)

