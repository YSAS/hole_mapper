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

def hashfile(filepath, contents=None):
    sha1 = hashlib.sha1()
    if contents:
        sha1.update(contents)
    else:
        with open(filepath, 'rb') as f: sha1.update(f.read())
    return sha1.hexdigest()

def load_dotfibermap(filename, usecache=True, metadata_only=False):
    """Does not return a discreete instance of the map. don't change it!"""
    
    #Read file
    try:
        with open(filename,'r') as f:
            lines=f.readlines()
    except IOError as e:
        raise e
    
    sha1=hashfile('',''.join(lines))
    
    if usecache:
        try:
            if _FIBERMAP_CACHE[filename].sha1==sha1:
                return _FIBERMAP_CACHE[filename]
        except KeyError:
            pass

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
                    k,_,v=l.partition('=')
                    d[k.strip()]=v.strip()
                sec['processed']=d
            else:
                if metadata_only:
                    sec['processed']={}
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

        map=Fibermap(sections['setup']['processed'], assigned, filename, sha1)

        if usecache:
            _FIBERMAP_CACHE[filename]=map

        #Finally the plate
        return map

    except Exception as e:
        raise FibermapError(str(e))


class FibermapError(Exception):
    pass

class Fibermap(object):
    def __init__(self, info, assigned, file, sha1):
        """info is a dictionary of keys in the [setup] section
        assigned is a list of dicts from the [assigned] section"""
        self.dict=info
        self.assigned=assigned
        self.sha1=sha1
        self.file=file

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

