from platefile import resfile, ascfile
from Hole import Hole

SCALE=14.25

class plateHoleInfo(object):
    '''Frontend to the .res & .asc files of a setup
       used to retrieve information about a given hole'''
    def __init__(self,dir,platename):
        
        #load the res & asc files
        self.rfile=resfile(dir+platename.replace('Sum','plate')+'.res')
        self.afile=ascfile(dir+platename+'.asc')
    
        self.setups={}
        self.holeSet=set()
        
        #Go through all the setups in the files
        for setup_name, setup_dict in self.rfile.setups.items():
            
            #add holes to R side first
            channel='armR'
            
            #make sure setup is in both
            if setup_name not in self.afile.setups.keys():
                raise ValueError('Setup must be in both res & asc files')
            
            #create a setup
            self.setups[setup_name]={'plate':platename,
                'setup':setup_name,
                'unused_holes':[],
                'channels':{'armR':[],'armB':[]},
                'groups':[]}
                
                
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
            armB, armR = assignTargetsToChannel(targets)

            self.setups[setup_name]['channels']['armB']=armB
            self.setups[setup_name]['channels']['armR']=armR
    
            if platename=='HotJupiters_1_Sum':
                self.setups=postProcessHJ(self.setups)
    
    def getSetupInfo(self, setup):
        '''Returns a list of lines about the setup requested,
        lines are from the .asc file are first, followed by lines 
        from the .res file'''
        setupNfo=self.afile.setups[setup]['setup_nfo_str']
        setupNfo.extend(self.rfile.setups[setup]['setup_nfo_str'])
        return setupNfo

def assignTargetsToChannel(targetHoleList):
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
    
def postProcessHJ(setups):
    """ 
    Take the 2 setups for Nov13 Bailey plate and break them into the
    6 real setups
    """
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
    