from coordinate import RA,Dec
from dimensions import PLATE_TARGET_RADIUS_LIMIT, SH_RADIUS
from copy import copy, deepcopy
from cassettes import CASSETTE_POSITIONS
from hole import Hole
import operator
from logger import getLogger
from fiber import Fiber

log=getLogger('target')

SH_TYPE='C'
STANDARD_TYPE='Z'
GUIDE_TYPE='G'
ACQUISITION_TYPE='A'
TARGET_TYPE='T'
SKY_TYPE='S'
GUIDEREF_TYPE='R'
FIDUCIAL_TYPE='F'
THUMBSCREW_TYPE='B'

VALID_TYPE_CODES=['T', 'S', 'C', 'G', 'A', 'Z','O','F','B','R','I','U']

class ConflictDummy(object):
    """Dummy conflict type for things like off edge of plate"""
    def __init__(self, id=''):
        self.type=''
        self.id=id
        class obj(object):
            pass
        self.field=obj
        self.field.name=''


class Target(object):
    def __init__(self, **kwargs):
        """ 
        hole should be a single hole or a list of holes with the primary hole first
        """
        #self.setup is reserved for adding by the setup class as needed
        
        self.ra=RA(kwargs.pop('ra',0.0))
        self.dec=Dec(kwargs.pop('dec',0.0))
        self.epoch=float(kwargs.pop('epoch',2000.0))
        self.pm_ra=float(kwargs.pop('pm_ra',0.0))
        self.pm_dec=float(kwargs.pop('pm_dec',0.0))
        self.id=kwargs.pop('id','')
        self.priority=float(kwargs.pop('priority',0.0))
        self.type=kwargs.pop('type','')
        self.field=kwargs.pop('field',None)
        
        # self.fm_priority_tmp is reserved for fieldmanager.py use
        
#        if self.type==STANDARD_TYPE and self.id='':
#            self.id='STANDARD'
        if self.type==FIDUCIAL_TYPE:
            self.id='FIDHOLE'
        elif self.type==THUMBSCREW_TYPE:
            self.id='THUMBSCREW'
        
        self._hole=None
        self._additional_holes=[]
        hole=kwargs.pop('hole',None)
        if type(hole)==list:
            self.hole=hole[0]
            self.additional_holes=hole[1:]
        else:
            self.hole=hole
            self.additional_holes=[]
        
        if hole==None:
            try:
                self.hole=Hole(float(kwargs.pop('x')),
                               float(kwargs.pop('y')),
                               float(kwargs.pop('z')),
                               float(kwargs.pop('d')),target=self)
            except KeyError:
                pass
        
    
        if self.type==SH_TYPE:
            self.hole=Hole(d=2*SH_RADIUS)
            self.additional_holes=[]
    
        self.user=kwargs.pop('user',{})

        self._conflicting=set()
        
        #Slit
#        self.slit=kwargs.pop('slit',None)

        #Setup
#        self.setup=kwargs.pop('setup',None)

        #Fiber
        self.preset_fiber=self.user.pop('fiber',None)
        if type(self.preset_fiber)==str:
            self.preset_fiber=Fiber(self.preset_fiber)
        self.fiber=self.preset_fiber
    
        #Cassette
        self._assigned_cassette_name=None
        
        #Cassette Restrictions
        pucn=kwargs.pop('usable_cassettes','').split(',')
        self._preset_usable_cassette_names=set(map(lambda x: x.strip().lower(),
                                                  pucn))
        self._usable_cassette_names=self._preset_usable_cassette_names.copy()
            
    def __str__(self):
        return '{} ({}, {}) t={} p={}'.format(self.id,self.ra.sexstr,
                                         self.dec.sexstr,self.type,
                                         self.priority)
    
    def assign(self, cassette=None, fiber=None):
        if cassette:
            assert self.fiber==None
            assert cassette in self._preset_usable_cassette_names
            self._assigned_cassette_name=cassette
        else:
            assert fiber !=None
            if self.preset_fiber:
                assert self.preset_fiber.name==fiber.name
            else:
                assert fiber.cassette_name in self._preset_usable_cassette_names
            self.fiber=fiber
            self._assigned_cassette_name=fiber.cassette_name
            
    def unassign(self):
        if self.preset_fiber:
            raise Exception('User assignments are irrevocable')
        else:
            self.fiber=None
            self._assigned_cassette_name=None

    @property
    def conflicting(self):
        try:
            ret=self._conflicting.pop()
            self._conflicting.add(ret)
        except KeyError:
            ret=None
        return ret
    
    @conflicting.setter
    def conflicting(self, targets):
        if type(targets)==type(None):
            targets=[]
        if type(targets)==set:
            self._conflicting=targets
        elif type(targets) in [list, tuple]:
            self._conflicting=set(targets)
        else:
            self._conflicting=set([targets])
    
    @property
    def hole(self):
        return self._hole
    
    @hole.setter
    def hole(self, hole):
        self._hole=hole
        if hole:
            dists={c:self._hole.distance(cp)
                    for c, cp in CASSETTE_POSITIONS.iteritems()}
            self._cassette_distances=dists
            self._hole.target=self

    @property
    def additional_holes(self):
        return self._additional_holes
    
    @additional_holes.setter
    def additional_holes(self, holes):
        self._additional_holes=holes

        if not self.is_sh:
            for h in self._additional_holes:
                h.target=self

    @property
    def holes(self):
        if self.hole:
            return [self.hole]+self.additional_holes
        else:
            return self.additional_holes

#    @property
#    def required_slit(self):
#        """Return the required slit per the target, then per the setup"""

    @property
    def conflicting_ids(self):
        ret=[]
        for ct in self._conflicting:
            if ct.field:
                ret.append('{}:{}'.format(ct.field.name, ct.id))
            else:
                ret.append(ct.id)
        return ','.join(ret)

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
             'pm_ra':'{:7.4f}'.format(self.pm_ra),
             'pm_dec':'{:7.4f}'.format(self.pm_dec),
             'epoch':'{:6.1f}'.format(self.epoch),
             'priority':'{:.2f}'.format(self.priority),
             'type':self.type}
        if self.fiber:
            ret['fiber']=self.fiber.name
        if self.field:
            ret['field']=self.field.name
        if self.conflicting:
            ret['conflicts']=self.conflicting_ids

        for k,v in self.user.iteritems():
            if k in ret:
                ret['user_'+k]=v
            else:
                ret[k]=v

        return ret

    @property
    def dict(self):
        """Does not include hole info"""
        ret={'id':self.id,
             'ra':self.ra.sexstr,
             'dec':self.dec.sexstr,
             'epoch':'{:6.1f}'.format(self.epoch),
             'priority':'{:.2f}'.format(self.priority),
             'type':self.type}
        if self.fiber:
            ret['fiber']=self.fiber.name
        if self.hole:
            ret.update(self.hole.holeinfo)
        if self.conflicting:
            ret['conflicts']=self.conflicting_ids

        for k,v in self.user.iteritems():
            if k in ret:
                ret['user_'+k]=v
            else:
                ret[k]=v

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
        """Must return true if fiber is user assigned """
        return self.fiber!=None

    @property
    def plug_priority(self):
        """
        Return number indicating if hole should be assigned a fiber sooner
        or later (lower)
        """
        if len(self._usable_cassette_names)==0:
            return -1
        elif len(self._usable_cassette_names)==1:
            return 0.0 #Don't care, we've already been assigned to a cassette
        else:
            #TODO: Should this be normalized by the number of usable cassettes
            return sum(self._cassette_distances[c]
                       for c in self._usable_cassette_names)

    @property
    def nearest_usable_cassette(self):
        """Return name of nearest usable cassette """
        if not self._usable_cassette_names:
            return None
        
        usable=[(c, self._cassette_distances[c])
                for c in self._usable_cassette_names]
                
        return min(usable, key=operator.itemgetter(1))[0]

    def reset_assignment(self):
        self.fiber=copy(self.preset_fiber)
        self._usable_cassette_names=self._preset_usable_cassette_names.copy()
        if self.fiber:
            self._assigned_cassette_name=self.fiber.cassette_name
        else:
            self._assigned_cassette_name=None

#    @property
#    def cassette_name(self):
#        """Return the cassette or None if one isnt assigned"""
#        if self.fiber:
#            return self.fiber.cassette.name
#        else:
#            return self._assigned_cassette_name

    @property
    def assigned_cassette(self):
        """Required by rejigger"""
        if self.fiber:
            return self.fiber.cassette_name
        else:
            return self._assigned_cassette_name

    def is_assignable(self, cassette=None):
        """
        True iff target can be (re)assigned, optionally to specified cassette
        or fiber.
        Targets without holes and targets with user assignments are never
        assignable.
        Do not specify both cassette and fiber
        """
        if not self.hole or self.preset_fiber:
            return False
        elif cassette:
            #TODO: Note this breaks if the usability of the cassettes evolves during assignment
            return cassette.name in self._preset_usable_cassette_names
        else:
            return True

    def set_possible_cassettes(self, cnames):
        self._preset_usable_cassette_names=set(cnames)
        self._usable_cassette_names=self._preset_usable_cassette_names.copy()

    def update_possible_cassettes_by_name(self, cassette_names):
        """
        Add cassettes to the list of possible cassettes usable with hole.
        Intersection with previously set possible cassettes is used as 
        the set of possibles
        """
        if type(cassette_names) not in [list, set, tuple]:
            raise TypeError('casssettes must be a list/set/tupel of cassette names')
        if self.fiber:
            raise Exception('Fiber already assigned')
#        if self._usable_cassette_names!=set(cassette_names):
#            log.debug('Updating possible '
#                      'cassettes:\n  {}\n  {}'.format(self._usable_cassette_names, cassette_names))
        #Update the list of possibles
        self._usable_cassette_names.intersection_update(cassette_names)

        try:
            assert len(self._usable_cassette_names)>0
        except AssertionError:
            pass
#            print('updating possible_cassettes to zero for {}'.format(
#                  str(self)))
#            import ipdb;ipdb.set_trace()



