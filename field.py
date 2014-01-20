from collections import defaultdict
import os
from jbastro.astroLib import sexconvert
from datetime import datetime
import holesxy
from logger import getLogger
from hole import Hole, SHACKHARTMAN_HOLE
from target import Target
from target import GUIDEREF_TYPE, GUIDE_TYPE
from graphcollide import build_overlap_graph_cartesian

log=getLogger('plateplanner.field')

#List of valid type codes
from target import VALID_TYPE_CODES

#List of required keys
REQUIRED_KEYS=['ra', 'dec', 'epoch', 'id', 'type', 'priority']
OPTIONAL_KEYS=['pm_ra','pm_dec']
OPTIONAL_KEYS_DEFAULTS=[0.0,0.0]

#List of forbidden keys
FORBIDDEN_KEYS=['user']

#Default priority if '-'
DEFAULT_PRIORITY = float('-inf')

#TODO: Encapsulate user defined params in 'user' for each targdict
def _parse_header_row(l):
    """ Verify row is a valid header and break it into keys """
    keys=l.split()
    
    assert len(keys) >= len(REQUIRED_KEYS)
    
    #Duplicates forbidden
    assert len(keys) == len(set(keys))
    
    #Must have all the required keys
    assert len([k for k in keys if k in REQUIRED_KEYS]) == len(REQUIRED_KEYS)
    
    #Must not have any forbidden keys
    assert len([k for k in keys if k in FORBIDDEN_KEYS])==0
    
    return keys

def _parse_record_row(rec, keys):
    
    vals=rec.split()
    
    #Number of values in the row must match the number of keys
    assert len(vals)==len(keys)
    
    #Create the dictionary
    rdict={keys[i].lower():vals[i] for i in range(len(keys))
            if vals[i] !='-' and
            keys[i].lower() in (REQUIRED_KEYS+OPTIONAL_KEYS)}
    
    #Vet all the keys
    for k in rdict.keys():
        if not KEY_VETTERS[k](rdict[k]):
            raise Exception('Key error {} for: {}'.format(k,rec))

    #Make sure all the required keys are set
    for k in REQUIRED_KEYS:
        if k not in ['id', 'priority']:
            assert k in rdict
    
    #Enforce cannonical RA & DEC format
    rdict['ra'] = sexconvert(rdict['ra'],dtype=float,ra=True)
    rdict['dec'] = sexconvert(rdict['dec'],dtype=float)
    
    #Set a priority if one isn't set
    if 'priority' not in rdict:
        rdict['priority'] = DEFAULT_PRIORITY
    
    #Generate the default ID if one wasnt defined
    if 'id' not in rdict:
        rdict['id'] = _get_default_id(rdict)
    
    #Force type to be upper case
    rdict['type']=rdict['type'].upper()
    
    #Support legacy type code O by converting to T
    if rdict['type']=='O':
        rdict['type']='T'

    #Add any user defined keys to 'user'
    rdict['user']={keys[i].lower():vals[i] for i in range(len(keys))
                    if vals[i] !='-' and keys[i].lower() not in
                    (REQUIRED_KEYS+OPTIONAL_KEYS)}
    return rdict

def _get_default_id(rdict):
    """ typecodeRA_DEC """
    return '{}{ra}_{dec}'.format(rdict['type'], ra=rdict['ra'], dec=rdict['dec'])

def _is_floatable(x):
    """ True iff float(x) succeeds """
    try:
        float(x)
        return True
    except Exception:
        return False

def _is_valid_dec(x):
    """ True iff the string x is a valid dec """
    try:
        if _is_floatable(x):
            assert -90 <= float(x) and float(x) <= 90
        else:
            h,m,s =x.split(':')
            assert -90 <= int(h) and int(h) <= 90
            assert 0 <=int(m) and int(m) < 60
            assert 0<=float(s) and float(s) < 60
    except Exception:
        return False
    return True

def _is_valid_ra(x):
    """ True iff the string x is a valid ra """
    try:
        if _is_floatable(x):
            assert 0 <= float(x) and float(x) <= 360
        else:
            h,m,s =x.split(':')
            assert 0<=int(h) and int(h) <=24
            assert 0<=int(m) and int(m) < 60
            assert 0<=float(s) and float(s) < 60
    except Exception:
        return False
    return True

#Define field keys
PROGRAM_KEYS=['name', 'obsdate']

#Define vetting functions for keys
KEY_VETTERS=defaultdict(lambda : lambda x: len(x.split())==1)
KEY_VETTERS['ra']=_is_valid_ra
KEY_VETTERS['dec']=_is_valid_dec
KEY_VETTERS['epoch']=_is_floatable
KEY_VETTERS['type']=lambda x: x in VALID_TYPE_CODES
KEY_VETTERS['priority']=_is_floatable
KEY_VETTERS['pm_ra']=_is_floatable
KEY_VETTERS['pm_dec']=_is_floatable


        #TODO: User keys disallow keys we use (prepend U_)
        #TODO: enforces all user keys are strings
def load_dotfield(file):
    """
    returns FieldCatalog() or raises error if file has issues.
    """

    ret=FieldCatalog(file=os.path.basename(file))

    try:
        lines=open(file,'r').readlines()
    except IOError as e:
        raise e

    lines=[l.strip() for l in lines]

    have_name=False

#    try:
    for l in (l for l in lines if l):
        if l[0] =='#':
            continue
        elif l[0] not in '+-0123456789' and not l.lower().startswith('ra'):
            try:
                k,_,v=l.partition('=')
                k=k.strip().lower()
                if k=='field':
                    k='name'
                v=v.strip()
                assert v != ''
            except Exception as e:
                raise Exception('Bad key=value formatting: {}'.format(str(e)))

            if k=='obsdate':
                ret.obsdate=datetime(*map(int, v.split()))
            elif k=='name':
                ret.name=v
            else:
                ret.user[k]=v
        elif l.lower().startswith('ra'):
            keys=_parse_header_row(l.lower())
        else:
            #import ipdb;ipdb.set_trace()
            targ=Target(**_parse_record_row(l, keys))
            ret.add_target(targ)
            targ.field=ret
#    except Exception as e:
#        raise IOError('Failed on line '
#                        '{}: {}\n  Error:{}'.format(lines.index(l),l,str(e)))
    #Use the s-h (or field center id if none) as the field name if one wasn't
    # defined
    if not ret.name:
        ret.name=ret.sh.id
    #import ipdb;ipdb.set_trace()
    return ret



class FieldCatalog(object):
    def __init__(self, file='', name='', obsdate=None,
                 sh=None, user=None, guides=None, targets=None,
                 acquisitions=None, skys=None, standards=None):
        """sh should be a target"""
        
        self.file=file
        self.name=name
        self.obsdate=obsdate
        self.sh=sh if targets else Target(type='C',hole=SHACKHARTMAN_HOLE)
        self.user=user if user else {}
        self.guides=guides if guides else []
        self.targets=targets if targets else []
        self.acquisitions=acquisitions if acquisitions else []
        self.skys=skys if skys else []
        self.standards=standards if standards else []
        
        self.holesxy_info=None
        
        self._processed=False

    def ra(self):
        print 'Not correcting field ra with PM'
        return self.sh.ra

    def dec(self):
        print 'Not correcting field dec with PM'
        return self.sh.dec

    def add_target(self,targ):
        if targ.is_sky:
            self.skys.append(targ)
        elif targ.is_target:
            self.targets.append(targ)
        elif targ.is_guide:
            self.guides.append(targ)
        elif targ.is_acquisition:
            self.acquisitions.append(targ)
        elif targ.is_standard:
            self.standards.append(targ)
        elif targ.is_sh:
            self.sh=targ
            self.sh.hole=SHACKHARTMAN_HOLE
        else:
            raise ValueError('Target {} of unknown type'.format(targ))


    def process(self):
        """
        Process the targets in the field to find their update xyz positions
        """
        obs_date=self.obsdate
        
        targs=self.guides+self.targets+self.acquisitions+self.skys
        ras=[t.ra.float for t in targs]
        decs=[t.dec.float for t in targs]
        
        #TODO: Update ra & dec with proper motions here
        
        epochs=[t.epoch for t in targs]
        targ_types=[t.type for t in targs]
        
        guide_ndxs=[i for i,t in enumerate(targ_types) if t=='G']
        
        pos, guideref, info=holesxy.compute_hole_positions(self.sh.ra.float,
                                self.sh.dec.float, self.sh.epoch,self.obsdate,
                                ras, decs, epochs, targ_types, fieldrot=180.0)
        
        #Store the info
        for i,t in enumerate(targs):
            t.hole=Hole(pos.x[i],pos.y[i],pos.z[i],pos.d[i],t)
        
        for i,ndx in enumerate(guide_ndxs):
            holes=[Hole(guideref.x[3*i+j], guideref.y[3*i+j],
                        guideref.z[3*i+j], guideref.d[3*i+j], targs[ndx])
                   for j in range(3)]
            targs[ndx].additional_holes=holes


        self.holesxy_info=info

        self._processed=True

    def get_info_dict(self):
        """ return a dictionary of field information """
        ret={'name':self.name,
             'file':self.file,
             'obsdate':str(self.obsdate),
             '(ra, dec)':'{} {}'.format(self.sh.ra.sexstr,self.sh.dec.sexstr),
             '(az, el)':'{:3f} {:3f}'.format(self.holesxy_info.az,
                                             self.holesxy_info.el),
             '(ha, st)':'{:3f} {:3f}'.format(self.holesxy_info.ha,
                                             self.holesxy_info.st),
             'airmass':'{:2f}'.format(self.holesxy_info.airmass)}

        for k,v in self.user.iteritems():
            if k in ret:
                ret['user_'+k]=str(v)
            else:
                ret[k]=str(v)
        return ret
    
    def get_assignable_targets(self):
        """Returns  """

    def get_drillable_targets(self):
        """Return all targets in the catalog that can be drilled"""
        try:
            return self._drillable_targets
        except AttributeError:
            pass
        
        if not self._processed:
            self.process()
        
        from time import time
        tics=[time()]
        
        #Get data needed for collision graph
        holes=self.holes()+[self.sh.hole]
        x=[h.x for h in holes]
        y=[h.y for h in holes]
        d=[h.d for h in holes]
                
        tic1=time()
        
        #Create the graph
        coll_graph=build_overlap_graph_cartesian(x,y,d, overlap_pct_r_ok=0.9)

        #Drop everything conflicting with the sh
        dropped=coll_graph.drop_conflicting_with(len(holes)-1)
        for i in dropped:
            holes[i].target.conflicting=self.sh

        holes.pop(-1)
        coll_graph._nnodes-=1

        tics.append(time())
        pri=[h.target.priority for h in holes]
        keep,drop=coll_graph.crappy_min_vertex_cover_cut(weights=pri,
                                                         retdrop=True)

        tics.append(time())
        
        #Now go through and figure out which targets are(not) usable
        drillable=[holes[i].target for i in keep]
        undrillable=[holes[i].target for i in drop]
        
        tics.append(time())
        
        #determine cause of conflict
        for i,t in enumerate(undrillable):
            conf=list(set(drillable[ndx]
                          for ndx in coll_graph.collisions(drop[i])))
            try:
                assert len(conf) >0
            except Exception:
                import ipdb;ipdb.set_trace()
            t.conflicting=conf
        
        drillable=list(set(drillable))
        undrillable=set(undrillable)

        tics.append(time())
        tics=[t-tics[0] for t in tics[1:]]
        log.debug('get_drillable_targets took: {}'.format(tics))

        self._drillable_targets=drillable

        return self._drillable_targets
        
    def isProcessed(self):
        return self._processed

    @property
    def usable_guides(self):
        return [g for g in self.guides if not g.conflicting]

    @property
    def usable_acquisitions(self):
        return [g for g in self.acquisitions if not g.conflicting]

    def all_targets(self):
        return (self.skys+self.targets+self.guides+self.acquisitions)

    def holes(self):
        """ return a list of all the holes the field would like on a plate """
        if not self._processed:
            return []
        else:
            return [hole for t in self.all_targets() for hole in t.holes()]

    def drillable_dictlist(self):
        ret=[]
        for t in (t for t in self.all_targets()
                  if not t.conflicting and t.on_plate):
            d=t.hole.info
            d.pop('field','')
            ret.append(d)
            if t.type==GUIDE_TYPE:
                #Change type code for guide refs
                for h in t.additional_holes:
                    d=h.info
                    d.pop('field','')
                    d['type']=GUIDEREF_TYPE
                    ret.append(d)
        return ret

    def undrillable_dictlist(self, flat=False):
        ret=[t.info for t in self.all_targets()
             if t.conflicting or not t.on_plate]
        map(lambda x: x.pop('field',''), ret)
        return ret

    def standards_dictlist(self):
        return [t.info for t in self.standards]
