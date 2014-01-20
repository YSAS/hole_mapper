
DEFAULT_FOCUS=280.0

FILTER_NAMES=['BK7']
SLIT_NAMES=['180 um','125 um','98 um','75 um','58 um','45 um']
MODE_NAMES=['HiRes','LoRes']
HIRES_MODE='hires'

def get_config_by_name(config_name, side):
    """ Return the configuration dictionary from the list of known configs"""
    #TODO: Write the config manager
    ...


def _config_dict_from_dotsetup_dict(section_dict, side):
    def get_key(d,key, side):
        try:
            return d[k+side]
        except KeyError:
            return d[key]
    try:
        return get_config_by_name(get_key(section_dict, 'config', side),
                                  side)
    except KeyError:
        pass
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
    
    if config['mode'].lower()=HIRES_MODE:
        config['hiel']=get_key(section_dict, 'elevation', side)
        config['hiaz']=get_key(section_dict, 'azimuth', side)
    else:
        config['loel']=get_key(section_dict, 'elevation', side)

    config['tetris_config']=tuple(map(lambda x: bool(int(x)),
                                      config['tetris_config'].split(',')))

    return config


def read_dotsetup(filename):
    """ read in a dotsetup file """
    #Read in the setups
    cp=RawConfigParser
    cp.optionxform=str
    with open(filename) as fp:
        cp.read(fp)
    
    setups=[]

    #Parse it all
    for sec in cp.sections():
        section_dict=dict(cp.items(sec))
        
        configB=_config_dict_from_dotsetup_dict(section_dict, 'B')
        configR=_config_dict_from_dotsetup_dict(section_dict, 'R')
        #TODO: Handle case where setup uses only one side
        
        configB=SetupConfig(**configB)
        configR=SetupConfig(**configR)
        field=section_dict['field']
        asignwith=map(lambda x: x.strip(),
                      section_dict.get('assignwith','').split(','))
        
        setup=Setup(platename, fieldname, configR, configB, assignwith)
        
        setups.append(setup)
    
    return setups

class SetupConfig(object):
    def __init__(self, mode=None, slit=None, loel=None,
                 hiaz=None, hiel=None, focus=None,
                 binning=None, filter=None, n_amps=None, speed=None,
                 tetris_config=(True,)*8):
    
        self.mode=mode
        assert self.mode in MODE_NAMES
        
        self.slits=slits
        assert len(slits)=8
        for s in slits:
            assert s in SLIT_NAMES

        self.loel=loel

        self.hiaz=hiaz
        self.hiel=hiel

        self.focus=focus

        self.binning=binning
        self.speed=speed
        self.n_amps=n_amps

        self.filter=filter
        assert filter in FILTER_NAMES
        
        assert len(tetris_config)==8
        self.tetris_config=tetris_config


class Setup(object):
    def __init__(self, platename, fieldname, configR, configB, assignwith):
        self.b=configB
        selb.r=configR
        self.plate=Plate(platename)
        self.field=self.plate.fields[fieldname]
        self.assign_with=[] #setup names, setups?
    
        #list of disjoint lists of cassette names all
        # sharing the same color and slit
        self.cassette_groups=[[]]
        
        self.cassette_config=None

    def writeplist(self, filename):
        import plistlib
        #TODO: Finish
        {'binning_{}'.format(side):'{} ({})'.format(c.binning, c.n_amps)
        
        'filter_{}'.format(side):c.filter
        'focus_{}'.format(side):str(c.focus)
        'hiaz_{}'.format(side):str(c.hiaz)
        'hiel_{}'.format(side):str(c.hiel)
        'loel_{}'.format(side):str(c.loel)
        'slide_{}'.format(side): #LoRes or HiRes
        'slit_{}'.format(side):c.slit #180 um, 125 um, 95 um, 75 um, 58 um, 45 um
        'speed_{}'.format(side):c.speed} #Slow, Fast, Turbo
        
        for k in config.keys():
            if config[k]==None:
                config.pop(k)
        
        plistlib.writeplist(config, filename)

    @property
    def cassettes(self):
        """ Returns the CassetteConfig for the setup """
        #TODO: Write
        ...

    @property
    def fibers_requested(self):
        """ return the number of fibers needed to fully assign the field """
        #TODO: Write
        return len(self.field.targets)+len(self.field.skys)

    @property
    def fibers_usable(self):
        """ return the number of fibers which may be assigned with this config """
        #TODO: Write
        return 0


