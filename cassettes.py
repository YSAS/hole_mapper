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


CASSETTE_NAMES=[c+str(i)+j for c in 'BR' for j in 'lh' for i in range(1,9)]
BLUE_CASSETTE_NAMES=['B'+str(i)+j for i in range(1,9) for j in 'hl']
RED_CASSETTE_NAMES=['R'+str(i)+j for i in range(1,9) for j in 'hl']

CASSETTE_POSITIONS=_init_cassette_positions()

class Cassette(object):
    def __init__(self, name, usable=None):
        assert 'h' in name or 'l' in name
        if usable == None and 'h' in name:
            self.usable=range(9,17)
        elif usable == None and 'l' in name:
            self.usable=range(1,9)
        else:
            self.usable=usable
        self.name=name
        self.pos=CASSETTE_POSITIONS[name]
        self.used=0
        self.targets=[]
        self.map={} #fiber # is key, target is value

#    def ordered_targets(self):
#        """ Return list of targets in order of fiber number """
#        return [self.map[fiber] for fiber in sorted(self.map.keys())]

    @property
    def n_avail(self):
        return len(self.usable)-self.used
    
    def reset(self):
        self.used=0
        self.targets=[]
        self.map={}

    def assign(self, target):
        """Add the hole to the cassette and assign the cassette to the hole"""
        if self.n_avail()==0:
            import ipdb;ipdb.set_trace()
            raise Exception('Cassette Full')

        if target.fiber:
            print "assigning hole with preset fiber"
            if target.fiber.cassette_name!=self.name:
                raise ValueError('target not compatible with cassette')
            if target.fiber.number in self.map:
                raise ValueError('preset fiber already mapped')
            self.map[target.fiber.number]=target
        else:
            target.assign(cassette=self.name)

        self.used+=1

        self.targets.append(target)

    def unassign(self, target):
        """
        Remove the hole from the cassette and unassign cassette from the hole
        """
        if target not in self.target:
            import ipdb;ipdb.set_trace()
            raise Exception('target not in cassette')
        self.used-=1
        self.targets.remove(target)
        for k in self.map.keys():
            if self.map[k]==hole:
                self.map.pop(k)
                break
        target.unassign()

    def label(self):
        """Return a string label for the cassette e.g. R1 1-8 or B3 1,4,7"""
        return self.name[0:2]+' '+rangify(sorted(self.map.keys()))

    def map_fibers(self, remap=False):
        """
        Associate targets with the individual fibers. Sets assignment for targets.
        """

        #assuming -x is to left
        if remap:
            for k in self.map.keys():
                if not self.map[k].preset_fiber:
                    self.map.pop(k)
    
        targs=[t for t in self.targets if t not in self.map.values()]
        targs.sort(key=operator.attrgetter('hole.x'), reverse=self.on_left)

        #assign the next fiber
        for t in targs:
            #Get next available fiber
            #min of self.usable not in self.map
            free=filter(lambda x: x not in self.map, self.usable)
            
            #assert len(free)>0
            if len(free)==0:
                import ipdb;ipdb.set_trace()
            
            num=min(free)
            
            #Assign pair in the cassette map
            self.map[num]=t
            
            #Tell the hole its fiber
            t.assign(fiber=Fiber(cassette=self.name,fnum=num))

    @property
    def on_left(self):
        return not self.onRight()

    @property
    def on_right(self):
        side=int(self.name[1]) % 2  != 0
        assert side == (self.pos[0] < 0)
        return side

    def get_target(self, fiber):
        assert fiber.cassette_name==self.name
        return self.map.get(fiber.number,None)

class CassetteConfig(object):
    """ A set of M2FS cassettes"""
    def __init__(self, usable=None, usableR=None, usableB=None):
        if usable:
            assert len(usable)==16
            assert not usableR
            assert not usableB
            usableR=usableB=usable
        else:
            if not usableR:
                usableR=(True,)*16
            if not usableB:
                usableB=(True,)*16

        assert len(usableR)==16
        assert len(usableB)==16

        fiber_stat=databasegetter.get_fiber_staus()
        
        self._cassettes=[]
        for name in RED_CASSETTE_NAMES:
            use=[usableR[i] and fiber_stat[name][i] for i in range(16)]
            self._cassettes.append(Cassette(name, use))
        for name in BLUE_CASSETTE_NAMES:
            use=[usableB[i] and fiber_stat[name][i] for i in range(16)]
            self._cassettes.append(Cassette(name, use))


    def __iter__(self):
        return iter(self._cassettes)

    @property
    def n_r_usable(self):
        return sum(len(c.usable) for c in self if c.name in RED_CASSETTE_NAMES)

    @property
    def n_b_usable(self):
        return sum(len(c.usable) for c in self if c.name in BLUE_CASSETTE_NAMES)

    def reset(self):
        """ Reset the cassettes (undo any assignments) """
        for c in self:
            c.reset()

    def assign(self, target, cassette_name):
        """ Assign target to a cassette fiber to target """
        cass=[c for c in self if c.name == cassette_name][0]
        cass.assign(t)

    def map(self, remap=False):
        for c in self:
            c.map_fibers(remap=remap)

    def condense(self):
        _condense_cassette_assignemnts([c for c in self if c.on_left])
        _condense_cassette_assignemnts([c for c in self if c.on_right])

    def rejigger(self):
        _rejigger_cassette_assignemnts([c for c in self if c.on_left])
        _rejigger_cassette_assignemnts([c for c in self if c.on_right])

def _condense_cassette_assignemnts(cassettes):
    #Grab cassettes with available fibers
    non_full=[c for c in cassettes if c.n_avail >0 and c.used>0]
              
    to_check=list(non_full)
    to_check.sort(key= lambda x: x.n_avail())
    
    while to_check:
        
        trial=to_check.pop()
        
        #Try to reassign all holes to non full cassettes
        targets=list(trial.targets)
        for t in targets:
            #If hole can't be assigned then screw it
            if not t.is_assignable:
                break
            #Try assigning the hole to another tetris
            recomp_non_full=False
            for c in non_full:
                if t.is_assignable(cassette=c):
                    trial.unassign(t)
                    c.assign(t)
                    recomp_non_full=True
                    break
            if recomp_non_full:
                #Redetermine what is full
                recomp_non_full=False
                non_full=[c for c in non_full if c.n_avail>0]
    
        #If we have emptied the cassette then don't add anything to it
        if trial.used == 0:
            try:
                non_full.remove(trial)
            except ValueError,e:
                #it is possible that trial filled up, was dropped from non_full
                # or something like that
                pass
        
        #Update sort of to check
        to_check.sort(key= lambda x: x.n_avail)

def _rejigger_cassette_assignemnts(cassettes):
    """Go through the cassettes swapping holes to eliminate
    verticle excursions
    """
    cassettes.sort(key=lambda c: c.pos[1])
    
    for i in range(len(cassettes)-1):
        cassette=cassettes[i]
        higer_cassettes=cassettes[i:]

        swappable_cassette_targets=[t for t in cassette.targets
                                    if t.is_assignable]

        swappable_higher_targets=[t for c in higer_cassettes
                                    for h in c.targets
                                    if t.is_assignable(cassette=cassette)]
        if len(swappable_higher_targets) ==0:
            continue
        
        targets=swappable_cassette_targets+swappable_higher_targets
        targets.sort(key=operator.attrgetter('hole.y'))
        
        #Find index of lowest target not in the cassette
        sort_ndxs=[targets.index(t) for t in swappable_cassette_targets]
        first_higher_ndx=len(sort_ndxs)
        for i in range(len(sort_ndxs)):
            if i not in sort_ndxs:
                first_higher_ndx=i
                break
        
        #For targets not at start of sorted list
        for i in sort_ndxs:
            if i > first_higher_ndx:
                low_target=targets[i]
                #attempt exchange with lower holes
                for j in range(first_higher_ndx, i):
                    #nb high cassette might be same
                    high_cassette=[c for c in cassettes
                                   if c.name==targets[j].assigned_cassette][0]
                    if high_cassette==cassette:
                        continue
                    if (targets[j].is_assignable(cassette=cassette) and
                        low_target.is_assignable(cassette=high_cassette)):
                        #Unassign
                        high_cassette.unassign(targets[j])
                        cassette.unassign(low_target)
                        #Assign
                        high_cassette.assign(low_target)
                        cassette.assign(targets[j])
                        break

