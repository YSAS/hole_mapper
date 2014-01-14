from dimensions import SH_RADIUS
from collections import defaultdict
import os
from jbastro.astroLib import sexconvert
from datetime import datetime
import holesxy

GUIDE_REF_TYPE='R'

#List of valid type codes
VALID_TYPE_CODES=['T', 'S', 'C', 'G', 'A', 'Z','O']

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

class field(dict):
    def __init__(self, *args):
        dict.__init__(self, args)
        self.update({'file':'','name':None,'obsdate':None,'user':{},
                     'G':[], 'T':[], 'C':[], 'A':[], 'S':[], 'Z':[],'R':[],
                     '_processed':False})
    
    def ra(self):
        print 'Not correcting field ra with PM'
        return self['C'][0]['ra']

    def dec(self):
        print 'Not correcting field dec with PM'
        return self['C'][0]['dec']

    def nfib_needed(self):
        return len(self['T'])+len(self['S'])

    def process(self):
        """
        Process the targets in the field and update the field with xyz positions 
        """
        field=self
        obs_date=self['obsdate']
        
        targs=field['G']+field['T']+field['A']+field['S']
        ras=[t['ra'] for t in targs]
        decs=[t['dec'] for t in targs]
        #TODO: Update ra & dec with proper motions here
        epochs=[t['epoch'] for t in targs]
        targ_types=[t['type'] for t in targs]
        pos, mech, info=holesxy.compute_hole_positions(field['C'][0]['ra'],
                            field['C'][0]['dec'], field['C'][0]['epoch'],
                            obs_date,
                            ras, decs, epochs, targ_types, fieldrot=180.0)
                            

        #Store the info
        for i,t in enumerate(targs):
            t['x'],t['y'],t['z'],t['r']=pos.x[i],pos.y[i],pos.z[i],pos.r[i]
        
        for i in (i for i,t in enumerate(mech.type) if t==GUIDE_REF_TYPE):
            #TODO: Make guide the responsible guide target
            hole=Hole()
            hole.update({'id':'GUIDEREF','x':mech.x[i], 'y':mech.y[i],
                        'z':mech.z[i], 'r':mech.r[i],'type':'R', 'guide':{}})
            field['R'].append(hole)

        field['_processed']=True

    def collisions(self):
        if not field['_collisions']:
            holes=self.holes()
            x=[h['x'] for h in holes]
            y=[h['y'] for h in holes]
            r=[h['r'] for h in holes]
            collision_graph=jbastro.build_overlap_graph_cartesian(x,y,r,
                                                      overlap_pct_ok=0.0)
    
    def drillable_holes(self):
        pass

    def undrillable_holes(self):
        """Return something wich lists the holes that cannot be drilled """
        pass

    def isProcessed(self):
        return self['_processed']

    def holes(self):
        """ return a list of all the holes the field has on the plate """
        if not self.isProcessed():
            return []
        else:
            return self['C']+self['T']+self['S']+self['A']+self['G']+self['R']


class Hole(dict):
    def __init__(self, *args):
        dict.__init__(self, args)
        self.update({'x':0.0,'y':0.0,'z':0.0,'r':0.0,'user':{},
                    'id':'', 'priority':0.0,'type':'',
                    'ra':0.0,'dec':0.0,'epoch':0.0,
                    'pm_ra':0.0, 'pm_dec':0.0})

    def __hash__(self):
        return "{}{}{}{}{}".format(self['x'], self['y'], self['z'],
                                   self['r'], self['type']).__hash__()

def load_dotfield(file):
    """
    returns {'name':field_name,
                'G':dictlist, guides
                'T':dictlist, targets
                'C':dictlist, shack hartman
                'A':dictlist, acquisitions
                'S':dictlist, skys
                'Z':dictlist, standard stars
                'R':dictlist} guide ref holes
    or raises error if file has issues.
    """

    ret=field()
    ret['file']=os.path.basename(file)
    

    try:
        lines=open(file,'r').readlines()
    except IOError as e:
        raise e

    lines=[l.strip() for l in lines]

    have_name=False

    try:
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
                if k in VALID_TYPE_CODES:
                    raise Exception('Key {} not allowed.'.format(k))
                if k in PROGRAM_KEYS and ret[k]==None:
                    if k=='obsdate':
                        ret[k]=datetime(*map(int, v.split()))
                    else:
                        ret[k]=v
                elif k not in ret['user']:
                    ret['user'][k]=v
                else:
                    raise Exception('Key {} may only be defined once.'.format(k))
            elif l.lower().startswith('ra'):
                keys=_parse_header_row(l.lower())
            else:
                hole=Hole()
                hole.update(_parse_record_row(l, keys))
                ret[hole['type']].append(hole)
    except Exception as e:
        raise IOError('Failed on line '
                        '{}: {}\n  Error:{}'.format(lines.index(l),l,str(e)))
    #Use the s-h (or field center id if none) as the field name if one wasn't
    # defined
    if not ret['name']:
        ret['name']=ret['C'][0]['id']

    for t in ret['C']:
        t['x'],t['y'],t['z'],t['r']=0.0,0.0,0.0,SH_RADIUS

    return ret
