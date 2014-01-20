from coordinate import RA,Dec
from dimensions import PLATE_TARGET_RADIUS_LIMIT
from copy import copy, deepcopy

SH_TYPE='C'
STANDARD_TYPE='Z'
GUIDE_TYPE='G'
ACQUISITION_TYPE='A'
TARGET_TYPE='T'
SKY_TYPE='S'
GUIDEREF_TYPE='R'
FIDUCIAL_TYPE='F'
THUMBSCREW_TYPE='B'

VALID_TYPE_CODES=['T', 'S', 'C', 'G', 'A', 'Z','O']

class Target(object):
    def __init__(self, **kwargs):
        """ 
        hole should be a single hole or a list of holes with the primary hole first
        """
        self.ra=RA(kwargs.pop('ra',0.0))
        self.dec=Dec(kwargs.pop('dec',0.0))
        self.epoch=float(kwargs.pop('epoch',2000.0))
        self.pm_ra=kwargs.pop('pm_ra',0.0)
        self.pm_dec=kwargs.pop('pm_dec',0.0)
        self.id=kwargs.pop('id','')
        self.priority=float(kwargs.pop('priority',0.0))
        self.type=kwargs.pop('type','')
        self.field=kwargs.pop('field',None)
        
        if self.type==STANDARD_TYPE:
            self.id='STANDARD'
        elif self.type==FIDUCIAL_TYPE:
            self.id='FIDHOLE'
        elif self.type==THUMBSCREW_TYPE:
            self.id='THUMBSCREW'
        
        hole=kwargs.pop('hole',None)
        if type(hole)==list:
            self.hole=hole[0]
            self.additional_holes=hole[1:]
        else:
            self.hole=hole
            self.additional_holes=[]
        
        self.user=kwargs.pop('user',{})

        self.conflicting=None

        if not self.is_sh:
            for h in self.holes():
                h.target=self

        #Fiber
        self.preset_fiber=kwargs.pop('fiber',None)
        if type(self.preset_fiber)==str:
            self.preset_fiber=Fiber(self.preset_fiber)
        self.fiber=self.preset_fiber
        
        #Cassette Restrictions
        pucn=kwargs.pop('usable_cassettes','').split(',')
        self.preset_usable_cassette_names=set(map(lambda x: x.strip().lower(),
                                                  pucn))
        self.usable_cassette_names=self.preset_usable_cassette_names.copy()

    def __str__(self):
        return '{} ({}, {}) type={}'.format(self.id,self.ra.sexstr,
                                         self.dec.sexstr,self.type)
    
    def __setattr__(self, name, value):
        """ Override to update cassette distances when hole is set """
        if name=='hole':
            object.__setattr__(self, name, value)
            dists={c:self.hole.distance(cp)
                   for c, cp in Cassette.cassette_positions.iteritems()}
            object.__setattr__(self, '_cassette_distances', dists)
        else:
            object.__setattr__(self, name, value)
    
    def holes(self):
        if self.hole:
            return [self.hole]+self.additional_holes
        else:
            return self.additional_holes

    @property
    def conflicting_ids(self):
        if not self.conflicting:
            return ''
        if type(self.conflicting)==type(self):
            return self.conflicting.id
        else:
            ret=[]
            for ct in self.conflicting:
                if ct.field:
                    ret.append('{}:{}'.format(ct.field.name, ct.id))
                else:
                    ret.append(ct.id)
            return ', '.join(ret)

    @property
    def on_plate(self):
        if not self.hole:
            return False
        else:
            return ((self.hole.x**2 + self.hole.y**2)<
                    PLATE_TARGET_RADIUS_LIMIT**2)

    @property
    def info(self):
        """Does not include hole info"""
        ret={'id':self.id,
             'ra':self.ra.sexstr,
             'dec':self.dec.sexstr,
             'epoch':'{:6.1f}'.format(self.epoch),
             'priority':'{:.2f}'.format(self.priority),
             'type':self.type}
        if self.fiber:
            ret['fiber']=self.fiber.name
        if self.field:
            ret['field']=self.field.name
        if self.conflicting:
            ret['conflicts']=self.conflicting_ids

        ret.update(self.user)

        return ret

    @property
    def is_standard(self):
        return self.type==STANDARD_TYPE

    @property
    def is_sky(self):
        return self.type==SKY_TYPE

    @property
    def is_sh(self):
        return self.type==SH_TYPE

    @property
    def is_guide(self):
        return self.type==GUIDE_TYPE

    @property
    def is_target(self):
        return self.type==TARGET_TYPE

    @property
    def is_acquisition(self):
        return self.type==ACQUISITION_TYPE

    @property
    def is_assigned(self):
        return self.fiber!=None

    @property
    def plug_priority(self):
        """
        Return number indicating if hole should be assigned a fiber sooner
        or later (lower)
        """
        if self.cassette:
            return 0.0 #Don't care, we've already been assigned to a cassette
        else:
            #TODO: Should this be normalized by the number of usable cassettes
            return sum(self.distance_to_cassette(c)
                       for c in self.usable_cassette_names)

    @property
    def nearest_usable_cassette(self):
        """Return name of nearest usable cassette """
        if len(self.usable_cassette_names)==1:
            return self.usable_cassette_names[0]
        
        usable=[(c, self.distance_to_cassette(c))
                for c in self.usable_cassette_names]
                
        return min(usable, key=operator.itemgetter(1))[0]

    def reset_assignment(self):
        self.fiber=copy(self.preset_fiber)
        self.usable_cassette_names=self.preset_usable_cassette_names.copy()

    @property
    def cassette_name(self):
        """Return the cassette or None if one isnt assigned"""
        if self.fiber:
            return self.fiber.cassette.name
        elif len(self.usable_cassettes)==1:
            return self.usable_cassette_names[0]
        else:
            return None

    def is_assignable(self, cassette=None, fiber=None):
        """
        True iff target can be (re)assigned, optionally to specified cassette
        or fiber.
        Targets without holes and targets with user assignments are never
        assignable.
        Do not specify both cassette and fiber
        """
        if self.preset_fiber:
            return False
        if cassette or fiber:
            if cassette:
                name=cassette.name
            if fiber:
                name=fiber.cassette.name
            if self.preset_usable_cassette_names:
                #we are asking is R or R8 in R8l or B4h in B4l, etc.
                # assignment can be more or less specific as desired
                x=filter(lambda x: x in name, self.preset_usable_cassette_names)
                ret=len(x)>0
            #TODO: Sort this out
            ret&=cassette.slit_compatible(self)
            return
        else:
            return True
            
    def distance_to_cassette(self, cassette_name):
        """ return the distance to the cassette """
        return self._cassette_distances[cassette]

#TODO: everything after here

    def assign_possible_cassettes_by_name(self, cassette_names,
                                          update_with_intersection=False):
        """
        Add cassettes to the list of possible cassettes usable with hole.
        If update_with_intersection is set, intersection of cassettes 
        cand previously set possible cassettes is used as the set of 
        possibles
        """
        if type(cassette_names)!=list :
            raise TypeError('casssettes must be a list of cassette names')
        if self.fiber:
            raise Exception('Fiber already assigned')
        if self.cassette_name:
            raise Exception('Cassette already assigned')

        #If no possibles have ever been set, set and finish
        if not self.usable_cassette_names:
            #TODO: What about if the pool dwindles to nothing we shouldn't
            # start over!
            self.usable_cassette_names=set(cassettes)
            return

        #Otherwise update the list of possibles
        if update_with_intersection:
            self.usable_cassette_names.intersection_update(cassette_names)
        else:
            self.usable_cassette_names.update(cassette_names)
            if self.preset_usable_cassette_names:
                self.usable_cassette_names.intersection_update(
                    self.preset_usable_cassette_names)

        assert len(self.usable_cassette_names)>0 #See above todo

