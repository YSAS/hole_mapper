from platefile import resfile, ascfile
from Hole import Hole
import Cassette
import Setup
import os.path

SCALE=14.25

class platefile(object):
    def __init__(self, filename):
        self.filename=filename


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
    ep=' '.join(words[6])

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
        
        #load the res & asc files
        
        if 'Sum.asc' in file:
            self.name=os.path.basename(file)[0:-4]
            
            self.rfile=resfile(file.replace('Sum.asc','plate.res'))
            self.afile=ascfile(file)
            self.pfile=platefile(file.replace('_Sum.asc','.plate'))
        else:
            self.name=os.path.basename(file)[0:-6]
            self.pfile=platefile(file)
    
        self.foobar=[]
        self.setups={}
        self.holeSet=set()
        
        if self.afile !=None:
            self._init_fromASC()
        else:
            self._init_from_plate()

        if 'HotJupiters_1' in self.name:
            _postProcessHJSetups(self)

        if 'Calvet' in self.name:
            _postProcessCalvetSetups(self)

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

    def _init_fromASC(self):
        
        #add standard to plate
        awords=self.afile.seventeen.split()
    
        self.holeSet.add(Hole(float(awords[0])/SCALE,
                        float(awords[1])/SCALE,
                        float(awords[2])/SCALE,
                        float(awords[3])/SCALE,
                        type=awords[4],
                        mattfib='R-01-17',
                        idstr=self.afile.seventeen))
        
        for l in self.afile.fid_thumb_lines:
            awords=l.split()
            self.holeSet.add(Hole(float(awords[0])/SCALE,
                                  float(awords[1])/SCALE,
                                  float(awords[2])/SCALE,
                                  float(awords[3])/SCALE,
                                  type=awords[4],
                                  mattfib='',
                                  idstr=l))
    
        #Go through all the setups in the files
        for setup_name, setup_dict in self.rfile.setups.items():
            
            #add holes to R side first
            channel='armR'
            
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
                if rtype =='O':
                    if 'F00' in rwords[9]:
                        ndx_add=1
                    else:
                        ndx_add=0
                    if len(rwords) > 10+ndx_add:
                        addit=parse_extra_data(self.name,setup_name,rwords[10+ndx_add:])
                        addit['PRIORITY']=int(rwords[9+ndx_add])
                    else:
                        addit={'PRIORITY':int(rwords[9+ndx_add])}

                    
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
            
            #other holes go into unused
            self.setups[setup_name]['unused_holes']=other

            #Put science holes into a channel
            self.setups[setup_name]['holes']=targets
            setupNfo=self.afile.setups[setup_name]['setup_nfo_str']
            setupNfo.extend(self.rfile.setups[setup_name]['setup_nfo_str'])
            self.setups[setup_name]['INFO']=_setup_nfo_to_dict(setupNfo)
    
    def cassettes_for_setup(self,setup_name):
        return self.cassettes[setup_name]
    
    def cassette_groups_for_setup(self, setup_name):
        return self.cassette_groups[setup_name]

    def available_cassettes(self, hole, setup_name):
        """
        Return cassette(s) name's containing fibers which can be used for hole
        """
        #Filter cassettes based on slit width & fiber availability
        available=filter(lambda x: x.slit==hole['SLIT'] and x.n_avail() > 0,
                         self.cassettes[setup_name].values())
        ret=[c.name for c in available]
        return ret

    def write_platefile(self):

        #get list of crap for the plate
        with open(self.pfile.filename,'w') as fp:
            fp.write("[Plate]\n")
            fp.write("formatversion=0.1\n")
            fp.write("name={}\n".format(self.name))

            s_sorted=sorted(self.setups.keys(),key=lambda s: int(s.split()[1]))
            for s in s_sorted:
                condensed_name=''.join(s.split())
                setup=self.setups[s]
                #Write out setup description section
                fp.write("[{}]\n".format(condensed_name))
                fp.write("name={}\n".format(s))
                
                #determine whitespace
                key_col_wid=max([len(k) for k in setup['INFO'].iterkeys()])+6
                for k, v in setup['INFO'].iteritems():
                    fp.write("{k}={space}{v}\n".format(k=k,v=v,
                        space=' '*(key_col_wid-len(k)-1)))

                #Write out objects & sky
                ob=[h for h in setup['holes'] ]#if h.isObject()]
                fp.write("[{}:Targets]\n".format(condensed_name))
                base_col_header=['ra','dec','ep','x','y','z','r','type', 'priority',
                            'id', 'fiber']
                
                extra_col_header=[]
                for h in ob:
                    extra_col_header.extend(h['CUSTOM'].keys())
                extra_col_header=list(set(extra_col_header))
                
                fp.write("H:'"+
                         "'\t'".join(base_col_header+extra_col_header)+
                         "'\n")
                fmt_str=("T{n}:'{"+
                        "}'\t'{".join(base_col_header+extra_col_header)+
                        "}'\n")
                
                for i,h in enumerate(ob):
                    fmt_dict={'n':i,
                        'ra':h.ra_string(),
                        'dec':h.de_string(),
                        'ep':h['EPOCH'],
                        'x':'%.4f'% (h.x*SCALE),
                        'y':'%.4f'% (h.y*SCALE),
                        'z':'%.4f'% (h.z*SCALE),
                        'r':'%.4f'% (h.radius*SCALE),
                        'type':h['TYPE'],
                        'priority':h['PRIORITY'],
                        'id':h['ID'],
                        'fiber':h['FIBER']}
                    for k in extra_col_header:
                        fmt_dict[k]=h.get(k,'')
                    fp.write(fmt_str.format(**fmt_dict))



def _assignTargetsToChannel(targetHoleList):
    """
    Break list of holes into two groups: armB & armR

    Default puts all in armB if fewer than 1-128
    if more divide evenly with boths arms, apportion sky
    evenly as well
    """
    skys=[h for h in targetHoleList if h.isSky()]
    objs=[h for h in targetHoleList if h.isObject()]
    if len(objs)+len(skys) < 129:
        return (objs+skys,[])
    else:
        import random
        random.shuffle(objs)
        armB=objs[0:len(objs)/2]+skys[0:len(skys)/2]
        armR=objs[len(objs)/2:]+skys[len(skys)/2:]
        assert len(armR)<129
        assert len(armB)<129
        return (armB,armR)
    
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

def _postProcessIanCassettes(plateinfo):
    """
    Take the 2 setups for Nov13 Bailey plate and break them into the
    6 real setups
    """
    for c in plateinfo.cassettes_for_setup('Setup 2').values():
        if 'l' in c.name:
            c.usable=[1,8]
        else:
            c.usable=[9,15,16] #[1,2,8,9,15,16] or [1,8,15]

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

def nanfloat(s):
    """Convert string to float or nan if can't"""
    try:
        return float(s)
    except Exception:
        return float('nan')

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
    if name=='Outer_LMC_1_Sum':
        ret['ID']=words[0]


    return ret

