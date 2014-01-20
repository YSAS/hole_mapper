from collections import defaultdict


PLATEHOLE_REQUIRED_COLS=['id','x','y','z','d']
UNDRILLABLE_REQUIRED_COLS=['id','ra','dec','epoch','priority','type',
                           'conflicts']
STANDARDS_REQUIRED_COLS=['id','ra','dec','epoch','priority']
DRILLABLE_REQUIRED_COLS=['id','ra','dec','epoch','priority','type', 'x','y',
                         'z','d']
DRILLFILE_REQUIRED_COLS=['x','y','z','d','type','id']


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

def defdict(dic,default='-'):
    x=defaultdict(lambda:default)
    x.update(dic)
    return x

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


def write(name, plate_holes, fields, dir='./'):
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


class Plate(object):
    def __init__(self):
        self.plate_holes
        self.name=
        self.file=
        self.user=
        




