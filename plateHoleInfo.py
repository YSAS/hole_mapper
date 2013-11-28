from platefile import resfile, ascfile
from Hole import Hole
import Cassette
import Setup
import os.path
import math
from m2fscontrolplate import Plate

SCALE=14.25
SH_RADIUS=0.1875
ORDERED_FIBER_NAMES=['{}{}-{:02}'.format(color,cnum,fnum)
                     for color in 'RB'
                     for cnum in range(1,9)
                     for fnum in range(1,17)]


class platefile(object):
    def __init__(self, filename):
        self.filename=filename

def nanfloat(s):
    """Convert string to float or nan if can't"""
    try:
        return float(s)
    except Exception:
        return float('nan')

def std_offset(c1,c2):
    """c1 sh, c2 std"""

    c1=(tuple([float(x) for x in c1[0].split()]),
        tuple([float(x) for x in c1[1].split()]))
    c2=(tuple([float(x) for x in c2[0].split()]),
        tuple([float(x) for x in c2[1].split()]))

    ra1=(c1[0][0]+c1[0][1]/60.0+c1[0][2]/3600.0)*15.0
    
    de1=c1[1][0]
    if de1<0:
        de1-=c1[1][1]/60.0+c1[1][2]/3600.0
    else:
        de1+=c1[1][1]/60.0+c1[1][2]/3600.0
    
    ra2=(c2[0][0]+c2[0][1]/60.0+c2[0][2]/3600.0)*15.0
    
    de2=c2[1][0]
    if de2<0:
        de2-=c2[1][1]/60.0+c2[1][2]/3600.0
    else:
        de2+=c2[1][1]/60.0+c2[1][2]/3600.0

    ra1*=math.pi/180.0
    de1*=math.pi/180.0
    ra2*=math.pi/180.0
    de2*=math.pi/180.0

    seps=math.acos(math.sin(de1)*math.sin(de2) +
                   math.cos(de1)*math.cos(de2)*math.cos(ra2-ra1) )


    return str(round(seps*180*3600/math.pi,2))


def _setup_nfo_to_dict(setup_nfo_list):
    nfo=setup_nfo_list
    #nfo 4 lines with endings
    #first from ascfile
    words=nfo[0].split()
    ha=words[4]
    st=words[5]
    airm=words[8]
    az=words[12]
    el=words[11]
    
    #last 3 from resfile
    words=nfo[1].split()
    ra=' '.join(words[0:3])
    de=' '.join(words[3:6])
    ep=words[6]

    import datetime
    words=nfo[3].split()
    setup_time_utc=datetime.datetime(int(words[5]), int(words[4]),
                                     int(words[3]), int(words[0]),
                                     int(words[1]), int(words[2]))
    return {'RA':ra,'DE':de,'EPOCH':ep,'UTC':setup_time_utc,
            'EL':el,'AZ':az,'AIRMASS':airm,'SIDEREAL_TIME':st,
            'OBSERVATORY':'LCO/Magellan',
            'TELESCOPE':'Clay'}

class plateHoleInfo(object):
    """
    Frontend to the .res & .asc files of a setup
    used to retrieve information about a given hole
    """
    def __init__(self,file):
        
        self.setups={}
        self.cassettes={}
        self.cassette_groups={}
        self.holeSet=set()
        self.sh_hole=None#'hole'
        self.standard={'hole':None,'offset':0.0}
        self.mechanical_holes=[]
        
        if 'Sum.asc' in file:
            self.name=os.path.basename(file)[0:-4]
            
            self.rfile=resfile(file.replace('Sum.asc','plate.res'))
            self.afile=ascfile(file)
            self.pfile_filename=file.replace('_Sum.asc','.plate')
            self._init_fromASC()
        
            if 'HotJupiters_1' in self.name:
                _postProcessHJSetups(self)

            if 'Calvet' in self.name:
                _postProcessCalvetSetups(self)
 
            if 'Carnegie' in self.name:
                _postProcessCarnegieSetups(self)
                
            if 'Kounkel_2' in self.name:
                _postProcessKounkel2Setups(self)

            #set of cassettes with same color & slit in future this
            # will come from plate file
            #h & l are used to divide the physical cassettes into a high-numbered
            #fiber logical cassette and a low-numbered liber logical cassette
            #for a given cassette h & l had better be created with the same slit
            # assignemnts!
            self.cassettes={s:Cassette.new_cassette_dict() for s in self.setups}
            self.cassette_groups={s:[Cassette.blue_cassette_names(),
                                     Cassette.red_cassette_names()]
                                  for s in self.setups}
        
            if 'Carnegie_1' in self.name:
                _postProcessIanCassettes(self)

            if 'HotJupiters_1' in self.name:
                _postProcessHJCassettes(self)

            if 'Calvet' in self.name:
                _postProcessCalvetCassettes(self)

            if 'Outer_LMC_1' in self.name:
                _postProcessNideverCassettes(self)
    
            if 'Vasily' in self.name:
                _postProcessVasilyCassettes(self)
                
            if 'Kounkel_2' in self.name:
                _postProcessKounkel2Cassettes(self)
        
        
        else:
            self.name=os.path.basename(file)[0:-6]
            self.pfile_filename=file
            self._init_from_plate(file)
        
        for s in self.setups:
            self.setups[s]['cassettes']=self.cassettes[s]

    def _init_fromASC(self):
        #add shack hartman holes
        
        #Add the SH to the global set
        self.sh_hole=Hole(0.0, 0.0, 0.0, SH_RADIUS/SCALE, type='C')
        self.holeSet.add(self.sh_hole)
        
        #add standard to plate
        awords=self.afile.seventeen.split()
        rwords=self.rfile.seventeen.split()
        std_ra=' '.join(rwords[1:4])
        std_de=' '.join(rwords[4:7])
        
        std_hole=Hole(float(awords[0])/SCALE, float(awords[1])/SCALE,
                      float(awords[2])/SCALE, float(awords[3])/SCALE,
                      type=awords[4], mattfib='R-01-17',
                      idstr=self.afile.seventeen)
        self.holeSet.add(std_hole)
        
        self.standard['hole']=std_hole
        
        
        
        #add fiducial & thumbscrew holes
        for l in self.afile.fid_thumb_lines:
            awords=l.split()
            h=Hole(float(awords[0])/SCALE,
                   float(awords[1])/SCALE,
                   float(awords[2])/SCALE,
                   float(awords[3])/SCALE,
                   type=awords[4])
            self.mechanical_holes.append(h)
            self.holeSet.add(h)
        
        #Go through all the setups in the files
        for setup_name, setup_dict in self.rfile.setups.items():
            
            #make sure setup is in both
            if setup_name not in self.afile.setups.keys():
                raise ValueError('Setup must be in both res & asc files')
            
            #create a setup
            self.setups[setup_name]=Setup.new_setup(platename=self.name,
                                                    setup_name=setup_name)
        
            targets=[]
            other=[]
            
            #Merge all the hole data in res & asc
            for i, rline in enumerate(setup_dict['setup_lines']):
                aline=self.afile.getLineNofSetup(i, setup_name)

                awords=aline.split()
                atype=awords[4]

                rwords=rline.split()
                rtype=rwords[8]

                #Verify that the asc & res files agree
                if rtype!=atype:
                    raise LookupError('Hole types different in .res & .asc')
                if rwords[0] !=awords[5]:
                    raise LookupError('old fiber assignments differ in .res & .asc')
                
                #Grab Matt's fiber assignment
                matt_fiber=rwords[0]
                
                #Perform a crappy extraction of additional hole information
                addit={}
                if rtype =='O' and len(rwords) > 9:
                    if 'F00' in rwords[9]:
                        ndx_add=1
                    else:
                        ndx_add=0
                    if len(rwords) > 10+ndx_add:
                        addit=parse_extra_data(self.name,setup_name,rwords[10+ndx_add:])
                        addit['priority']=int(rwords[9+ndx_add])
                    else:
                        addit={'priority':int(rwords[9+ndx_add])}

                    
                #Instantiate a hole
                hole=Hole(float(awords[0])/SCALE,
                     float(awords[1])/SCALE,
                     float(awords[2])/SCALE,
                     float(awords[3])/SCALE,
                     ra=tuple([x for x in rwords[1:4]]),
                     de=tuple([x for x in rwords[4:7]]),
                     ep=float(rwords[7]),
                     type=rtype,
                     mattfib=matt_fiber,
                     idstr=aline,
                     **addit)

                #Enforce holes exist only once
                if hole in self.holeSet:
                    print "Duplicate hole: {}".format(hole)
                    for h in self.holeSet:
                        if h.hash==hole.hash:
                            hole=h
                            break
                else:
                    self.holeSet.add(hole)

                #Don't add fiber 17 to any setup
                if matt_fiber[-3:-1]=='17':
                    continue

                #gather the holes
                if rtype in ('O', 'S'):
                    targets.append(hole)
                else:
                    other.append(hole)
            
            #other holes go into unused, bit of a misnomer
            self.setups[setup_name]['unused_holes']=other

            #Put science holes into a channel
            self.setups[setup_name]['holes']=targets
            setupNfo=self.afile.setups[setup_name]['setup_nfo_str']
            setupNfo.extend(self.rfile.setups[setup_name]['setup_nfo_str'])
            self.setups[setup_name]['INFO']=_setup_nfo_to_dict(setupNfo)

            if setup_name=='Setup 1':
                #compute the offset to the stadard star
                self.standard['offset']=std_offset(
                        (self.setups[setup_name]['INFO']['RA'],
                            self.setups[setup_name]['INFO']['DE']),
                            (std_ra,std_de))
            self.setups[setup_name]['INFO']['NAME']=setup_name

    def _init_from_plate(self, file):
    
        def plateDict_2_Hole(d):
            addit=d.copy()
            try:
                return Hole(float(addit.pop('x'))/SCALE,
                            float(addit.pop('y'))/SCALE,
                            float(addit.pop('z'))/SCALE,
                            float(addit.pop('r'))/SCALE,
                            **addit)
            except ValueError:
                return None

        plate=Plate(file)
        #Add the SH to the global set

        self.sh_hole=plateDict_2_Hole(plate.shackhartman)
        
        self.holeSet.add(self.sh_hole)
        
        #Add standard to plate
        std_hole=plateDict_2_Hole(plate.standard)
        self.holeSet.add(std_hole)
        self.standard={'hole':std_hole, 'offset':plate.standard_offset}
        
        #add fiducial & thumbscrew holes
        self.mechanical_holes=[plateDict_2_Hole(d) for d in plate.mechanical]
        self.holeSet.update(self.mechanical_holes)
    
        #Go through all the setups in the files
        for setup_name, setup in plate.setups.iteritems():
            
            targets=[]
            other=[]
            for t in setup._target_list:
                hole=plateDict_2_Hole(t)
                if not hole:
                    #fiber mightnot be plugged
                    continue
                #Enforce holes exist only once
                if hole in self.holeSet:
                    print "Duplicate hole: {}".format(hole)
                    for h in self.holeSet:
                        if h.hash==hole.hash:
                            hole=h
                            break
                else:
                    self.holeSet.add(hole)
                
                targets.append(hole)

            for t in setup._guide_list:
                hole=plateDict_2_Hole(t)
                #Enforce holes exist only once
                if hole in self.holeSet:
                    print "Duplicate hole: {}".format(hole)
                    for h in self.holeSet:
                        if h.hash==hole.hash:
                            hole=h
                            break
                else:
                    self.holeSet.add(hole)
                
                other.append(hole)
            
            if targets:
                #create a setup
                self.setups[setup_name]=Setup.new_setup(platename=self.name,
                                                        setup_name=setup_name)
                                                    

                #other holes go into unused, bit of a misnomer
                self.setups[setup_name]['unused_holes']=other

                #Put science holes into a channel
                self.setups[setup_name]['holes']=targets
                self.setups[setup_name]['INFO']=setup.attrib.copy()

                self.cassettes[setup_name]=Cassette.new_cassette_dict()
                for h in targets:
                    if h['FIBER']:
                        cname=h['ASSIGNMENT']['CASSETTE']
                        fnum=h['ASSIGNMENT']['FIBERNO']
                        self.cassettes[setup_name][cname].map[fnum]=h
                        self.cassettes[setup_name][cname].holes.append(h)
                        self.cassettes[setup_name][cname].used+=1
                
                self.setups[setup_name]['cassetteConfig']=self.cassettes[setup_name]
                self.cassette_groups[setup_name]=[Cassette.blue_cassette_names(),
                                                  Cassette.red_cassette_names()]

        self.plate=plate

    def cassettes_for_setup(self,setup_name):
        return self.cassettes[setup_name]
    
    def cassette_groups_for_setup(self, setup_name):
        return self.cassette_groups[setup_name]

    def write_platefile(self):

        #get list of crap for the plate
        with open(self.pfile_filename,'w') as fp:
            fp.write("[Plate]\n")
            fp.write("formatversion= 0.2\n")
            fp.write("NAME= {}\n".format(self.name))
            fp.write("STD_OFFSET= {}\n".format(self.standard['offset']))
            
            
            #Write out mechanical holes
            fp.write("[PlateHoles]\n")
            plate_holes=(self.mechanical_holes+
                        [self.sh_hole,self.standard['hole']])
            base_col_header=['x','y','z','r','type']
            fp.write("H:'" + "'\t'".join(base_col_header) + "'\n")
            fmt_str="H{n:<3}:'{" + "}'\t'{".join(base_col_header) + "}'\n"
            for i,h in enumerate(plate_holes):
                fmt_dict={'n':i,
                          'x':'%.4f'% (h.x*SCALE),
                          'y':'%.4f'% (h.y*SCALE),
                          'z':'%.4f'% (h.z*SCALE),
                          'r':'%.4f'% (h.radius*SCALE),
                          'type':h['TYPE']}
                fp.write(fmt_str.format(**fmt_dict))
    
            #Write out the setups
            s_sorted=sorted(self.setups.keys(),key=lambda s: int(s.split()[1]))
            for s in s_sorted:
                condensed_name=''.join(s.split())
                setup=self.setups[s]
                #Write out setup description section
                fp.write("[{}]\n".format(condensed_name))
                
                #Determine whitespace for setup keys & write out
                key_col_wid=max([len(k) for k in setup['INFO'].iterkeys()])+6
                k='NAME'
                v=setup['INFO']['NAME']
                fp.write("{k}={space}{v}\n".format(k=k,v=v,
                    space=' '*(key_col_wid-len(k)-1)))
                for k, v in setup['INFO'].iteritems():
                    if k=='NAME':
                        continue
                    fp.write("{k}={space}{v}\n".format(k=k,v=str(v),
                        space=' '*(key_col_wid-len(k)-1)))

                #Write out objects & sky
                ob=[h for h in setup['holes'] ]#if h.isObject()]
                fp.write("[{}:Targets]\n".format(condensed_name))
                base_col_header=['ra','dec','ep','x','y','z','r','type', 'priority',
                            'slit', 'id']
                
                extra_col_header=[]
                for h in ob:
                    extra_col_header.extend(h['CUSTOM'].keys())
                extra_col_header=list(set(extra_col_header))
                
                fp.write("H:'"+
                         "'\t'".join(base_col_header+extra_col_header)+
                         "'\n")
                fmt_str=("{fiber} : '{"+
                        "}'\t'{".join(base_col_header+extra_col_header)+
                        "}'\n")
                        
                for fiber in ORDERED_FIBER_NAMES:
                    h=[h for h in setup['holes'] if h['FIBER']==fiber]
                    assert len(h)<=1
                    if h:
                        h=h[0]
                        fmt_dict={'ra':h.ra_string(),
                                'dec':h.de_string(),
                                'ep':h['EPOCH'],
                                'x':'%.4f'% (h.x*SCALE),
                                'y':'%.4f'% (h.y*SCALE),
                                'z':'%.4f'% (h.z*SCALE),
                                'r':'%.4f'% (h.radius*SCALE),
                                'type':h['TYPE'],
                                'priority':h['PRIORITY'],
                                'id':h['ID'],
                                'fiber':fiber,
                                'slit':h['SLIT']}
                        for k in extra_col_header:
                            fmt_dict[k]=h.get(k,'')
                        fp.write(fmt_str.format(**fmt_dict))
                    else:
                        h=[h for h in setup['assignwithholes']
                           if h['FIBER']==fiber]
                        if h:
                            id='unassigned'
                        else:
                            id='inactive'
                    
                        #TODO add dead fiber support
                    
                        fmt_dict={'ra':'', 'dec':'', 'ep':'', 'x':'',
                            'y':'','z':'', 'r':'', 'type':'',
                            'priority':'', 'id':id,'fiber':fiber,
                            'slit':''} #TODO report slit from cassette
                        for k in extra_col_header:
                            fmt_dict[k]=''
                        fp.write(fmt_str.format(**fmt_dict))
    
                #Write out guide & acquisition
                ga=[h for h in setup['unused_holes'] if h['TYPE'] in ['G','A'] ]
                fp.write("[{}:Guide]\n".format(condensed_name))
                
                base_col_header=['ra','dec','ep','x','y','z','r','type']
                
                extra_col_header=[]
                for h in ga:
                    extra_col_header.extend(h['CUSTOM'].keys())
                extra_col_header=list(set(extra_col_header))
                
                fp.write("H:'"+
                         "'\t'".join(base_col_header+extra_col_header)+
                         "'\n")
                fmt_str=("G{n:<3}:'{"+
                        "}'\t'{".join(base_col_header+extra_col_header)+
                        "}'\n")
                
                for i,h in enumerate(ga):
                    fmt_dict={'n':i,
                        'ra':h.ra_string(),
                        'dec':h.de_string(),
                        'ep':h['EPOCH'],
                        'x':'%.4f'% (h.x*SCALE),
                        'y':'%.4f'% (h.y*SCALE),
                        'z':'%.4f'% (h.z*SCALE),
                        'r':'%.4f'% (h.radius*SCALE),
                        'type':h['TYPE']}
                    for k in extra_col_header:
                        fmt_dict[k]=h.get(k,'')
                    fp.write(fmt_str.format(**fmt_dict))


    
def _postProcessHJSetups(plateinfo):
    """ 
    Take the 2 setups for Nov13 Bailey plate and break them into the
    6 real setups
    """
    setups=plateinfo.setups

    #need to create three setups from each setup
    #1 is calibration
    #2 is lores (all science targets)
    #3 is hires primary field
    #4-6 is same, but for original setup 2
    new_setups={}
    
    holes=setups['Setup 1']['holes']
    
    #telluric calibrator target pool
    tpool=[h for h in holes if h.get('subclass','')=='Telluric']
    #hires targets
    ppool=[h for h in holes if h.get('subclass','')=='']
    #lo res target pool
    lpool=[h for h in holes if h.get('subclass','')=='Extra']

    import copy
    for k in ['Setup 1','Setup 2','Setup 3']:
        new_setups[k]=copy.copy(setups['Setup 1'])
        new_setups[k]['setup']=k
    new_setups['Setup 1']['holes']=tpool
    new_setups['Setup 2']['holes']=lpool
    new_setups['Setup 3']['holes']=ppool

    holes=setups['Setup 2']['holes']
    #telluric calibrator target pool
    tpool=[h for h in holes if h.get('subclass','')=='Telluric']
    #hires targets
    ppool=[h for h in holes if h.get('subclass','')=='']
    #lo res target pool
    lpool=[h for h in holes if h.get('subclass','')=='Extra']

    for k in ['Setup 4','Setup 5','Setup 6']:
        new_setups[k]=copy.copy(setups['Setup 2'])
        new_setups[k]['setup']=k
    new_setups['Setup 4']['holes']=tpool
    new_setups['Setup 5']['holes']=lpool
    new_setups['Setup 6']['holes']=ppool

    #update the setups
    plateinfo.setups=new_setups

def _postProcessCalvetSetups(plateinfo):
    """
    Drop excess targets
    """
    for s in plateinfo.setups.itervalues():
        ob=[h for h in s['holes'] if h.isObject()]
        sk=[h for h in s['holes'] if h.isSky()]
        ratio=float(len(ob))/len(sk)
        pct_keep=float(128)/(len(ob)+len(sk))
        from math import floor
        no=int(floor(pct_keep*len(ob)))
        ns=int(floor(pct_keep*len(sk)))
        ob.sort(key=lambda h: h['PRIORITY'])
        sk.sort(key=lambda h: h['PRIORITY'])
        s['holes']=ob[0:no]+sk[0:ns]

def _postProcessCarnegieSetups(plateinfo):
    """
    Drop excess targets
    """
    droptarg=[('06 49 4.92','-36 00 29.3'),
              ('06 49 3.13','-35 59 42.2'),
              ('06 49 6.67','-36 00 13.1'),
              ('06 49 17.74','-35 57 5.2'),
              ('06 49 11.16','-35 55 58.2'),
              ('06 49 22.03','-36 02 0.6'),
              ('06 49 3.09','-35 55 22.6'),
              ('06 48 56.65','-35 57 50.3'),
              ('06 49 3.09','-36 05 13.4'),
              ('06 48 54.51','-36 05 13.4'),
              ('06 48 46.44','-35 55 58.2'),
              ('06 48 39.86','-35 57 5.2'),
              ('06 48 34.08','-36 00 18.0'),
              ('06 48 46.44','-36 04 37.8'),
              ('06 48 35.57','-35 58 35.4')]
              
    def in_to_drop(hole):
        return (' '.join(h['RA']),' '.join(h['DEC'])) in droptarg
    s=plateinfo.setups['Setup 2']
    s['holes']=[h for h in s['holes'] if not in_to_drop(h)]

def _postProcessKounkel2Setups(plateinfo):
    """
    Drop excess targets
    """
    plateinfo.setups['Setup 1']['assignwithholes']=plateinfo.setups['Setup 4']['holes']
    plateinfo.setups['Setup 4']['assignwithholes']=plateinfo.setups['Setup 1']['holes']

def _postProcessIanCassettes(plateinfo):
    """
    Take the 2 setups for Nov13 Bailey plate and break them into the
    6 real setups
    """
    for c in plateinfo.cassettes_for_setup('Setup 2').values():
        if 'l' in c.name:
            if 'R8' in c.name:
                c.usable=[1]
            else:
                c.usable=[1,8]
        else:
            if 'R8' in c.name:
                c.usable=[9,16]
            else:
                c.usable=[15]

def _postProcessHJCassettes(plateinfo):
    for s in ['Setup 3','Setup 6']:
        for c in plateinfo.cassettes_for_setup(s).values():
            if 'l' in c.name:
                c.usable=[2,4,6,8]
            else:
                c.usable=[10,12,14,16]
    for c in plateinfo.cassettes_for_setup('Setup 4').values():
        if 'l' in c.name:
            c.usable=[2]
        else:
            c.usable=[16]
    for c in plateinfo.cassettes_for_setup('Setup 1').values():
        #have 8 want in fiber 8 of every other tetris
        if c.name[1] in ['1','3','5','7']:
            if 'l' in c.name:
                c.usable=[8]
            else:
                c.usable=[]
        else:
            c.usable=[]
    for s in ['Setup 2','Setup 5']:
        for c in plateinfo.cassettes_for_setup(s).values():
            if 'l' in c.name:
                c.usable=range(1,8,2)
            else:
                c.usable=range(9,16,2)

def _postProcessCalvetCassettes(plateinfo):
    for c_set in plateinfo.cassettes.values():
        for c in c_set.values():
            if 'l' in c.name:
                c.usable=[2,4,6,8]
            else:
                c.usable=[10,12,14,16]

def _postProcessVasilyCassettes(plateinfo):
    #Setups 1, 2, 3, 4
    ok=['B1','R1','B5','R5','B2','R2','B6','R6']
    for c in plateinfo.cassettes_for_setup('Setup 1').values():
        if c.name[0:2] in ok:
            if 'l' in c.name:
                c.usable=range(1,9)
            else:
                c.usable=range(9,17)
        else:
            c.usable=[]
    plateinfo.cassette_groups['Setup 1']=[[i+k for i in ok for k in 'lh']]
    
    ok=['B3','R3','B7','R7','B4','R4','B8','R8']
    for c in plateinfo.cassettes_for_setup('Setup 2').values():
        if c.name[0:2] in ok:
            if 'l' in c.name:
                c.usable=range(1,9)
            else:
                c.usable=range(9,17)
        else:
            c.usable=[]
    plateinfo.cassette_groups['Setup 2']=[[i+k for i in ok for k in 'lh']]

def _postProcessKounkel2Cassettes(plateinfo):
    cnames=Cassette.new_cassette_dict().keys()

    ok3=['B1h','R3h','B5h','R7h']
    ok5=['R2l','R6h','R6l']
    filtered_left=[c for c in Cassette.left_only(cnames) if c not in ok5]
    filtered_right=[c for c in Cassette.right_only(cnames) if c not in ok3]
    ok3+=filtered_left
    ok5+=filtered_right
    #Setups 3
    ok=ok3
    for c in plateinfo.cassettes_for_setup('Setup 3').values():
        if c.name in ok:
            if 'l' in c.name:
                c.usable=range(1,9)
            else:
                c.usable=range(9,17)
        else:
            c.usable=[]
    plateinfo.cassette_groups['Setup 3']=[ok]
    #Setup 5
    ok=ok5
    for c in plateinfo.cassettes_for_setup('Setup 5').values():
        if c.name in ok:
            if 'l' in c.name:
                c.usable=range(1,9)
            else:
                c.usable=range(9,17)
        else:
            c.usable=[]
    plateinfo.cassette_groups['Setup 5']=[ok]


def _postProcessNideverCassettes(plateinfo):
    #Setups 1, 2, 3, 4
    ok=['B1','B5','B2','B6']
    for c in plateinfo.cassettes_for_setup('Setup 1').values():
        if c.name[0:2] in ok:
            if 'l' in c.name:
                c.usable=range(1,9)
            else:
                c.usable=range(9,17)
        else:
            c.usable=[]
    plateinfo.cassette_groups['Setup 1']=[[i+k for i in ok for k in 'lh']]

    ok=['R1','R5','R2','R6']
    for c in plateinfo.cassettes_for_setup('Setup 2').values():
        if c.name[0:2] in ok:
            if 'l' in c.name:
                c.usable=range(1,9)
            else:
                c.usable=range(9,17)
        else:
            c.usable=[]
    plateinfo.cassette_groups['Setup 2']=[[i+k for i in ok for k in 'lh']]

    ok=['B3','B7','B4','B8']
    for c in plateinfo.cassettes_for_setup('Setup 3').values():
        if c.name[0:2] in ok:
            if 'l' in c.name:
                c.usable=range(1,9)
            else:
                c.usable=range(9,17)
        else:
            c.usable=[]
    plateinfo.cassette_groups['Setup 3']=[[i+k for i in ok for k in 'lh']]

    ok=['R3','R7','R4','R8']
    for c in plateinfo.cassettes_for_setup('Setup 4').values():
        if c.name[0:2] in ok:
            if 'l' in c.name:
                c.usable=range(1,9)
            else:
                c.usable=range(9,17)
        else:
            c.usable=[]
    plateinfo.cassette_groups['Setup 4']=[[i+k for i in ok for k in 'lh']]

    #Setups 5, 6, 7, 8
    ok=['B1','B5','B2','B6']
    for c in plateinfo.cassettes_for_setup('Setup 5').values():
        if c.name[0:2] in ok:
            if 'l' in c.name:
                c.usable=range(1,9)
            else:
                c.usable=range(9,17)
        else:
            c.usable=[]
    plateinfo.cassette_groups['Setup 5']=[[i+k for i in ok for k in 'lh']]

    ok=['R1','R5','R2','R6']
    for c in plateinfo.cassettes_for_setup('Setup 6').values():
        if c.name[0:2] in ok:
            if 'l' in c.name:
                c.usable=range(1,9)
            else:
                c.usable=range(9,17)
        else:
            c.usable=[]
    plateinfo.cassette_groups['Setup 6']=[[i+k for i in ok for k in 'lh']]

    ok=['B3','B7','B4','B8']
    for c in plateinfo.cassettes_for_setup('Setup 7').values():
        if c.name[0:2] in ok:
            if 'l' in c.name:
                c.usable=range(1,9)
            else:
                c.usable=range(9,17)
        else:
            c.usable=[]
    plateinfo.cassette_groups['Setup 7']=[[i+k for i in ok for k in 'lh']]

    ok=['R3','R7','R4','R8']
    for c in plateinfo.cassettes_for_setup('Setup 8').values():
        if c.name[0:2] in ok:
            if 'l' in c.name:
                c.usable=range(1,9)
            else:
                c.usable=range(9,17)
        else:
            c.usable=[]
    plateinfo.cassette_groups['Setup 8']=[[i+k for i in ok for k in 'lh']]

def parse_extra_data(name,setup, words):
    ret={}
    #import pdb;pdb.set_trace()
    #Carnegie
    if name=='Carnegie_1_Sum':
        if setup=='Setup 1':
            x,y,z=words[0].split('_')
            ret['foo']=x
            ret['bar']=y
            ret['baa']=z
        if setup=='Setup 2':
            keys=['ID','V','V-I','d']
            fields=words[0].split('_')
            for i,x in enumerate(fields):
                field=x.split('=')
                if len(field)>1:
                    ret[keys[i]]=field[1]
            if 'V-I' in ret:
                ret['COLOR']=nanfloat(ret['V-I'])
            if 'V' in ret:
                ret['MAGNITUDE']=nanfloat(ret['V'])
        if setup=='Setup 3':
            ret['ID']=words[0]
    #Nuria 1
    if name=='Calvet_1_Sum':
        if setup in ['Setup 1','Setup 2','Setup 6']:
            id,mag=words[0].split('_')
        else:
            id1,id2,mag=words[0].split('_')
            id=id1+'_'+id2
        ret['ID']=id
        ret['V?']=mag
        ret['MAGNITUDE']=nanfloat(mag)
    #Nuria 1
    if name=='Calvet_2_Sum':
        if setup in ['Setup 1','Setup 2','Setup 3','Setup 4','Setup 5']:
            id,mag=words[0].split('_')
        else:
            id1,id2,mag=words[0].split('_')
            id=id1+'_'+id2
        ret['ID']=id
        ret['V?']=mag
        ret['MAGNITUDE']=nanfloat(mag)
    #Jeb
    if name=='HotJupiters_1_Sum':
        l=words[0].split('_')
        ret['ID']=l[0]
        ret['V']=l[1]
        ret['MAGNITUDE']=nanfloat(l[1])
        if len(l)>2:
            ret['subclass']=l[2]
    #Fornax_1
    if name=='Fornax_1_Sum':
        l=words[0].split('=')
        ret['V']=l[1]
        ret['MAGNITUDE']=nanfloat(l[1])
    #David
    if name=='Outer_LMC_1_Sum':
        ret['ID']=words[0]
    #Carina_1
    if name=='VasilyStream_1_Sum':
        l=words[0].split('_')
        ret['i']=l[3]
        ret['g']=l[2]
        ret['MAGNITUDE']=nanfloat(l[2])

    return ret
