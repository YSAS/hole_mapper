#!/usr/bin/env python
import numpy as np
import matplotlib.pyplot as plt
import argparse
from astropy.io import fits
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

if __name__ =='__main__':
    args=_parse_cl()

    files = [os.path.join(dirpath, f)
         for dirpath, dirnames, files in os.walk(args.dir)
         for f in files if os.path.splitext(f)[1].lower()=='.field']

    for infile in files:
        outfile='.'.join(infile.split('.')[:-1])+'.txt'
        field=load_dotfield(infile)
        with open(outfile,'w') as f:
            for h in field['T']+field['C']+field['S']+field['G']+field['A']:
                extra=str(h.get('v',''))
                extra+=str(h.get('vmag',''))
                if 'class' in h:
                    extra+='_'+str(h['class'])
                f.write("{ra:.7f} {dec:.7f} {tcode} {pri:f} {id} {extra}\n".format(
                        ra=sexconvert(h['ra'],dtype=float,ra=True),
                        dec=sexconvert(h['dec'],dtype=float,ra=False),
                        tcode=h['type'] if h['type'] != 'T' else 'O',
                        pri=float(h['priority']),
                        id=h['id'].replace(' ','_'),
                        extra=extra))


#space delimited
#ra decimal 7 min
#dec decimal
#type code  (T -> O)
#priority float
#ID char sting