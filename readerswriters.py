from target import VALID_TYPE_CODES
from collections import defaultdict
import os.path
from datetime import datetime
from jbastro.astroLib import sexconvert

#Default priority if '-'
DEFAULT_PRIORITY = float('-inf')


def _defdict(dic,default='-'):
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

#    for d in dictlist:
#        for k in d:
#            d[k]=d[k].replace(' ','_')

    rec+=[fmt.format(r=_defdict(dic)) for dic in dictlist]
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

    #Duplicates forbidden
    if len(keys) != len(set(keys)):
        raise Exception('Duplicates columns forbidden:\n {}'.format(keys))
    
    #Must have all the required keys
    if len([k for k in keys if k in REQUIRED]) != len(REQUIRED):
        missing=[k for k in REQUIRED if k not in keys]
        raise Exception('Missing required columns:\n {}'.format(missing))
    
    #Must not have any forbidden keys
    if len([k for k in keys if k in FORBIDDEN])!=0:
        raise Exception('Column name forbidden:\n {}'.format(FORBIDDEN))

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
    if 'ra' in keys:
        rdict['ra'] = sexconvert(rdict['ra'],dtype=float,ra=True)
    if 'dec' in keys:
        rdict['dec'] = sexconvert(rdict['dec'],dtype=float)
    
    #Set a priority if one isn't set
    if 'priority' in keys and 'priority' not in rdict:
        rdict['priority'] = DEFAULT_PRIORITY
    
    #Generate the default ID if one wasnt defined
    if 'id' in keys and 'id' not in rdict:
        rdict['id'] = _generate_default_id(rdict)

    if 'type' in keys:
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



