from target import Target
import os.path
from logger import getLogger
from pathconf import PLUGMAP_DIRECTORY
from readerswriters import _parse_header_row, _parse_record_row

REQUIRED_ASSIGNMENTS_SECTION_KEYS=['fiber', 'id','ra','dec','epoch','pm_ra','pm_dec',
                               'priority', 'type', 'x','y', 'z','d']

def load_dotplugmap(filename):

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
                else:
                    req=[]

                keys=_parse_header_row(sec['lines'][0], REQUIRED=req)
                user_keys=[k for k in keys if k not in req]

                dicts=[]
                for l in sec['lines'][1:]:
                    #TODO: Check for required values?
                    dicts.append(_parse_record_row(l, keys, user_keys))
                sec['processed']=dicts
        
        dict=sections['setup']['processed']

        assigned=map(lambda x: Target(**x),
                          sections['assignments']['processed'])


        #Finally the plate
        return Plugmap(sections['setup']['processed'], assigned)

    except Exception as e:
        raise PlugmapError(str(e))


class PlugmapError(Exception):
    pass

class Plugmap(object):
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
        return self.dict['name'].split(':')[0]

    @property
    def mapping(self):
        return {r['fiber']:r['id'] for r in self.assigned}


