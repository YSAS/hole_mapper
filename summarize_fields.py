#!/usr/bin/env python
from collections import defaultdict
import argparse
import os
from jbastro.astroLib import sexconvert
def _parse_cl():
    parser = argparse.ArgumentParser(description='Help undefined',
                                     add_help=True)
    parser.add_argument('-d','--dir', dest='dir', default='./',
                        action='store', required=False, type=str,
                        help='Search directory for .field files')
    return parser.parse_args()

#List of valid type codes
VALID_TYPE_CODES=['T', 'S', 'C', 'G', 'A', 'Z','O']

#List of required keys
REQUIRED_KEYS=['ra', 'dec', 'epoch', 'id', 'type', 'priority']

#List of forbidden keys
FORBIDDEN_KEYS=['fiber', 'x', 'y', 'z', 'r', 'ep', 'de']

#Default priority if '-'
DEFAULT_PRIORITY = float('-inf')


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
    rdict={keys[i].lower():vals[i] for i in range(len(keys)) if vals[i] !='-'}
    
    #Vet all the keys
    for k in rdict.keys():
        if not KEY_VETTERS[k](rdict[k]):
            raise Exception('Key error {} for: {}'.format(k,rec))

    #Make sure all the required keys are set
    for k in REQUIRED_KEYS:
        if k not in ['id', 'priority']:
            assert k in rdict
    
    #Enforce cannonical RA & DEC format
    rdict['ra'] = sexconvert(rdict['ra'],ra=True)
    rdict['dec'] = sexconvert(rdict['dec'])
    
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


#Define vetting functions for keys
KEY_VETTERS=defaultdict(lambda : lambda x: len(x.split())==1)
KEY_VETTERS['ra']=_is_valid_ra
KEY_VETTERS['dec']=_is_valid_dec
KEY_VETTERS['epoch']=_is_floatable
KEY_VETTERS['type']=lambda x: x in VALID_TYPE_CODES
KEY_VETTERS['priority']=_is_floatable
KEY_VETTERS['pm_ra']=_is_floatable
KEY_VETTERS['pm_dec']=_is_floatable


def load_dotfield(file):
    """
    returns {'name':field_name,
                'G':dictlist,
                'T':dictlist,
                'C':dictlist,
                'A':dictlist,
                'S':dictlist,
                'Z':dictlist}
    or raises error if file has issues.
    """
#    try:
    ret={'file':os.path.basename(file),
         'G':[], 'T':[], 'C':[], 'A':[], 'S':[], 'Z':[]}

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
                    v=v.strip()
                    assert v != ''
                except Exception as e:
                    raise Exception('Bad key=value formatting: {}'.format(str(e)))
                if k in VALID_TYPE_CODES:
                    raise Exception('Key {} not allowed.'.format(k))
                if k in ret:
                    raise Exception('Key {} may only be defined once.'.format(k))
                ret[k]=v
            elif l.lower().startswith('ra'):
                keys=_parse_header_row(l.lower())
            else:
                rec = _parse_record_row(l, keys)
                ret[rec['type']].append(rec)
    except Exception as e:
        raise Exception('Failed on line '
                        '{}: {}\n  Error:{}'.format(lines.index(l),l,str(e)))
    #Use the s-h (or field center id if none) as the field name if one wasn't
    # defined
    if 'name' not in ret:
        ret['name']=ret['C'][0]['id']

    return ret

def _make_fmt_string(keys, recs):
    max_lens=[max([len(str(r[k])) for r in recs]) for k in keys]
    l_strs=[('>' if l >0 else '<')+str(abs(l)) for l in max_lens]
    fmt_segs=["{r["+keys[i]+"]:"+l_strs[i]+"}" for i in range(len(keys))]
    return ' '.join(fmt_segs)


if __name__ =='__main__':
    args=_parse_cl()
    files = [os.path.join(dirpath, f)
             for dirpath, dirnames, files in os.walk(args.dir)
             for f in files if os.path.splitext(f)[1].lower()=='.field']

    #Load the fields
    fields=[]
    for f in files:
        try:
            fields.append(load_dotfield(f))
        except Exception as e:
            print "Failed to load: {} \n    {}".format(f,e)

    #Generate basic stats on them
    field_nfo_dicts=[]
    for field in fields:
        field_nfo_dicts.append({'name':field['name'],
                                'file':field['file'],
                                'nC':len(field['C']),
                                'nG':len(field['G']),
                                'nA':len(field['A']),
                                'nT':len(field['T']),
                                'nS':len(field['S']),
                                'nZ':len(field['Z'])})

    header_dict={'name':'Fieldname',
                 'file':'Filename',
                 'nC':'Num S-H',
                 'nG':'Num Guide',
                 'nA':'Num Acq',
                 'nT':'Num Targ',
                 'nS':'Num Sky',
                 'nZ':'Num Stds'}
    keys=['name', 'file', 'nC', 'nG', 'nA', 'nT', 'nS', 'nZ']
    fmt_str=_make_fmt_string(keys, [header_dict]+field_nfo_dicts)
    print fmt_str.format(r=header_dict)
    for r in field_nfo_dicts:
        print fmt_str.format(r=r)


