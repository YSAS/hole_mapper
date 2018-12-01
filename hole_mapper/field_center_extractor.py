#!/usr/bin/env python
from glob import glob
from jbastro.astrolibsimple import sexconvert
import argparse, os

def parse_cl():
    parser = argparse.ArgumentParser(description='List field centers',
                                     add_help=True)
    parser.add_argument('-d','--dir', dest='dir',
                        action='store', required=False, type=str,
                        help='source dir for files',default='./')
    return parser.parse_args()

args=parse_cl()


files = [os.path.join(dirpath, f)
         for dirpath, dirnames, files in os.walk(args.dir)
         for f in files
         if '.pdf' not in f and '.gz' not in f and
         '.zip' not in f and f[0]!='.' and '.py' not in f]

for file in files:
    with open(file) as f:
        lines=f.readlines()
        try:
            tcol=[l.lower().split().index('type') for l in lines
                  if 'type' in l.lower()][0]
        except Exception:
            tcol=4
        field_line_gen=(l for l in lines
                   if l.lower().strip().startswith('field'))
        sh_line_gen=(l for l in lines if len(l.lower().split())>=5 and
                     l.lower().split()[tcol]=='c')
        fields=[l.split('=')[1].strip() for l in field_line_gen]
        coords=[' '.join(l.split()[:3]) for l in sh_line_gen]

    print '#{}'.format(file)
    if len(fields)!=len(coords):
        print ('#WARNING: Mismatch in fieldnames and field centers')
    for n,c in zip(fields,coords):
        ra=sexconvert(c.split()[0],ra=1, fmt='{: 03.0f} {:02} {:07.4f}')
        de=sexconvert(c.split()[1], fmt='{: 03.0f} {:02} {:07.4f}')
        print '{:20} {}  {}  {}'.format(n,ra,de,c.split()[2])