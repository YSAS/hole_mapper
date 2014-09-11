from target import Target
import os.path
from logger import getLogger
from pathconf import FIBERMAP_DIRECTORY
from readerswriters import _parse_header_row, _parse_record_row
from glob import glob
import hashlib

REQUIRED_ASSIGNMENTS_SECTION_KEYS=['fiber', 'id','ra','dec','epoch','pm_ra',
   'pm_dec', 'priority', 'type', 'x','y', 'z','d']
REQUIRED_UNUSED_SECTION_KEYS=['id','ra','dec','epoch','pm_ra',
   'pm_dec', 'priority', 'type', 'x', 'y', 'z','d']
REQUIRED_GUIDES_SECTION_KEYS=['id','ra','dec','epoch','pm_ra',
   'pm_dec', 'priority', 'type', 'x', 'y', 'z','d']

_log=getLogger('fibermap')

_FIBERMAP_CACHE={}

def hashfile(filepath):
    sha1 = hashlib.sha1()
    with open(filepath, 'rb') as f:
        sha1.update(f.read())
    return sha1.hexdigest()

def load_dotfibermap(filename):
    """Does not return a discreete instance of the map. don't change it!"""
    try:
        if _FIBERMAP_CACHE[filename]['hash']==hashfile(filename):
            return _FIBERMAP_CACHE[filename]['map']
    except KeyError:
        pass
    
    #Read file
    try:
        with open(filename,'r') as f:
            lines=f.readlines()
    except IOError as e:
        raise e

    #Break file into sections
    lines=[l.strip() for l in lines]

    curr_section=None
    sections={}
    for l in (l for l in lines if l and l[0]!='#'):
        
        if l[0] =='[':
            #Check formatting
            if not l.endswith(']') or not l[1:-1]:
                err='{} - Bad section name l{}: {}'.format(
                      os.path.basename(filename), lines.index(l), l)
                raise PlateError(err)
            curr_section=l[1:-1].lower()
            sections[curr_section]={'lines':[]}
        else:
            if curr_section==None:
                err='{} - Section must start with []'
                raise PlateError(err.format(os.path.basename(filename)))
            sections[curr_section]['lines'].append(l)

    try:
        #Process sections
        for sec_name, sec in sections.items():
            if '=' in sec['lines'][0]:
                #Section is key value pairs
                d={}
                for l in sec['lines']:
                    k,v=l.split('=')
                    d[k.strip()]=v.strip()
                sec['processed']=d
            else:
                #Section is dictlist records
                if 'assignments' in sec_name:
                    req=REQUIRED_ASSIGNMENTS_SECTION_KEYS
                elif 'unused' in sec_name:
                    req=REQUIRED_UNUSED_SECTION_KEYS
                elif 'guides' in sec_name:
                    req=REQUIRED_GUIDES_SECTION_KEYS
                else:
                    req=[]

                keys=_parse_header_row(sec['lines'][0], REQUIRED=req)
                user_keys=[k for k in keys if k not in req]

    #            import ipdb;ipdb.set_trace()
                dicts=[_parse_record_row(l, keys, user_keys)
                       for l in sec['lines'][1:]]
                sec['processed']=dicts
        
        dict=sections['setup']['processed']

        assigned=sections['assignments']['processed']

        map=Fibermap(sections['setup']['processed'], assigned)
        _FIBERMAP_CACHE[filename]={'hash':hashfile(filename), 'map':map}

        #Finally the plate
        return map

    except Exception as e:
        raise FibermapError(str(e))


class FibermapError(Exception):
    pass

class Fibermap(object):
    def __init__(self, info, assigned):
        """info is a dictionary of keys in the [setup] section
        assigned is a list of dicts from the [assigned] section"""
        self.dict=info
        self.assigned=assigned

    @property
    def name(self):
        return self.dict['name']

    @property
    def platename(self):
        return self.dict['plate']

    @property
    def mapping(self):
#        return {r.fiber.name:r.id for r in self.assigned}
        return {r['fiber']:r['id'] for r in self.assigned}

def fibermap_files():
    _log.info('Looking for fibermaps in {}'.format(FIBERMAP_DIRECTORY()))
    files=glob(FIBERMAP_DIRECTORY()+'*.fibermap')
    return files

def get_fibermap_for_setup(setupname):

    files=fibermap_files()

    for file in files:
        if os.path.basename(file).lower() not in []:
            try:
                fm=load_dotfibermap(file)
                if fm.name.lower()==setupname.lower():
                    return fm
            except (IOError, FibermapError) as e:
                _log.warn('Skipped {} due to {}'.format(file,str(e)))
   
    raise ValueError('No fibermap for {}'.format(setupname))

def get_platenames_for_known_fibermaps():
    
    files=fibermap_files()
    
    ret=[]
    for file in files:
        if os.path.basename(file).lower() not in []:
            try:
                fm=load_dotfibermap(file)
                ret.append(fm.platename)
            except (IOError, FibermapError) as e:
                _log.warn('Skipped {} due to {}'.format(file,str(e)))
    return list(set(ret))


def get_fibermap_names_for_plate(platename):
    
    files=fibermap_files()
    
    ret=[]
    for file in files:
        if os.path.basename(file).lower() not in []:
            try:
                fm=load_dotfibermap(file)
                if fm.platename==platename:
                    ret.append(fm.name)
            except (IOError, FibermapError) as e:
                _log.warn('Skipped {} due to {}'.format(file,str(e)))
    return ret


#from fibermap import *
#platefile='/Users/one/Desktop/February Plates/curated/Nidever3-4.plate'
#import oldplate
#oldplate.Plate(platefile)
#from glob import glob
#for f in glob('/Users/one/Desktop/procold/*.plate'):
#    makefm(f,'/Users/one/Desktop/procold/')
def makefm(platefile, dir='./'):
    import oldplate
    from readerswriters import _dictlist_to_records, _format_attrib_nicely
    REQUIRED_PLUGGED_SECTION_KEYS=['fiber', 'id', 'ra', 'dec', 'epoch', 'type',
                               'priority','pm_ra','pm_dec','x','y','z','d']
    REQUIRED_GUIDE_SECTION_KEYS=['id', 'ra', 'dec', 'epoch', 'type',
                                 'priority','pm_ra','pm_dec','x','y','z','d']
    REQUIRED_UNUSED_SECTION_KEYS=['id', 'ra', 'dec', 'epoch', 'type',
                                  'priority','pm_ra','pm_dec','x','y','z','d']

    old=oldplate.Plate(platefile)
    for sname, s in old.setups.items():

        mapfile='{}:{}:o.fibermap'.format(old.name, sname.replace(' ',''))
        mapfile=mapfile.replace(':','-')
        with open(os.path.join(dir,mapfile),'w') as fp:
    
            fp.write("[setup]\n")

            d=s.attrib
            d['(ra, dec)']='{} {}'.format(d.pop('ra','').replace(' ',':'),
                                          d.pop('de','').replace(' ',':'))
            d['(az, el)']='{} {}'.format(d.pop('az',''),d.pop('el',''))
            d['(ha, st)']=''
            d['config']='o'
            d['nused']=s.n_fibers_used()
            d['plate']=old.name
            d['fieldname']=sname
            d['name']='{}:{}:{}'.format(old.name.replace(' ','_'),
                                        sname.replace(' ','_'),
                                        'o')
            d['obsdate']=d.pop('utc','')
            d.pop('n')
            for r in _format_attrib_nicely(d): fp.write(r)
    
            #Fibers assigned and unassigned

            #Grab fibers
            fp.write("[assignments]\n")
            dl=s._target_list
            for i,d in enumerate(dl):
                if d['id']=='inactive': d['id']='unplugged'
                d['dec']=d.pop('de')
            recs=_dictlist_to_records(dl,col_first=REQUIRED_PLUGGED_SECTION_KEYS)
            for r in recs: fp.write(r)
    
            #Write guides and acquisitions
            fp.write("[guides]\n")
            dl=s._guide_list
            
            for i,d in enumerate(dl):
                d['id']='guide{}'.format(i)
                d['dec']=d.pop('de')
            recs=_dictlist_to_records(dl, col_first=REQUIRED_GUIDE_SECTION_KEYS)
            for r in recs: fp.write(r)

            #All the other targets
            fp.write("[unused]\n")
            recs=_dictlist_to_records([],col_first=REQUIRED_UNUSED_SECTION_KEYS)
            for r in recs: fp.write(r)
