import plistlib
import os.path
from glob import glob
from pathconf import CONFIGDEF_DIRECTORY
from copy import deepcopy


KNOWN_SLITS=['180','125','95','75','58','45']
KNOWN_FILTERS=['BK7', 'Mgb_O69',' CalRT_O41','HotJupiter','Mgb_Rev2', 'IanR',
              'Halpha_Li', 'IanR_O77_80','Mgb-Rev2','CaT-OneOrder',
              'BStar_O80_87', 'BulgeGC_1','Mgb_FourOrders','RRLyr_1','JS_dSph']

def _load_configs():
    setupfiles=glob(CONFIGDEF_DIRECTORY()+'*.configdef')
    for f in setupfiles:
        cfg=load_dotconfigdef(f)
        _KNOWN_CONFIGS[cfg.name]=cfg


def load_dotconfigdef(filename):

    #Read file
    with open(filename,'r') as fp:
        lines=[l.strip() for l in fp.readlines()]
    try:
        section_dict={}
        for l in (l for l in lines if l and l[0]!='#'):
            k,v=l.split('=')
            assert k.strip() not in section_dict
            assert v.strip()
            section_dict[k.strip()]=v.strip()

        name=os.path.basename(filename)[:-10]
        kwords=_config_dict_from_dotsetup_dict(section_dict,'R')
        configR=M2FSArmConfig('R', **kwords)
        kwords=_config_dict_from_dotsetup_dict(section_dict,'B')
        configB=M2FSArmConfig('B', **kwords)
    except (ValueError, AssertionError) as e:
        raise ValueError('Bad config {}: {}'.format(filename,str(e)+l))

    return M2FSConfig(name, configR, configB)


def get_config(configname):
    try:
        ret=_KNOWN_CONFIGS[configname]
    except KeyError:
        _load_configs()
        if configname in _KNOWN_CONFIGS:
            ret=_KNOWN_CONFIGS[configname]
        else:
            raise ValueError('Could not find config {}'.format(configname))

    return deepcopy(ret)

def _config_dict_from_dotsetup_dict(section_dict, side):
    
    get_key= lambda d, key, side : d.get(key+side, d.get(key, None))
    
    
    def get_active_fibers_key(d, n, side):
        return d.get('active_fibers{}{}'.format(n,side),
                     d.get('active_fibers{}'.format(n),
                           d.get('active_fibers{}'.format(side),
                                 d.get('active_fibers', None))))
    
    conf_name=get_key(section_dict, 'config', side)
    if conf_name:
        return get_config(conf_name, side)

    #Load the config piecemeal
    config={'mode':get_key(section_dict, 'mode',side),
            'binning':get_key(section_dict, 'binning',side),
            'filter':get_key(section_dict, 'filter',side),
            'slit':get_key(section_dict, 'slit',side),
            'active_fibers1':get_active_fibers_key(section_dict,1,side),
            'active_fibers2':get_active_fibers_key(section_dict,2,side),
            'active_fibers3':get_active_fibers_key(section_dict,3,side),
            'active_fibers4':get_active_fibers_key(section_dict,4,side),
            'active_fibers5':get_active_fibers_key(section_dict,5,side),
            'active_fibers6':get_active_fibers_key(section_dict,6,side),
            'active_fibers7':get_active_fibers_key(section_dict,7,side),
            'active_fibers8':get_active_fibers_key(section_dict,8,side),
            'n_amps':get_key(section_dict, 'n_amps',side),
            'speed':get_key(section_dict, 'speed',side)}
    
    if config['mode'].lower()=='hires':
        config['hiel']=get_key(section_dict, 'hiel', side)
        config['hiaz']=get_key(section_dict, 'azimuth', side)
    else:
        config['loel']=get_key(section_dict, 'loel', side)

    config['active_fibers1']=tuple(map(lambda x: bool(int(x)),
                                       config['active_fibers1'].split(',')))
    config['active_fibers2']=tuple(map(lambda x: bool(int(x)),
                                       config['active_fibers2'].split(',')))
    config['active_fibers3']=tuple(map(lambda x: bool(int(x)),
                                       config['active_fibers3'].split(',')))
    config['active_fibers4']=tuple(map(lambda x: bool(int(x)),
                                       config['active_fibers4'].split(',')))
    config['active_fibers5']=tuple(map(lambda x: bool(int(x)),
                                       config['active_fibers5'].split(',')))
    config['active_fibers6']=tuple(map(lambda x: bool(int(x)),
                                       config['active_fibers6'].split(',')))
    config['active_fibers7']=tuple(map(lambda x: bool(int(x)),
                                       config['active_fibers7'].split(',')))
    config['active_fibers8']=tuple(map(lambda x: bool(int(x)),
                                       config['active_fibers8'].split(',')))

    return config

class M2FSConfig(object):
    def __init__(self, name, r, b):
        self.name=name
        self.r=r
        self.b=b

    def write_plist(self, filename):
        c={}
        if self.b: c.update(self.b.plist_dict)
        if self.r: c.update(self.r.plist_dict)
        plistlib.writePlist(c, filename)


class M2FSArmConfig(object):
    def __init__(self, side, mode=None, slit=None, loel=None,
                 hiaz=None, hiel=None, active_fibers1=None,
                 active_fibers2=None,
                 active_fibers3=None,
                 active_fibers4=None,
                 active_fibers5=None,
                 active_fibers6=None,
                 active_fibers7=None,
                 active_fibers8=None,
                 binning=None, filter=None, n_amps=None, speed=None):
        
        self.side=side.upper()
        
        self.mode=mode.lower()
        if self.mode not in ['hires', 'lores']:
            raise ValueError('Bad mode')
        
        self.slit=slit
        if slit not in KNOWN_SLITS:
            raise ValueError('Bad slit')
        
        self.loel=loel
        
        self.hiaz=hiaz
        self.hiel=hiel
        
        self.binning=binning
        self.speed=speed
        self.n_amps=n_amps
        
        self.active_fibers={1:tuple(map(bool,active_fibers1)),
                            2:tuple(map(bool,active_fibers2)),
                            3:tuple(map(bool,active_fibers3)),
                            4:tuple(map(bool,active_fibers4)),
                            5:tuple(map(bool,active_fibers5)),
                            6:tuple(map(bool,active_fibers6)),
                            7:tuple(map(bool,active_fibers7)),
                            8:tuple(map(bool,active_fibers8))}

        lowerfilt=[f.lower() for f in KNOWN_FILTERS]
        try:
            ndx=lowerfilt.index(filter.lower())
        except ValueError:
            raise ValueError('Congrats on your purchase of the '
                             '{} filter. '.format(filter)+
                             'Please add it to KNOWN_FILTERS in config.py')
        self.filter=KNOWN_FILTERS[ndx]

    
    @property
    def plist_dict(self):
        c=self
        r={'binning_{}'.format(self.side):'{} ({})'.format(c.binning, c.n_amps),
           'filter_{}'.format(self.side):c.filter,
           'hiaz_{}'.format(self.side):str(c.hiaz),
           'hiel_{}'.format(self.side):str(c.hiel),
           'loel_{}'.format(self.side):str(c.loel),
           'slide_{}'.format(self.side):'HiRes' if c.mode=='hires' else 'LoRes',
           'slit_{}'.format(self.side):'{} um'.format(c.slit),
           'speed_{}'.format(self.side):c.speed}
        return r


_KNOWN_CONFIGS={}
_load_configs()

