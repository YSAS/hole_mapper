import numpy as np
import operator

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


def _init_cassette_positions():
    """
    left:
    B1h
    B1l
    R1h
    R1l
    
    B3
    R3
    
    B5
    R5
    B7
    R7
    
    right:
    B2
    R2
    ...
    B8
    R8
    """
    
    #Each cassette (half-cassette?) has a vertex on the plate nominally
    # corresponding to the natural location where the fibers want to go
    # for startes we will model that as alternating red and blue
    # y coordinates distributed evenly, x coordinates s.t. it is on the plate radius
    # evenly dividing area, - for left side, pos for right
    
    #left are at (-x,y) & right @ (x,y)
    _cassette_positions={}
    r=np.sqrt(.5) #enclose half area
    y=np.linspace(r, -r, 16+2)[1:-1]
    x=np.sqrt(r**2 - y**2)
    leftlabels=[c+str(i)+j for i in range(1,9,2) for c in 'BR' for j in 'hl']
    rightlabels=[c+str(i)+j for i in range(2,9,2) for c in 'BR' for j in 'hl']
    for i,l in enumerate(leftlabels):
        _cassette_positions[l]=(-x[i],y[i])
    for i,l in enumerate(rightlabels):
        _cassette_positions[l]=(x[i],y[i])

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
        self.slit=slit
        self.holes=[]
    
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
    
    def assign_hole(self, hole):
        """Add the hole to the cassette and assign the cassette to the hole"""
        self.consume()
        self.holes.append(hole)
        hole.assign_cassette(self.name)
    
    def assign_fiber(self, hole, skip_lower=False):
        """
        Associate hole with the next available fiber. Sets assignment for hole.
        
        Set skip_lower to start assignment with 9
        
        """
        #Get next available fiber
        #min of self.usable not in self.map
        if skip_lower:
            min_num=9
        else:
            min_num=0
        free=filter(lambda x: x not in self.map and x >= min_num, self.usable)
        
        assert len(free)>0
        
        num=min(free)
        
        #Assign pair in the cassette map
        self.map[num]=hole
        
        #Tell the hole its fiber
        hole.assign({'CASSETTE':self.name,
                     'FIBERNO':num})
    
    def n_upper_avail(self):
        return len(filter(lambda x:x>8, self.usable))
    
    def n_lower_avail(self):
        return len(self.usable)-self.n_upper_avail()
    
    def label(self):
        """Return a string label for the cassette e.g. R1 1-8 or B3 1,4,7"""
        return self.name+' '+rangify(sorted(self.map.keys()))

    def map_fibers(self):
        if max(self.n_upper_avail(),self.n_lower_avail()) < self.used:
            #divide into upper and lower groups
            #upper group gets upper fibers, lower gets lower, decide which gets
            #full set by whichever set (upper 8 vs lower 8) has smallest scatter
            #in y
            self.holes.sort(key=operator.attrgetter('y'))
            lower=self.holes[0:self.n_lower_avail()]
            upper=self.holes[self.n_lower_avail():]
        elif self.n_upper_avail() >= self.used:
            upper=self.holes
            lower=[]
        else:
            lower=self.holes
            upper=[]
        for holes in [lower, upper]: #assign the lower first (1-8 is on bottom??)
            #assuming -x is to left
            holes.sort(key=operator.attrgetter('x'), reverse=self.onRight())
            #assign the next fiber
            for h in holes:
                self.assign_fiber(h, skip_lower=len(lower)==0)


#    def map_fibers(self):
#        if max(self.n_upper_avail(),self.n_lower_avail()) < self.used:
#            #divide into upper and lower groups
#            #upper group gets upper fibers, lower gets lower, decide which gets
#            #full set by whichever set (upper 8 vs lower 8) has smallest scatter
#            #in y
#            self.holes.sort(key=operator.attrgetter('y'))
#            lower=self.holes[0:self.n_lower_avail()]
#            upper=self.holes[self.n_lower_avail():]
#        elif self.n_upper_avail() >= self.used:
#            upper=self.holes
#            lower=[]
#        else:
#            lower=self.holes
#            upper=[]
#        for holes in [lower, upper]: #assign the lower first (1-8 is on bottom??)
#            #assuming -x is to left
#            holes.sort(key=operator.attrgetter('x'), reverse=self.onRight())
#            #assign the next fiber
#            for h in holes:
#                self.assign_fiber(h, skip_lower=len(lower)==0)

    def onRight(self):
        return int(self.name[1]) % 2  == 0

def blue_cassette_names():
    return ['B'+str(i)+j for i in range(1,9) for j in 'hl']

def red_cassette_names():
    return ['R'+str(i)+j for i in range(1,9) for j in 'hl']

def new_cassette_dict(slitwid=180):
    return {side+str(i)+j: Cassette(side+str(i)+j, slitwid)
    for side in 'RB' for i in range(1,9) for j in 'hl'}
