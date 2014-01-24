from target import VALID_TYPE_CODES
from field import FieldCatalog
from setup import Setup
from plate import Plate
from target import Target

from collections import defaultdict
import databasegetter
import os.path
from datetime import datetime
from jbastro.astroLib import sexconvert

#Default priority if '-'
DEFAULT_PRIORITY = float('-inf')


PLATEHOLE_REQUIRED_COLS=['id','x','y','z','d']
UNDRILLABLE_REQUIRED_COLS=['id','ra','dec','epoch','pm_ra','pm_dec','priority',
                           'type', 'conflicts']
STANDARDS_REQUIRED_COLS=['id','ra','dec','epoch','priority','pm_ra','pm_dec']
DRILLABLE_REQUIRED_COLS=['id','ra','dec','epoch','pm_ra','pm_dec', 'priority',
                         'type', 'x','y', 'z','d']
DRILLFILE_REQUIRED_COLS=['x','y','z','d','type','id']


REQUIRED_UNDRILLED_SECTION_KEYS=['ra', 'dec', 'epoch', 'id', 'type', 'priority',
                                 'pm_ra','pm_dec']
REQUIRED_PLATEHOLE_SECTION_KEYS=['id','x','y','z','d']
REQUIRED_DRILLED_SECTION_KEYS=['id','ra','dec','epoch','pm_ra','pm_dec', 'priority',
                               'type', 'x','y', 'z','d']
REQUIRED_STANDARDS_SECTION_KEYS=['ra', 'dec', 'epoch', 'id', 'type', 'priority',
                                 'pm_ra','pm_dec']
REQUIRED_PLATE_RECORD_ENTRIES=['ra', 'dec', 'epoch', 'id', 'type', 'priority',
                            'pm_ra','pm_dec','x','y','z']


REQUIRED_FIELD_KEYS=['ra', 'dec', 'epoch', 'id', 'type', 'priority']
FIELD_KEYS=REQUIRED_FIELD_KEYS+['pm_ra','pm_dec']
REQUIRED_FIELD_RECORD_ENTRIES=['ra', 'dec', 'epoch', 'type']


def defdict(dic,default='-'):
    x=defaultdict(lambda:default)
    x.update(dic)
    return x

def _format_attrib_nicely(itemdict):
    items=[item for item in itemdict.iteritems() ]
    key_col_wid=max([len(k[1]) for k in items])+6
    
    items.sort(key=lambda x:x[0])
    
    ret=[]
    for k, v in items:
        spaces=' '*(key_col_wid-len(k)-1)
        ret.append("{k}={space}{v}\n".format(k=k, v=v, space=spaces))
    return ret

def _make_fmt_string(keys, recs):
    max_lens=[max( [len(k)] + [len(str(r.get(k,''))) for r in recs])
              for k in keys]
    l_strs=[('>' if l >0 else '<')+str(abs(l)) for l in max_lens]
    fmt_segs=["{r["+keys[i]+"]:"+l_strs[i]+"}" for i in range(len(keys))]
    return ' '.join(fmt_segs)+'\n'

def _dictlist_to_records(dictlist, col_first=None, col_last=None,
                         required_only=False):
    
    if not col_first:
        col_first=[]
    if not col_last:
        col_last=[]
    if required_only and len(col_last)+len(col_first)==0:
        raise ValueError('Must specify required columns with required_only')

    #Get all the columns
    cols=list(set([k.lower() for rec in dictlist for k in rec.keys()]))
    
    #reorder cols so that cols_ordered comes first
    for c in col_first+col_last:
        try:
            cols.remove(c)
        except ValueError:
            pass

    if required_only:
        cols=col_first+col_last
    else:
        cols=col_first+cols+col_last

    fmt=_make_fmt_string(cols, dictlist)
    
    #Create the records
    rec=[fmt.format(r={c:c for c in cols})] #header
    
    rec+=[fmt.format(r=defdict(dic)) for dic in dictlist]
    return rec

def _generate_default_id(rdict):
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


#Define vetting functions for keys
KEY_VETTERS=defaultdict(lambda : lambda x: len(x.split())==1)
#TODO: Test behavior with bad ra/dec data
KEY_VETTERS['ra']=_is_valid_ra
KEY_VETTERS['dec']=_is_valid_dec
KEY_VETTERS['epoch']=_is_floatable
KEY_VETTERS['type']=lambda x: x in VALID_TYPE_CODES
KEY_VETTERS['priority']=_is_floatable
KEY_VETTERS['pm_ra']=_is_floatable
KEY_VETTERS['pm_dec']=_is_floatable


#TODO: Encapsulate user defined params in 'user' for each targdict
def _parse_header_row(l, REQUIRED=[], FORBIDDEN=[]):
    """ Verify row is a valid header and break it into keys """
    keys=l.split()
    
    assert len(keys) >= len(REQUIRED)
    
    #Duplicates forbidden
    assert len(keys) == len(set(keys))
    
    #Must have all the required keys
    assert len([k for k in keys if k in REQUIRED]) == len(REQUIRED)
    
    #Must not have any forbidden keys
    assert len([k for k in keys if k in FORBIDDEN])==0
    
    return keys

def _parse_record_row(rec, keys, user_keys, REQUIRED=[]):
    
    vals=rec.split()
    
    #Number of values in the row must match the number of keys
    assert len(vals)==len(keys)
    
    #Create the dictionary
    rdict={keys[i].lower():vals[i] for i in range(len(keys))
           if vals[i] !='-' and keys[i].lower() not in user_keys}
    
    #Vet all the keys
    for k in rdict.keys():
        if not KEY_VETTERS[k](rdict[k]):
            raise Exception('Key error {} for: {}'.format(k,rec))

    #Make sure all the required keys are set
    for k in REQUIRED:
        assert k in rdict
    
    #Enforce cannonical RA & DEC format
    rdict['ra'] = sexconvert(rdict['ra'],dtype=float,ra=True)
    rdict['dec'] = sexconvert(rdict['dec'],dtype=float)
    
    #Set a priority if one isn't set
    if 'priority' not in rdict:
        rdict['priority'] = DEFAULT_PRIORITY
    
    #Generate the default ID if one wasnt defined
    if 'id' not in rdict:
        rdict['id'] = _generate_default_id(rdict)
    
    #Force type to be upper case
    rdict['type']=rdict['type'].upper()
    
    #Support legacy type code O by converting to T
    if rdict['type']=='O':
        rdict['type']='T'

    #Add any user defined keys to 'user'
    rdict['user']={keys[i].lower():vals[i]
                    for i in range(len(keys))
                    if vals[i] !='-' and keys[i].lower() in user_keys}
    return rdict


###
#
#
# Loaders
#
#
###



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
            keys=_parse_header_row(l.lower(), REQUIRED=REQUIRED_FIELD_KEYS)
            user_keys=[k for k in keys if k not in FIELD_KEYS]
        else:
            #import ipdb;ipdb.set_trace()
            rec=_parse_record_row(l, keys, user_keys,
                                  REQUIRED=REQUIRED_FIELD_RECORD_ENTRIES)
            targ=Target(**rec)
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


def load_dotplate(filename):

    #Read file
    try:
        lines=open(file,'r').readlines()
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
                raise Exception('Bad section name '
                                'l{}: {}'.format(lines.index(l),l))
            curr_section=l[1:-1].lower()
            sections[curr_section]={'lines':[]}
        else:
            if curr_section==None:
                raise Exception('Section must start with []')
            sections[curr_section]['lines'].append(l)

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
        field_dict=section[fsec]['processed']
        undrilled=map(lambda x: Target(**x),
                      section[fsec+':undrilled']['processed'])
        drilled=map(lambda x: Target(**x),
                    section[fsec+':drilled']['processed'])
        standards=map(lambda x: Target(**x),
                    section[fsec+':standards']['processed'])
        fields.append(Field(field_dict, drilled, undrilled, standards))

    #Finally the plate
    return Plate(sections['plate'],plate_holes,fields)

def load_dotconfigdef(filename):

    #Read file
    try:
        lines=open(file,'r').readlines()
    except IOError as e:
        raise e

    lines=[l.strip() for l in lines]

    section_dict={}
    for l in (l for l in lines if l and l[0]!='#'):
        k,v=l.split('=')
        assert k.strip() not in d
        section_dict[k.strip()]=v.strip()

    #Load the config piecemeal
    configR={'mode':section_dict['modeR'],
        'binning':section_dict['binningR'],
        'filter':section_dict['filterR'],
        'slit':section_dict['slitR'],
        'tetris_config':section_dict['tetris_configR'],
        'n_amps':section_dict['n_ampsR'],
        'speed':section_dict['speedR']}
    try:
        config['focus']=section_dict['focusR']
    except KeyError:
        pass
    
    if configR['mode'].lower()==HIRES_MODE:
        configR['hiel']=section_dict['elevationR']
        configR['hiaz']=section_dict['azimuthR']
    else:
        configR['loel']=section_dict['elevationR']
    
    configR['tetris_config']=tuple(map(lambda x: bool(int(x)),
                                      configR['tetris_config'].split(',')))

    configB={'mode':section_dict['modeB'],
        'binning':section_dict['binningB'],
        'filter':section_dict['filterB'],
        'slit':section_dict['slitB'],
        'tetris_config':section_dict['tetris_configB'],
        'n_amps':section_dict['n_ampsB'],
        'speed':section_dict['speedB']}
    try:
        config['focus']=section_dict['focusB']
    except KeyError:
        pass
    
    if configB['mode'].lower()==HIRES_MODE:
        configB['hiel']=section_dict['elevationB']
        configB['hiaz']=section_dict['azimuthB']
    else:
        configB['loel']=section_dict['elevationB']
    
    configB['tetris_config']=tuple(map(lambda x: bool(int(x)),
                                      configB['tetris_config'].split(',')))

    return configR, configB

def load_dotsetup(filename):
    """ read in a dotsetup file """
    #Read in the setups
    cp=RawConfigParser
    cp.optionxform=str
    with open(filename) as fp:
        cp.read(fp)
    
    setups=[]
    
    def _config_dict_from_dotsetup_dict(section_dict, side):
        def get_key(d,key, side):
            try:
                return d[k+side]
            except KeyError:
                return d[key]
        try:
            conf_name=get_key(section_dict, 'config', side)
            return databasegetter.get_config(conf_name, side)
        except KeyError:
            pass
        #Load the config piecemeal
        config={'mode':get_key(section_dict, 'mode',side),
                'binning':get_key(section_dict, 'binning',side),
                'filter':get_key(section_dict, 'filter',side),
                'slit':get_key(section_dict, 'slit',side),
                'tetris_config':get_key(section_dict, 'tetris_config',side),
                'n_amps':get_key(section_dict, 'n_amps',side),
                'speed':get_key(section_dict, 'speed',side)}
        
        try:
            config['focus']=get_key(section_dict, 'focus', side)
        except KeyError:
            pass
        
        if config['mode'].lower()==HIRES_MODE:
            config['hiel']=get_key(section_dict, 'elevation', side)
            config['hiaz']=get_key(section_dict, 'azimuth', side)
        else:
            config['loel']=get_key(section_dict, 'elevation', side)

        config['tetris_config']=tuple(map(lambda x: bool(int(x)),
                                          config['tetris_config'].split(',')))

        return config

    
    #Parse it all
    for sec in cp.sections():
        section_dict=dict(cp.items(sec))
        
        configB=_config_dict_from_dotsetup_dict(section_dict, 'B')
        configR=_config_dict_from_dotsetup_dict(section_dict, 'R')
        #TODO: Handle case where setup uses only one side
        
        configB=SetupConfig(**configB)
        configR=SetupConfig(**configR)
        field=section_dict['field']
        asignwith=map(lambda x: x.strip(),
                      section_dict.get('assignwith','').split(','))
                      
        setup=Setup(filename, fieldname, configR, configB,
                    assignwith=assignwith)

        setups.append(setup)
    
    return setups


####
#
#
#Writers
#
#
####

def write_dotplate(name, plate_holes, fields, dir='./'):
    filename='{}{}.plate'.format(dir, name)

    #get list of crap for the plate
    with open(filename,'w') as fp:
    
        #Write the [Plate] section
        fp.write("[Plate]\n")

        for r in _format_attrib_nicely({'name':name}):
            fp.write(r)

        #Write out mechanical holes
        fp.write("[PlateHoles]\n")
        recs=_dictlist_to_records(plate_holes, PLATEHOLE_REQUIRED_COLS)
        for r in recs:
            fp.write(r)
        
        #Write out the fields
        for i,f in enumerate(fields):

            #Write out field info section
            fp.write("[Field{}]\n".format(i))
            
            #Write out the field attributes
            for r in _format_attrib_nicely(f.get_info_dict()):
                fp.write(r)
            
            #Write out holes not drilled on the plate
            fp.write("[Field{}:Undrilled]\n".format(i))
            recs=_dictlist_to_records(f.undrillable_dictlist(),
                                      UNDRILLABLE_REQUIRED_COLS)
            for r in recs:
                fp.write(r)

            #Write out holes drilled on the plate
            fp.write("[Field{}:Drilled]\n".format(i))
            recs=_dictlist_to_records(f.drillable_dictlist(),
                                      DRILLABLE_REQUIRED_COLS)
            for r in recs:
                fp.write(r)

            #Write out standard stars
            fp.write("[Field{}:Standards]\n".format(i))
            recs=_dictlist_to_records(f.standards_dictlist(),
                                      STANDARDS_REQUIRED_COLS)
            for r in recs:
                fp.write(r)


def write_drill(name, plate_holes, fields, dir='./'):
    """ Write drill files for vince """
    file_fmt_str='{}{}_All_Holes_{}.txt'
    
    dicts=[d for f in fields for d in f.drillable_dictlist()]+plate_holes
    diams=set(d['d'] for d in dicts)
    
    for diam in diams:
        dicts_for_file=[d for d in dicts if d['d']==diam]
        with open(file_fmt_str.format(dir, name, diam),'w') as fp:

            recs=_dictlist_to_records(dicts_for_file, DRILLFILE_REQUIRED_COLS,
                                      required_only=True)
            for r in recs[1:]:
                fp.write(r)


DEFAULT_SEARCH_PATH='./'

def get_plate(platename, search_dir=None):
    dir=search_dir if search_dir else DEFAULT_SEARCH_PATH
    try:
        return load_dotplate(os.path.join(dir,platename)+'.plate')
    except IOError:
        return None

def get_config(configname, side, search_dir=None):
    dir=search_dir if search_dir else DEFAULT_SEARCH_PATH
    try:
        configR,configB=load_dotconfigdef(os.path.join(dir,configname)+
                                          '.configdef')
        if side.lower()=='r':
            return configR
        else:
            return configB
    except IOError:
        raise ValueError('Config {} not known'.format(configname))

def get_fiber_staus():
    """ returns a dict
    
    {cassettename:8-tuple of booleans with True being good}
    """
    return {n:(True,)*8 for n in cassettes.CASSETTE_NAMES}


def get_setup(setupname, search_dir=None):
    try:
        return load_dotsetup(os.path.join(dir,setupname)+'.setup')
    except IOError:
        raise ValueError('Could not find setup {}'.format(setupname))



def get_custom_usable_cassette_func(setup_name, search_dir=None):
    """ if file exists file should have a function with the following sig:
    targets_configured_for_assignement=usable_cassette(setup_object, list_of_assign_with_setup_objects)
    """
    try:
        globals={}
        locals={}
        with open(os.path.join(dir,setupname)+'.py') as f:
            exec(f.read(), globals, locals)

        return locals['usable_cassette']
    except IOError:
        raise NameError()
