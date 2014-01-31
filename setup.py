from ConfigParser import RawConfigParser
import os.path
from plate import get_plate
from cassettes import CassetteConfig
from cassettes import CASSETTE_NAMES, RED_CASSETTE_NAMES, BLUE_CASSETTE_NAMES
from pathconf import CONFIGDEF_DIRECTORY, SETUP_DIRECTORY
from readerswriters import _dictlist_to_records, _format_attrib_nicely
from logger import getLogger

log = getLogger('setup')


FILTER_NAMES=['BK7','IanR']
SLIT_NAMES=['180 um','125 um','98 um','75 um','58 um','45 um']
MODE_NAMES_PLIST_NAME_MAP={'hires':'HiRes','lores':'LoRes'}

HIRES_MODE='hires'


REQUIRED_PLUGGED_SECTION_KEYS=['fiber', 'id', 'ra', 'dec', 'epoch', 'type',
                               'priority','pm_ra','pm_dec']


class M2FSConfig(object):
    def __init__(self, side=None, mode=None, slit=None, loel=None,
                 hiaz=None, hiel=None, focus=None,
                 binning=None, filter=None, n_amps=None, speed=None):
        
        self.side=side.upper()
        
        
        self.mode=mode.lower()
        assert self.mode in MODE_NAMES_PLIST_NAME_MAP
        
        self.slit=slit
        assert slit in SLIT_NAMES
        
        self.loel=loel
        
        self.hiaz=hiaz
        self.hiel=hiel
        
        self.focus=focus
        
        self.binning=binning
        self.speed=speed
        self.n_amps=n_amps
        
        self.filter=filter
        assert filter in FILTER_NAMES
    
    @property
    def info(self):
        c=self
        r={'binning_{}'.format(self.side):'{} ({})'.format(c.binning, c.n_amps),
            'filter_{}'.format(self.side):c.filter,
            'focus_{}'.format(self.side):str(c.focus),
            'hiaz_{}'.format(self.side):str(c.hiaz),
            'hiel_{}'.format(self.side):str(c.hiel),
            'loel_{}'.format(self.side):str(c.loel),
            'slide_{}'.format(self.side):MODE_NAMES_PLIST_NAME_MAP[c.mode],
            'slit_{}'.format(self.side):c.slit,
            'speed_{}'.format(self.side):c.speed}
        return r



class Setup(object):
    def __init__(self, setupfile, platename, fieldname,
                 configR, configB, assignwith=None):
        
        ok_fibers_r=configR.pop('tetris_config') #boolean 16 tuple,fibers to use
        ok_fibers_b=configB.pop('tetris_config') #boolean 16 tuple,fibers to use
        self.b=M2FSConfig(side='B',**configB)
        self.r=M2FSConfig(side='R',**configR)
        self.name,_,_=os.path.basename(setupfile).rpartition('.')
        self.plate=get_plate(platename)
        self.field=self.plate.get_field(fieldname)
        self.cassette_config=CassetteConfig(usableR=ok_fibers_r,
                                            usableB=ok_fibers_b)
        if not assignwith:
            self.assign_with=[]
        else:
            self.assign_with=assignwith
            for aw in self.assign_with:
                aw.plate=self.plate
                aw.field=self.plate.get_field(aw.field.name)
                #aw.cassette_config=self.cassette_config
        


    @property
    def uses_r_side(self):
        """ Returns true iff the setup need to use the r side """
        return True

    @property
    def uses_b_side(self):
        """ Returns true iff the setup need to use the B side """
        return True

    @property
    def info(self):
        ret=self.field.info.copy()
    
        addit={'assign_with':', '.join(s.name for s in self.assign_with),
               'plate':self.plate.name}
        
        addit.update(self.r.info)
        addit.update(self.b.info)
    
        for k in addit:
            assert k not in ret

        ret.update(addit)
        
        return ret
    
    @property
    def uses_b_side(self):
        """ returns true iff targets have been assigned to b side"""
        for t in self.field.skys+self.field.targets:
            if t.fiber and t.fiber.color=='b':
                return True
        return False

    @property
    def uses_r_side(self):
        """ returns true iff targets have been assigned to r side"""
        for t in self.field.skys+self.field.targets:
            if t.fiber and t.fiber.color=='r':
                return True
        return False

    def writeplist(self, dir='./'):
        filename='{}_{}.m2fs'.format(self.plate.name,self.name)
        import plistlib
        #TODO: Finish
        c={}
        if self.uses_b_side:
            c.update(self.configB.info)
        if self.uses_r_side:
            c.update(self.configR.info)

        for k in config.keys():
            if config[k]==None or config[k]=='None':
                config.pop(k)
        plistlib.writeplist(config, os.path.join(dir,filename))
        
    def writemap(self, dir='./'):
        """
        [setup]
        field info + setup config info
        [setup:plugged]
        header
        records
        [setup:unplugged]
        header
        records
        """
        filename='{}_{}.fibermap'.format(self.plate.name,self.name)
        import ipdb;ipdb.set_trace()
        with open(os.path.join(dir, filename),'w') as fp:
    
            fp.write("[setup]\n")

            recs=_format_attrib_nicely(self.info)
            for r in recs:
                fp.write(r+'\n')
    
            fp.write("[assignemnts]\n")
            #Create dictlist for all fibers
            #Grab fibers
            def dicter(fiber):
                if not f.target:
                    return {'fiber':fiber.name,'id':'unplugged'}
                elif f.target not in self.field.all_targets:
                    return {'fiber':fiber.name,'id':'unassigned'}
                else:
                    return fiber.target.dictlist
            
            dl=[dicter(f) for f in self.cassette_config.fibers]
            recs=_dictlist_to_records(dl, col_first=REQUIRED_PLUGGED_SECTION_KEYS)
            
            fp.write("[guides]\n")
            
#            target record for each guide/acquisition

            fp.write("[unused]\n")
#            target record for any targets not on plate on unassigned


    def write(self,dir='./'):
        """ Call to write the outputs after calling assign"""
        self.writemap(dir=dir)
        self.writeplist(dir=dir)
        for s in self.assign_with:
            s.writemap(dir=dir)
            s.writeplist(dir=dir)

    def assign(self):
        
        #Field targets and skys do not overlab with any guides
        #or acquisitions in any setups, because such cases were culled when
        #creating the plate
        
        try:
            func=get_custom_usable_cassette_func(self.name)
        except NameError:
            func=usable_cassette
            
        to_assign=func(self, self.assign_with)
        _assign_fibers(self.cassette_config, to_assign)


def usable_cassette(setup, assign_with=None):
    """ 
    This function recieves the setup and any setups which should be
    assigned simultaneously and returns the list of targets for which 
    assignments should be computed, with their
    _preset_usable_cassette_names attribute set to a set of cassette names
    which may be used
    To override this create a .py file with the same name of the setup in the
    same directory as the setup with single? function named usable_cassette
    """
    to_assign=setup.field.skys+setup.field.targets
    
    to_assign_with=[t for s in assign_with
                      for t in s.field.skys+s.field.targets]
    
    if not to_assign_with:
        if len(to_assign) <= setup.cassette_config.n_r_usable:
            #put all on one side by setting
            for t in to_assign:
                t._preset_usable_cassette_names=set(RED_CASSETTE_NAMES)
        elif len(to_assign) <= setup.cassette_config.n_b_usable:
            for t in to_assign:
                t._preset_usable_cassette_names=set(BLUE_CASSETTE_NAMES)
        else:
            for t in setup.field.targets:
                t._preset_usable_cassette_names=set(CASSETTE_NAMES)
            for i, t in enumerate(setup.field.skys):
                if i % 2:
                    t._preset_usable_cassette_names=set(RED_CASSETTE_NAMES)
                else:
                    t._preset_usable_cassette_names=set(BLUE_CASSETTE_NAMES)
    else:
        #Assume we are distributing everything evenly
        to_assign+=to_assign_with
        for t in (t for t in to_assign if t.is_target):
            t._preset_usable_cassette_names=set(CASSETTE_NAMES)
        for i, t in enumerate(t for t in to_assign if t.is_sky):
            if i % 2:
                t._preset_usable_cassette_names=set(RED_CASSETTE_NAMES)
            else:
                t._preset_usable_cassette_names=set(BLUE_CASSETTE_NAMES)

    to_assign=to_assign[:setup.cassette_config.n_b_usable+
                         setup.cassette_config.n_r_usable]
    return to_assign

def _assign_fibers(cassettes, to_assign):
    """
    
    cassettes should be a cassettesconfig 
    
        assign_with may be list of setups to perform assignment with
    if none, assignwith from the setup will be used
    
    
    load holes from file, by default assume all are on same slit and no pattern
    
    break holes into sets based on slit requirements
    
    get cassets for each set of holes based on specification
    compute number of cassets needed for each set based on fiber pattern for
    
    
    for each set of holes assign holes to nearest suitable casset (with free fibers)
    assign holes in order of increasing closeness to suitable, non-full cassets
    compute clossness as sum of distances to relevant casset vertices
    
    Consider swapping after algorithm by computing convex hull for each casset and
    finding interlopers then swapping them
    
    
    #Consider making each hole have a number of targets associated with it
    # the targets would contain the fiber and target info instead of the hole object
    # and the hole could be associated with multiple targets (1 per setup)
    
    All science & sky holes are loaded, holes with file-specifed fibers or
    arm/cassette/fiberno and slit constrains are set
    Cassette slit widths, usable fibers are set. slit widths must be assigned
    beforehand to prevent a sparse configuration from happening e.g. all but 16
    furthest are same slit assign 16 furthest -> no available cassettes for rest
    
    #    Assign holes without channel to r or b channel
    #        get holes without channel
    #        break holes into groups based on required slit
    #        get number of available fibers on each channel, given slit and filter reqs
    #        if all fit on one channel, do it, otherwise divide randomly??

    #Barring preassignment, we would like to distribute sky fibers evenly over
    #cassette groups, where a group is a set of cassettes with same color & slit
    for i,h in enumerate(skys):
        h.assignment.cassette=cassette_groups[i mod len(cassette_groups)]

    for each hole w/o preassigned fiber:
        get cassets available to hole (cassets with correct slit and free fibers)
        compute distance to each cassette vertex & sum for available vertices
    
    sort science holes by distance metric
    
    while there are science holes w/o assigned cassette:
        get first hole
        get cassets available to hole (cassets with correct slit and free fibers)
        assign to nearest available casset
        update cassette availability for each hole (a cassette may have filled)
        recompute distance metric for each hole
        sort remaining holes by distance metric
        
    swap between cassettes as needed
    
    for each cassette
        assign fiber numbers with x coordinate of holes
    """
    

    #Reset all the assignments
    cassettes.reset()
    for t in to_assign:
        t.reset_assignment()
    
    #Grab all skys and objects that don't have assignments
    unassigned_skys=[t for t in to_assign
                     if t.is_sky and not t.is_assigned]
    unassigned_objs=[t for t in to_assign
                     if t.is_target and not t.is_assigned]

    #Grab targets with assignments and configure the cassettes
    assigned=[t for t in to_assign if t.is_assigned]
    for t in assigned:
        print "some were assigned"
        cassettes.assign(t, t.fiber.cassette)

    #All targets must have possible_cassettes_names set

    #While there are holes w/o an assigned cassette (groups don't count)
    while unassigned_skys:
        #Update cassette availability for each hole (a cassette may have filled)
        for t in unassigned_skys:
            #Get cassettes with correct slit and free fibers
            # n.b these are just cassette name strings
            possible_cassettes=[c.name for c in cassettes
                                if t.is_assignable(cassette=c) and
                                c.n_avail >0]
            if not possible_cassettes:
                print 'Could not find a suitable cassette for {}'.format(t)
                import ipdb;ipdb.set_trace()
            #Set the cassettes that are usable for the hole
            #  no_add is true so we keep the distribution of sky fibers
            t.update_possible_cassettes_by_name(possible_cassettes)

        #Get hole furthest from its cassettes and assign to nearest available
        unassigned_skys.sort(key=lambda t: t.plug_priority)
        t=unassigned_skys.pop()
        cassettes.assign(t, t.nearest_usable_cassette)


    #While there are holes w/o an assigned cassette (groups don't count)
    while unassigned_objs:
        
#        for foo in to_assign:
#            if (foo.assigned_cassette and
#                foo not in cassettes.get_cassette(foo.assigned_cassette).targets):
#                import ipdb;ipdb.set_trace()

        #Update cassette availability for each hole (a cassette may have filled)
        for t in unassigned_objs:
            #Get cassettes with correct slit and free fibers
            # n.b these are just cassette name strings
            possible_cassettes=[c.name for c in cassettes
                                if t.is_assignable(cassette=c) and
                                c.n_avail >0]

            if not possible_cassettes:
                print 'Could not find a suitable cassette for {}'.format(t)
                import ipdb;ipdb.set_trace()
            #Set the cassetes that are usable for the hole
            #  no_add is true so we keep the distribution of sky fibers
            t.update_possible_cassettes_by_name(possible_cassettes)


        #Get hole furthest from its cassettes and assign to nearest available
        unassigned_objs.sort(key=lambda t: t.plug_priority)
        t=unassigned_objs.pop()
#        if t.id in ['na196']:
#            import ipdb;ipdb.set_trace()
        cassettes.assign(t, t.nearest_usable_cassette)


    ####All targets have now been assigned to a cassette####

    for t in to_assign:
        if t not in cassettes.get_cassette(t.assigned_cassette).targets:
            import ipdb;ipdb.set_trace()

    #For each cassette assign fiber numbers with x coordinate of holes
    cassettes.map()
    
    for t in to_assign:
        if t not in cassettes.get_cassette(t.assigned_cassette).targets:
            import ipdb;ipdb.set_trace()

    #Compact the assignments (get rid of underutillized cassettes)
    cassettes.condense()

    for t in to_assign:
        if t not in cassettes.get_cassette(t.assigned_cassette).targets:
            import ipdb;ipdb.set_trace()
    
    #Rejigger the fibers
    cassettes.rejigger()

    for t in to_assign:
        if t not in cassettes.get_cassette(t.assigned_cassette).targets:
            import ipdb;ipdb.set_trace()

    #Remap fibers
    cassettes.map(remap=True)


def _config_dict_from_dotsetup_dict(section_dict, side):
    
    get_key= lambda d, key, side : d.get(key+side, d.get(key, None))
    
    conf_name=get_key(section_dict, 'config', side)
    if conf_name:
        return get_config(conf_name, side)

    #Load the config piecemeal
    config={'mode':get_key(section_dict, 'mode',side),
            'binning':get_key(section_dict, 'binning',side),
            'filter':get_key(section_dict, 'filter',side),
            'slit':get_key(section_dict, 'slit',side),
            'tetris_config':get_key(section_dict, 'tetris_config',side),
            'n_amps':get_key(section_dict, 'n_amps',side),
            'speed':get_key(section_dict, 'speed',side)}
    
    try:
        config['focus']=get_key(section_dict, 'focus', side)
    except KeyError:
        pass
    
    if config['mode'].lower()==HIRES_MODE:
        config['hiel']=get_key(section_dict, 'elevation', side)
        config['hiaz']=get_key(section_dict, 'azimuth', side)
    else:
        config['loel']=get_key(section_dict, 'elevation', side)

    config['tetris_config']=tuple(map(lambda x: bool(int(x)),
                                      config['tetris_config'].split(',')))

    return config



def load_dotsetup(filename, load_awith=False):
    """ read in a dotsetup file """
    #Read in the setups
    cp=RawConfigParser()
    cp.optionxform=str
    with open(filename) as fp:
        cp.readfp(fp)
    
    setups=[]
    
    #Parse it all
    for sec in cp.sections():
        section_dict=dict(cp.items(sec))
        
        configB=_config_dict_from_dotsetup_dict(section_dict, 'B')
        configR=_config_dict_from_dotsetup_dict(section_dict, 'R')
        #TODO: Handle case where setup uses only one side
        
        field=section_dict['field']
        plate=section_dict['plate']
        assignwith=[]
        if load_awith:
            setup_names=section_dict.get('assignwith','')
            for name in setup_names.split(','):
                assignwith.append(get_setup(name.strip()))

        setup=Setup(filename, section_dict['plate'], section_dict['field'],
                    configR, configB, assignwith=assignwith)

        setups.append(setup)
    
    return setups[0]



def _load_dotconfigdef(filename):

    #Read file
    try:
        lines=open(filename,'r').readlines()
    except IOError as e:
        raise e

    lines=[l.strip() for l in lines]

    section_dict={}
    for l in (l for l in lines if l and l[0]!='#'):
        k,v=l.split('=')
        assert k.strip() not in section_dict
        section_dict[k.strip()]=v.strip()

    configR=_config_dict_from_dotsetup_dict(section_dict,'R')
    configB=_config_dict_from_dotsetup_dict(section_dict,'B')

    return configR, configB


def get_config(configname, side=None):

    cfile=os.path.join(CONFIGDEF_DIRECTORY,configname)+'.configdef'
    try:
        configR,configB=_load_dotconfigdef(cfile)
        if not side:
            return configR,configB
        elif side.lower()=='r':
            return configR
        elif side.lower()=='b':
            return configB
        else:
            raise ValueError("Invalid side: '{}'".format(side))
    except IOError:
        raise ValueError('Config {} not known'.format(configname))

def get_setup(setupname, load_awith=False):
    """Set alone to false to load any assign with setups"""
    try:
        return load_dotsetup(os.path.join(SETUP_DIRECTORY,setupname)+'.setup',
                             load_awith)
    except IOError:
        raise ValueError('Could not find setup {}'.format(setupname))

def get_custom_usable_cassette_func(setupname):
    """ if file exists file should have a function with the following sig:
    targets_configured_for_assignement=usable_cassette(setup_object, list_of_assign_with_setup_objects)
    """
    try:
        loc=locals()
        globa=globals()
        file=os.path.join(SETUP_DIRECTORY,setupname)+'.py'
        with open(file,'r') as f:
            exec(f.read(), globa, loc) #I'm a very bad person
        log.warning('Using custom usable cassette function: {} '.format(file))
        return loc['usable_cassette']
    except IOError:
        raise NameError()

