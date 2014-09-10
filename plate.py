from target import Target
from field import Field
import os.path
from logger import getLogger
from pathconf import PLATE_DIRECTORY
from glob import glob

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

class PlateError(Exception):
    pass

class Plate(object):
    def __init__(self, info_dict, plate_holes, fields):
        self.name=info_dict.pop('name')
        self.user=info_dict.copy()
        self.plate_holes=plate_holes
        self.fields=fields

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

def load_dotplate(filename):

    #Read file
    try:
        lines=open(filename,'r').readlines()
    except IOError as e:
        raise e

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
            undrilled=map(lambda x: Target(**x),
                          sections[fsec+':undrilled']['processed'])
            drilled=map(lambda x: Target(**x),
                        sections[fsec+':drilled']['processed'])
            standards=map(lambda x: Target(**x),
                        sections[fsec+':standards']['processed'])
            fields.append(Field(field_dict, drilled, undrilled, standards))

        #Finally the plate
        return Plate(sections['plate']['processed'], plate_holes, fields)

    except Exception as e:
        raise PlateError(str(e))

def get_plate(platename):
    try:
        return load_dotplate(os.path.join(PLATE_DIRECTORY(),platename)+'.plate')
    except IOError:
        raise ValueError("Unknown plate '{}'.".format(platename))

def get_all_plate_names():
    """ dict of plate names to files"""
    ret={}
    _log.info('Looking for plates in {}'.format(PLATE_DIRECTORY()))
    files=glob(PLATE_DIRECTORY()+'*.plate')
    for file in files:
        if os.path.basename(file).lower() not in ['none.plate', 'sample.plate']:
            try:
                p=load_dotplate(file)
                ret[p.name]=file
            except (IOError, PlateError) as e:
                _log.warn('Skipped {} due to {}'.format(file,str(e)))
    return ret
