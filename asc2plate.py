#!/usr/bin/env python
import numpy as np
import matplotlib.pyplot as plt
import argparse
import os
from fieldmanager import write_dotplate


#writing a plate:
#  plate_holes=fieldmanager.Manager.plate_drillable_dictlist()
#   fieldmanager.write_dotplate(name, plate_holes, list_of_field.FieldCatalog)


plate_holes=[
 {'id':'FIDHOLE','type':'F','x':-13.7500,'y': 2.5000,'z':-1.5000,'d':0.2600},
 {'id':'FIDHOLE','type':'F','x': 13.7500,'y': 2.5000,'z':-1.5000,'d':0.2600},
 {'id':'FIDHOLE','type':'F','x':-13.7500,'y':-2.5000,'z':-1.5000,'d':0.2600},
 {'id':'FIDHOLE','type':'F','x': 13.7500,'y':-2.5000,'z':-1.5000,'d':0.2600},
 {'id':'THUMBSCREW','type':'B','x': -12.1250,'y':7.0000,'z':-1.5000,'d':0.2600},
 {'id':'THUMBSCREW','type':'B','x': -2.9100,'y':-13.6950,'z':-1.5000,'d':0.2600},
 {'id':'THUMBSCREW','type':'B','x': 12.1250,'y':5.6940,'z':-1.5000,'d':0.2600}]

class ascFieldCat(object):
    def __init__(self,name, file, obsdate, ra, dec, az,
                 el, ha, st, airmass, holedictlist):
        """
        holedictlist is list of dicts with the keys:
            x,y,z,d, type, id, ra, dec, pm_ra, pm_dec, epoch, priority
        
        obsdate in form of '2016-02-05 06:00:00'
    
        az, el, airmass,ha, st as decimals
        
        ra and dec as sexigesmal strings e.g. 09:59:18.2808
        """
        self.name=name
        self.file=file
        self.ha=ha
        self.st=st
        self.az=az
        self.el=el
        self.airmass=airmass
        self.ra=ra
        self.dec=dec
        self.obsdate=obsdate
        self.minsky=0
        self.maxsky=256
        self.mustkeep='False'
        self.holedictlist=holedictlist

    def get_info_dict(self ):
        """ this function must emulate field.FieldCatalog.get_info_dict()"""
        ret={'name':self.name,
             'file':self.file,
             'obsdate':self.obsdate,
             'mustkeep':self.mustkeep,
             'minsky':str(self.minsky),
             'maxsky':str(self.maxsky),
             '(ra, dec)':'{} {}'.format(self.ra,self.dec),
             '(az, el)':'{:3f} {:3f}'.format(float(self.az), float(self.el)),
             '(ha, st)':'{:3f} {:3f}'.format(float(self.ha), float(self.st)),
             'airmass':'{:2f}'.format(float(self.airmass)),
             'sh_hdr':'',
             'sh_rec':''}

        return ret

    def drillable_dictlist(self):
        """
        this function must emulate field.FieldCatalog.drillable_dictlist()
        """
        return self.holedictlist

    def undrillable_dictlist(self):
        return {}

    def standards_dictlist(self):
        return {}


def ascload(ascfile):
    setups={}
    fid_thumb_lines=[]
    cal_line=''
    with open(ascfile,"r") as fin:
        for line in fin:
            words=line.split()
            if words[0]=='Setup':
                currsetup=words[0]+' '+words[1]
                ha,st=words[4],words[5]
                airmass=words[8]
                el,az=words[11],words[12]
                setups[currsetup]={'ha':ha,'st':st,'airmass':airmass,
                                   'el':el,'az':az,'name':currsetup,
                                   'asclines':[]}
            elif words[5][-2:]!='17':
                if words[4] not in 'FT':
                    setups[currsetup]['asclines'].append(line)
                if currsetup=='Setup 1' and words[4] in 'FT':
                    fid_thumb_lines.append(line)
            else:
                cal_line=line
    return setups,fid_thumb_lines,cal_line


def resload(resfile):
    """Loads and parses files with lines of format
    B-01-01  01 08 10.42  -72 54 25.6  2000.0  O      F00-   806  I=19.64
    word[0] oldFiber
    word[1:8] sky coords
    word[8] object type
    word[9:] additional info
    """

    setups={}
    cal_line=''
    with open(resfile,"r") as fin:
        i=0
        currsetup=1
        for line in fin:
            if i==0:
                setups['Setup %d'%currsetup]={'setup_nfo_str':[line],
                                              'reslines':[]}
                i+=1
            elif i<3:
                setups['Setup %d'%currsetup]['setup_nfo_str'].append(line)
                i+=1
            else:
                #is a hole line or end
                words=line.split()
                if words[0] == 'END':
                    i=0
                    currsetup+=1
                else:
                    if words[0][-2:]!='17':
                        setups['Setup %d'%currsetup]['reslines'].append(line)
                    else:
                        cal_line=line

    for name, setup in setups.items():

        #process setup['setup_nfo_str']
        words=setup['setup_nfo_str'][0].split()
        ra=':'.join(words[:3])
        dec=':'.join(words[3:6])
        epoch=words[6]
        words=words=setup['setup_nfo_str'][2].split()
        obsdate='{}-{}-{} {}:{}:{}'.format(words[5],words[4],words[3],
                                           words[0],words[1],words[2])
        setup['obsdate']=obsdate
        setup['ra']=ra
        setup['dec']=dec
        setup['epoch']=epoch
        setup.pop('setup_nfo_str')

    return setups

def res4asc(ascfile):
    path=os.path.dirname(ascfile)
    file=os.path.basename(ascfile)
    name='.'.join(file.split('.')[:-1]).replace('_Sum','')
    return os.path.join(path, name+'_plate.res')

def ascresloader(ascfile, resfile=''):

    path=os.path.dirname(ascfile)
    file=os.path.basename(ascfile)
    name='.'.join(file.split('.')[:-1]).replace('_Sum','')
    
    
    if not resfile: resfile=os.path.join(path, name+'_plate.res')
    
    
    #read in the raw files
    ascset,_,cal_line=ascload(ascfile)
    resset=resload(resfile)

    #consistency check
    if set(ascset.keys())!=set(resset.keys()):
        print 'asc and res files must have same number of setups'
        sys.exit()

    #parse lines of each res/asc setup into a into dummy field catalog
    catlist=[]
    for sn in ascset.keys():

        #consistency check (recall guideref are only in asc file
        nguide=sum([1 if l.split()[8].lower()=='g' else 0
                    for l in resset[sn]['reslines']])
        
        if len(ascset[sn]['asclines'])-3*nguide != len(resset[sn]['reslines']):
            print '{} does not have the same number of entries in res and asc files'.format(sn)
#            sys.exit()

        holes=[]
        for i,l in enumerate(resset[sn]['reslines']):
        
            #break line into words
            reswords=l.split()
            ascwords=ascset[sn]['asclines'][i].split()
            
            #consistency check
            if ascwords[-1]!=reswords[0]:
                print 'Line {} of {} mismatch in asc and res'.format(i,sn)
                sys.exit()

            #parse ascwords into a target/hole dict
            x,y,z,d=ascwords[:4]
            type={'O':'T','A':'A','G':'G','R':'R','S':'S'}[ascwords[4]]


            #parse reswords into a target/hole dict

            #RA
            h,m,s=reswords[1:4]
            m=int(m)
            s=float(s)
            if s==60:
                m=m+1
                s=0
            s='{:05.2f}'.format(s)
            if m>=60:
                m-=60
                if h[0]=='-':
                    h=int(h)-1
                else:
                    h=int(h)+1
            else:
                h=int(h)
            m='{:02}'.format(m)
            h='{:3}'.format(h)
            if reswords[1]=='-' and h[0]!='-': h='-'+h

            ra=':'.join([h,m,s])

            #DEC
            deg,m,s=reswords[4:7]
            m=int(m)
            s=float(s)
            if s==60:
                m=m+1
                s=0
            s='{:05.2f}'.format(s)
            if m>=60:
                m-=60
                if deg[0]=='-':
                    deg=int(deg)-1
                else:
                    deg=int(deg)+1
            else:
                deg=int(deg)
            m='{:02}'.format(m)
            deg='{:3}'.format(deg)
            if reswords[1]=='-' and deg[0]!='-': deg='-'+deg

            dec=':'.join([deg,m,s])


            epoch=reswords[7]
            id=(ra+'_'+dec).replace(' ','')

            x={'x':x,'y':y,'z':z,'d':d,'type':type,
               'id':id, 'ra':ra, 'dec':dec,
               'pm_ra':'-','pm_dec':'-', 'epoch':epoch, 'priority':0.00}

            holes.append(x)
    
        #make a dict og guide ids and positions
        guides={x['id']:(float(x['x']),float(x['y']))
                for x in holes if x['type']=='G'}
    
        #do the guideref holes
        for i,l in enumerate(ascset[sn]['asclines']):

            #break line into words
            ascwords=ascset[sn]['asclines'][i].split()
            
            if ascwords[4].lower()!='r': continue
            
            #parse ascwords into a target/hole dict
            x,y,z,d=ascwords[:4]
            type='R'
            ra='00:00:00.00'
            dec='00:00:00.00'
            epoch='2000'
            
            
            #figure out which guide they go with by proximity
            guided=[(id,np.sqrt((float(x)-g[0])**2+(float(y)-g[1])**2)) for id,g in guides.items()]
            guided.sort(key=lambda x:x[1])
            
            id=guided[0][0]

            x={'x':x,'y':y,'z':z,'d':d,'type':type,
               'id':id, 'ra':ra, 'dec':dec,
               'pm_ra':'-','pm_dec':'-', 'epoch':epoch, 'priority':0.00}

            holes.append(x)

        #create the dummy catalog
        cat=ascFieldCat(name+'_'+sn.replace('Setup ','Field'),
                        file,
                        resset[sn]['obsdate'],
                        resset[sn]['ra'],
                        resset[sn]['dec'],
                        ascset[sn]['az'],ascset[sn]['el'],
                        ascset[sn]['ha'], ascset[sn]['st'],
                        ascset[sn]['airmass'],
                        holes)

        #add to the list of catalogs
        catlist.append(cat)


        x,y,z,d=cal_line.split()[:4]
        std={'id':'STANDARD','type':'Z','x':x,'y':y,'z':z,'d':d}


    return name,catlist,std


PROG_DESC='Convert a .res/.asc pair to a .plate'

def parse_cl():
    parser = argparse.ArgumentParser(description=PROG_DESC,
                                     add_help=True)
    parser.add_argument('asc', action='store', type=str,
                        help='ascfile',default='')
    parser.add_argument('res',action='store', type=str,
                        help='resfile',default='')
    return parser.parse_args()

def ascres2plate(ascfile,resfile):

    name,catlist,std=ascresloader(ascfile, resfile)
    ph=list(plate_holes)
    ph.append(std)
    dir=os.path.dirname(ascfile)
    if os.path.exists(os.path.join(dir,'{}.plate'.format(name))):
        raise IOError('File exists')
    write_dotplate(name, ph, catlist, dir=dir)

if __name__ =='__main__':
    args=parse_cl()

    ascres2plate(args.asc, args.res)

import glob
dir='/Users/one/toconvert_feb14/'
ascfiles=glob.glob(dir+'*.asc')
for f in ascfiles: ascres2plate(f,'')


sum([l.split()[8]=='O' for l in r['Setup 1']['reslines']]),sum([l.split()[4]=='O' for l in a[0]['Setup 1']['asclines']])
len(a[0]['Setup 1']['asclines'])
