from platefile import resfile, ascfile
from Hole import Hole
import Cassette
import Setup
import os.path

SCALE=14.25

class platefile(object):
    def __init__(self, filename):
        self.filename=filename

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
        
        #set of cassettes with same color & slit in future this
        # will come from plate file
        #h & l are used to divide the physical cassettes into a high-numbered
        #fiber logical cassette and a low-numbered liber logical cassette
        #for a given cassette h & l had better be created with the same slit
        # assignemnts!
        self.cassette_groups={s:[Cassette.blue_cassette_names(),
                                 Cassette.red_cassette_names()]
                              for s in self.setups}
        
        self.cassettes={s:Cassette.new_cassette_dict() for s in self.setups}
        
        if 'HotJupiters_1' in self.name:
            _postProcessHJ(self)
        if 'Carnegie_1' in self.name:
            _postProcessIan(self)

    def _init_fromASC(self):
        #Go through all the setups in the files
        for setup_name, setup_dict in self.rfile.setups.items():
            
            #add holes to R side first
            channel='armR'
            
            #make sure setup is in both
            if setup_name not in self.afile.setups.keys():
                raise ValueError('Setup must be in both res & asc files')
            
            #create a setup
            self.setups[setup_name]=Setup.new_setup(platename=self.name,setup_name=setup_name)
        
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
                mag=0.0
                id=''
                subclass=''
                if rtype =='O' and rwords[10:]!=[]:
                    additnfo=(' '.join(rwords[10:])).split('_')
                    if len(additnfo)>2:
                        subclass=' '.join(additnfo[2:])
                    mag=float(additnfo[1])
                    id=additnfo[0]
                
                #Instantiate a hole
                hole=Hole(float(awords[0])/SCALE,
                     float(awords[1])/SCALE,
                     float(awords[3])/SCALE,
                     ra=tuple([float(x) for x in rwords[1:4]]),
                     de=tuple([float(x) for x in rwords[4:7]]),
                     ep=float(rwords[7]),
                     type=rtype,
                     mattfib=matt_fiber,
                     idstr=aline,
                     id=id,
                     mag=mag,
                     extra=subclass)

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
            armB, armR = _assignTargetsToChannel(targets)

            self.setups[setup_name]['channels']['armB']=armB
            self.setups[setup_name]['channels']['armR']=armR
    
    def cassettes_for_setup(self,setup_name):
        return self.cassettes[setup_name]
    
    def cassette_groups_for_setup(self, setup_name):
        return self.cassette_groups[setup_name]

    def getSetupInfo(self, setup):
        '''Returns a list of lines about the setup requested,
        lines are from the .asc file are first, followed by lines 
        from the .res file'''
        setupNfo=self.afile.setups[setup]['setup_nfo_str']
        setupNfo.extend(self.rfile.setups[setup]['setup_nfo_str'])
        return setupNfo

    def available_cassettes(self, hole, setup_name):
        """
        Return cassette(s) name's containing fibers which can be used for hole
        """
        if hole.__hash__()==190951225552046123:
            import pdb;pdb.set_trace()
        #Filter cassettes based on slit width & fiber availability
        available=filter(lambda x: x.slit==hole['SLIT'] and x.n_avail() > 0,
                         self.cassettes[setup_name].values())
        ret=[c.name for c in available]
        return ret

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
    
def _postProcessHJ(plateinfo):
    """ 
    Take the 2 setups for Nov13 Bailey plate and break them into the
    6 real setups
    """
    
    for c in plateinfo.cassettes:
        c.usable=range(2,17,2)
    
    setups=plateinfo.setups
    holes=setups['Setup 1']['pool']
    ppool=[] #primary target pool
    tpool=[] #telluric calibrator target pool
    lpool=[] #lo res target pool
    
    for h in holes:
        subclass=h['EXTRA']
        if 'Telluric' in subclass:
            tpool.append(h)
        elif 'Extra' in subclass:
            lpool.append(h)
        else:
            ppool.append(h)

    return setups


def _postProcessIan(plateinfo):
    """
        Take the 2 setups for Nov13 Bailey plate and break them into the
        6 real setups
        """
    
    for c in plateinfo.cassettes:
        c.usable=[1,8,15] #[1,2,8,9,15,16]
    