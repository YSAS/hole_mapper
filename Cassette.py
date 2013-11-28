import numpy as np
import operator
from collections import defaultdict

def rangify(data):
    from itertools import groupby
    from operator import itemgetter
    str_list = []
    for k, g in groupby(enumerate(data), lambda (i,x):i-x):
        ilist = map(itemgetter(1), g)
        if len(ilist) > 1:
            str_list.append('%d-%d' % (ilist[0], ilist[-1]))
        else:
            str_list.append('%d' % ilist[0])
    return ', '.join(str_list)

def fiber2cassettename(fib):
    ret = fib[0:2]
    if int(fib.split('-')[1])>8:
        return ret+'h'
    else:
        return ret+'l'

def left_only(cassettes):
    if not cassettes:
        return type(cassettes)()
    if type(cassettes) == dict:
        return {k:v for k,v in cassettes.iteritems() if v.onLeft()}
    elif type(cassettes) in [list, tuple]:
        if type(cassettes[0])==Cassette:
            return [c for c in cassettes if c.onLeft()]
        else:
            #assume list of cassette names
            _cass=new_cassette_dict()
            return [c for c in cassettes if _cass[c].onLeft()]

def right_only(cassettes):
    if not cassettes:
        return type(cassettes)()
    if type(cassettes) == dict:
        return {k:v for k,v in cassettes.iteritems() if v.onRight()}
    elif type(cassettes) in [list, tuple]:
        if type(cassettes[0])==Cassette:
            return [c for c in cassettes if c.onRight()]
        else:
            #assume list of cassette names
            _cass=new_cassette_dict()
            return [c for c in cassettes if _cass[c].onRight()]

#in res and asc -x is on right looking at plate
def _init_cassette_positions():
    """
    right looking at plate:
    B1h 9-16
    B1l 1-8
    R1h
    R1l
    B3h 9-16
    B3l 1-8
    R3h
    R3l
    
    R5h 9-16
    R5l 1-8
    B5h
    B5l
    R7h 9-16
    R7l 1-8
    B7h
    B7l
  
    left looking at plate:
    R2l 1-8
    R2h 9-16
    B2l
    B2h
    R4l
    R4h
    B4l
    B4h
    
    B6l
    B6h
    R6l
    R6h
    Bhl
    B8h
    R8l
    R8h
    """
    
    #Each cassette (half-cassette?) has a vertex on the plate nominally
    # corresponding to the natural location where the fibers want to go
    # for startes we will model that as alternating red and blue
    # y coordinates distributed evenly, x coordinates s.t. it is on the plate radius
    # evenly dividing area
    #left side is on +x
    #right side is on -x
    
    _cassette_positions={}
    r=np.sqrt(.25) #enclose half area
    y=np.linspace(r, -r, 16+2)[1:-1]
    x=np.sqrt(r**2 - y**2)
    #    y=np.linspace(1, -1, 16+2)[1:-1]
    #    x=np.zeros(len(y))+.45
    rightlabels=([c+str(i)+j for i in range(1,5,2) for c in 'BR' for j in 'hl']+
                 [c+str(i)+j for i in range(5,9,2) for c in 'RB' for j in 'hl'])
    leftlabels=([c+str(i)+j for i in range(2,6,2) for c in 'RB' for j in 'lh']+
                [c+str(i)+j for i in range(6,9,2) for c in 'BR' for j in 'lh'])
    for i,l in enumerate(leftlabels):
        _cassette_positions[l]=(x[i],y[i])
    for i,l in enumerate(rightlabels):
        _cassette_positions[l]=(-x[i],y[i])

    return _cassette_positions

cassette_positions=_init_cassette_positions()


class Cassette(object):
    def __init__(self, name, slit, usable=None):
        assert 'h' in name or 'l' in name
        if usable == None and 'h' in name:
            self.usable=range(9,17)
        elif usable == None and 'l' in name:
            self.usable=range(1,9)
        else:
            self.usable=usable
        self.name=name
        self.map={} #fiber # is key, hole is value
        self.pos=cassette_positions[name]
        self.used=0
        self._defaultslit=slit #This is for now, in the future we might just
        #set the slits for the holes and see what happens
        self._slit=defaultdict(lambda:_defaultslit)
        self.holes=[]
    
    def slit(self,setup):
        return self._slit[setup]
    
    def color(self):
        if self.name[0]=='R':
            return 'red'
        else:
            return 'blue'

    def first_hole(self):
        return self.map[min(self.map)]

    def last_hole(self):
        return self.map[max(self.map)]

    def ordered_holes(self):
        """
        Return list of holes in order of fiber number
        """
        return [self.map[fiber] for fiber in sorted(self.map.keys())]

    def n_avail(self):
        return len(self.usable)-self.used
    
    def consume(self):
        self.used+=1
        assert self.used <= len(self.usable)
    
    def reset(self):
        self.used=0
        self.holes=[]
        self.map={}
        self._slit=defaultdict(lambda:_defaultslit)
    
    def slit_compatible(self, hole):
        """ true if the holes slit matches the slit for the holes setup"""
        slit=self._slit[hole['SETUP']]
        return (slit==-1) or (slit==hole['SLIT'])
    
    def assign_hole(self, hole):
        """Add the hole to the cassette and assign the cassette to the hole"""
        if self.n_avail()==0:
            import pdb;pdb.set_trace()
            raise Exception('Cassette Full')
        self.consume()
        self.holes.append(hole)
        hole.assign_cassette(self.name)

    def unassign_hole(self, hole):
        """
        Remove the hole from the cassette and unassign cassette from the hole
        """
        if hole not in self.holes:
            import pdb;pdb.set_trace()
            raise Exception('Hole not in cassette')
        self.used-=1
        self.holes.remove(hole)
        for k in self.map.keys():
            if self.map[k]==hole:
                self.map.pop(k)
        hole.unassign()

    def _assign_fiber(self, hole):
        """
        Associate hole with the next available fiber. Sets assignment for hole.
        """
        #Get next available fiber
        #min of self.usable not in self.map
        free=filter(lambda x: x not in self.map, self.usable)
        
        assert len(free)>0
        
        num=min(free)
        
        #Assign pair in the cassette map
        self.map[num]=hole
        
        #Tell the hole its fiber
        hole.assign({'CASSETTE':self.name, 'FIBERNO':num})

    def label(self):
        """Return a string label for the cassette e.g. R1 1-8 or B3 1,4,7"""
        return self.name[0:2]+' '+rangify(sorted(self.map.keys()))

    def map_fibers(self, remap=False):
        #assuming -x is to left
        self.holes.sort(key=operator.attrgetter('x'), reverse=not self.onRight())
        if remap:
            self.map={}
        #assign the next fiber
        for h in self.holes:
            self._assign_fiber(h)

    def onLeft(self):
        return not self.onRight()

    def onRight(self):
        side=int(self.name[1]) % 2  != 0
        assert side == (self.pos[0] < 0)
        return side

    def get_hole(self, fiber):
        return self.map.get(int(fiber.split('-')[1]),None)

def blue_cassette_names():
    return ['B'+str(i)+j for i in range(1,9) for j in 'hl']

def red_cassette_names():
    return ['R'+str(i)+j for i in range(1,9) for j in 'hl']

def new_cassette_dict(slitwid=180):
    return {side+str(i)+j: Cassette(side+str(i)+j, slitwid)
    for side in 'RB' for i in range(1,9) for j in 'hl'}
