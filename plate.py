from target import Target
from field import Field
import os.path
from logger import getLogger
from pathconf import PLATE_DIRECTORY
from glob import glob
import copy, hashlib

from readerswriters import _parse_header_row, _parse_record_row

REQUIRED_UNDRILLED_SECTION_KEYS=['ra', 'dec', 'epoch', 'id', 'type', 'priority',
                                 'pm_ra','pm_dec']
REQUIRED_PLATEHOLE_SECTION_KEYS=['id','x','y','z','d', 'type']
REQUIRED_DRILLED_SECTION_KEYS=['id','ra','dec','epoch','pm_ra','pm_dec',
                               'priority', 'type', 'x','y', 'z','d']
REQUIRED_STANDARDS_SECTION_KEYS=['ra', 'dec', 'epoch', 'id', 'type', 'priority',
                                 'pm_ra','pm_dec']
REQUIRED_PLATE_RECORD_ENTRIES=['ra', 'dec', 'epoch', 'id', 'type', 'priority',
                               'pm_ra','pm_dec','x','y','z']

_log=getLogger('plate')

_PLATE_CACHE={}

def hashfile(filepath, contents=None):
    sha1 = hashlib.sha1()
    if contents:
        sha1.update(contents)
    else:
        with open(filepath, 'rb') as f: sha1.update(f.read())
    return sha1.hexdigest()


class PlateError(Exception):
    pass

class Plate(object):
    def __init__(self, info_dict, plate_holes, fields, sha1):
        self.name=info_dict.pop('name')
        self.user=info_dict.copy()
        self.plate_holes=plate_holes
        self.fields=fields
        self.sha1=sha1

    def get_field(self, name):
        try:
            return [f for f in self.fields if f.name ==name][0]
        except IndexError:
            raise ValueError('No field with name {} on plate {}'.format(name,
                              self.name))

    @property
    def all_holes(self):
        return ([h for f in self.fields for h in f.holes]+
                [h for t in self.plate_holes for h in t.holes])

    @property
    def file_version(self):
        return '1.0'

def load_dotplate(filename, singleton_ok=False, debug=False, usecache=True,
                  metadata_only=False):
    """
    metadata_only -> don't create targets for drilled or undrilled sections
    """

    #Read file
    try:
        with open(filename,'r') as f:
            lines=f.readlines()
    except IOError as e:
        raise e
    
    sha1=hashfile('',''.join(lines))

    if usecache:
        try:
            if _PLATE_CACHE[filename].sha1==sha1:
                if singleton_ok:
                    return _PLATE_CACHE[filename]
                else:
                    return copy.deepcopy(_PLATE_CACHE[filename])
        except KeyError:
            pass

    #Break file into sections
    lines=[l.strip() for l in lines]

    curr_section=None
    sections={}
    for l in (l for l in lines if l and l[0]!='#'):
        
        if l[0] =='[' and l[-1]==']':
#            #Check formatting
#            if not l.endswith(']') or not l[1:-1]:
#                err='{} - Bad section name l{}: {}'.format(
#                      os.path.basename(filename), lines.index(l), l)
#                raise PlateError(err)
            curr_section=l[1:-1].lower()
            sections[curr_section]={'lines':[]}
        else:
            if curr_section==None:
                err='{} - Section must start with []'
                raise PlateError(err.format(os.path.basename(filename)))
            sections[curr_section]['lines'].append(l)

#    try:
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
            #Section is dictlist records
            if 'undrilled' in sec_name:
                req=REQUIRED_UNDRILLED_SECTION_KEYS
            elif 'plateholes' == sec_name:
                req=REQUIRED_PLATEHOLE_SECTION_KEYS
            elif 'standards' in sec_name:
                req=REQUIRED_STANDARDS_SECTION_KEYS
            else:
                req=REQUIRED_DRILLED_SECTION_KEYS

            keys=_parse_header_row(sec['lines'][0], REQUIRED=req)
            user_keys=[k for k in keys if k not in req]

            dicts=[]
            for l in sec['lines'][1:]:
                #TODO: Check for required values?
                dicts.append(_parse_record_row(l, keys, user_keys))
            sec['processed']=dicts
    
    #Create the plate
    
    #Plateholes
    plate_holes=[Target(**r) for r in sections['plateholes']['processed']]

    #Fields
    fields=[]
    field_sec_names=[k for k in sections if 'field' in k and ':' not in k]
    for fsec in field_sec_names:
        field_dict=sections[fsec]['processed']
        if metadata_only:
            undrilled=[]
            drilled=[]
        else:
            undrilled=map(lambda x: Target(**x),
                          sections[fsec+':undrilled']['processed'])
            drilled=map(lambda x: Target(**x),
                        sections[fsec+':drilled']['processed'])
        standards=map(lambda x: Target(**x),
                    sections[fsec+':standards']['processed'])
        fields.append(Field(field_dict, drilled, undrilled, standards))

    #Finally the plate
    plate=Plate(sections['plate']['processed'], plate_holes, fields, sha1)

    if usecache:
        _PLATE_CACHE[filename]=plate

    return plate

#    except Exception as e:
#        if debug:
#            import ipdb;ipdb.set_trace()
#        raise PlateError(str(e))

def get_plate(platename):
    try:
        return load_dotplate(os.path.join(PLATE_DIRECTORY(),platename)+'.plate')
    except IOError:
        raise ValueError("Unknown plate '{}'.".format(platename))

def get_all_plate_filenames():
    _log.info('Looking for plates in {}'.format(PLATE_DIRECTORY()))
    files=glob(PLATE_DIRECTORY()+'*.plate')
    ok=lambda x: os.path.basename(x).lower() not in ('none.plate','sample.plate')
    return filter(ok, files)

def get_all_plate_names():
    """ dict of plate names to files"""
    ret={}
    files=get_all_plate_filenames()
    for file in files:
        try:
            p=load_dotplate(file, singleton_ok=True)
            ret[p.name]=file
        except (IOError, PlateError) as e:
            _log.warn('Skipped {} due to {}'.format(file,str(e)))
    return ret
