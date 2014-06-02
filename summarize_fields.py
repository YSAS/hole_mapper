#!/usr/bin/env python
from collections import defaultdict
import argparse
import os
from jbastro.astrolibsimple import sexconvert
from field import load_dotfield

def _parse_cl():
    parser = argparse.ArgumentParser(description='Help undefined',
                                     add_help=True)
    parser.add_argument('-d','--dir', dest='dir', default='./',
                        action='store', required=False, type=str,
                        help='Search directory for .field files')
    return parser.parse_args()

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


