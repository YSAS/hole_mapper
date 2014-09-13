from ConfigParser import RawConfigParser
import os.path
from glob import glob
from plate import get_plate
from cassettes import CassetteConfig, DEAD_FIBERS
from cassettes import CASSETTE_NAMES, RED_CASSETTE_NAMES, BLUE_CASSETTE_NAMES
from pathconf import SETUP_DIRECTORY
from readerswriters import _dictlist_to_records, _format_attrib_nicely
from logger import getLogger
from config import get_config
from assign import assign
import hashlib
import fibermap

log = getLogger('setup')



REQUIRED_PLUGGED_SECTION_KEYS=['fiber', 'id', 'ra', 'dec', 'epoch', 'type',
                               'priority','pm_ra','pm_dec','x','y','z','d']
REQUIRED_GUIDE_SECTION_KEYS=['id', 'ra', 'dec', 'epoch', 'type',
                             'priority','pm_ra','pm_dec','x','y','z','d']
REQUIRED_UNUSED_SECTION_KEYS=['id', 'ra', 'dec', 'epoch', 'type',
                              'priority','pm_ra','pm_dec','x','y','z','d']


def load_dotsetup(file):
    #Read in the setup definitions
    cp=RawConfigParser()
    cp.optionxform=str
    with open(file) as fp:
        cp.readfp(fp)
    
    setupdefs=[]

    try:
        for section in cp.sections():
            section_dict=dict(cp.items(section))
            setupdefs.append(SetupDefinition(file, section_dict.pop('plate'),
                                             section_dict.pop('field'),
                                             section_dict.pop('config'),
                                             section_dict.pop('assign_to'),
                                             extra=section_dict))
    except KeyError as e:
        err='File {}: Key {} missing from setup {}'.format(file, e.message,
                                                           section)
        log.error(err)
        raise IOError(err)
    return setupdefs


def _load_setups():
    setupfiles=glob(SETUP_DIRECTORY()+'*.setup')
    files=(f for f in setupfiles
           if os.path.basename(f).lower() != 'example.setup')
    for f in files:
        try:
            _KNOWN_SETUPS.update({s.name:s for s in load_dotsetup(f)})
        except IOError:
            pass

def get_setup(setupname):
    try:
        setup_def=_KNOWN_SETUPS[setupname]
    except KeyError:
        _load_setups()
        if setupname in _KNOWN_SETUPS:
            setup_def=_KNOWN_SETUPS[setupname]
        else:
            raise ValueError('Could not find setup {}'.format(setupname))

    #Create setup from setupdef
    try:
        config=get_config(setup_def.configname)
    except ValueError as e:
        raise e

    try:
        plate=get_plate(setup_def.platename)
    except ValueError as e:
        raise e

    return Setup(setup_def, plate, config)

def get_setup_names_for_plate(platename):
    _load_setups()
    return [name for name, sdef in _KNOWN_SETUPS.items()
            if sdef.platename==platename]

def get_all_setups():
    _load_setups()
    return [get_setup(name) for name in _KNOWN_SETUPS]

class SetupDefinition(object):
    def __init__(self, file, platename, fieldname, configname, assign_to,
                 extra=None):
        self.file=file
        self.platename=platename
        self.fieldname=fieldname
        self.configname=configname
        self.assign_to=assign_to.lower()
        self.assign_given=extra.pop('assign_given','')
        if self.assign_to not in ['single', 'any', 'r','b']:
            raise ValueError('Supported values for assign_to are '
                             'single and any. Fix file {}'.format(self.file))
        self.extra=extra if extra else {}
    
    @property
    def name(self):
        if (self.assign_to!='any' or
            self.assign_given or
            self.extra.get('mustkeep',None)!=None or
            self.extra.get('keepall',False)):
            hashstr=':'+hashlib.sha1(self.assign_to+
                                     self.assign_given+
                                     str(self.extra.get('mustkeep',None))+
                                     str(self.extra.get('keepall',False))).hexdigest()[:6]
        else:
            hashstr=''
        return '{}:{}:{}{}'.format(self.platename, self.fieldname,
                                 self.configname,hashstr)


class Setup(object):
    def __init__(self, setupdef, plate, config):
    
        self.file=setupdef.file
        
        self.name=setupdef.name
        
        self.config=config
        
        self._assigning_to=''

        self.plate=plate
        
        self.setupdef=setupdef

        #Fetch Field from plate
        self.field=self.plate.get_field(setupdef.fieldname)
        
        #Fetch cassettes
        self.cassette_config=CassetteConfig(usable=config)
    
        for t in self.field.all_targets:
            t.setup=self
            try:
                assert t.field==self.field
            except AssertionError:
                import ipdb;ipdb.set_trace()

    @property
    def assign_to(self):
        return self.setupdef.assign_to
    
    @property
    def mustkeep(self):
        """should keep all the highest priority targets"""
        if 'mustkeep' in self.setupdef.extra:
            return self.setupdef.extra['mustkeep']
        return self.field.info.get('mustkeep', False)
    
    @property
    def keepall(self):
        """ don't drop any targets due to conflicts with other setups"""
        return self.setupdef.extra.get('keepall', False)

    def reset(self):
        self.config=get_config(self.config.name)
        for t in self.field.skys+self.field.targets:
            t.reset_assignment()
        self.cassette_config=CassetteConfig(usable=self.config)
    
    def set_assigning_to(self,red=False, blue=False, both=False):
        if sum([red, blue, both])!=1:
            raise ValueError('One and only one of red, blue, '
                             'or both must be True')
        if both and self.assign_to=='single':
            raise ValueError('Definition specifies single assignment')
        if red:
            self._assigning_to='r'
        elif blue:
            self._assigning_to='b'
        else:
            self._assigning_to='both'
    
    @property
    def assigning_to(self):
        if self._assigning_to=='b':
            return 'b'
        elif self._assigning_to=='r':
            return 'r'
        elif self._assigning_to:
            return 'both'
        raise RuntimeError('Must call set_assigning_to first')

    @property
    def minsky(self):
        return int(self.field.info.get('minsky',0))

    @property
    def info(self):
        ret=self.field.info.copy()
        ret['field']=ret.pop('name')
        ret['fieldfile']=ret.pop('file')
        if self.setupdef.assign_given:
            ret['assign_given']= self.setupdef.assign_given
        ret['mustkeep']=self.mustkeep
#        import ipdb;ipdb.set_trace()
        addit={'assign_with':', '.join(s.name for s in self.assign_with),
               'plate':self.plate.name, 'config':self.config.name,
               'name':self.name}
        
        for k in addit:
            assert k not in ret

        ret.update(addit)
        
        return ret
    
    @property
    def assign_with(self):
        return self._assign_with
    
    def set_assign_with(self, setups):
        """inform setup of other setups used while assigning"""
        try:
            setups=set(setups)
        except TypeError:
            setups=set([setups])
        try:
            setups.remove(self)
        except KeyError:
            pass
        self._assign_with=tuple(setups)
    
    @property
    def to_assign(self):
        """
        Return a list of skys and targets which should be assigned for this
        setup. Includes all skys. Exludes targets from assign_given setups
        
        """
        get_map=self.setupdef.assign_given
        previously=[]
        while get_map:
            log.info('Excluding previously assigned from {}'.format(
                      get_map))
            fm=fibermap.get_fibermap_for_setup(get_map)
            previously+=fm.mapping.values()
            get_map=fm.dict.get('assign_given','')
        
        targs=[t for t in self.field.targets if t.id not in previously]
        return self.field.skys+targs
    
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
    
    @property
    def n_usable_fibers(self):
        """number of fibers usable when instrument configured for this setup
        respects assign_to
        """
        if self.assign_to =='r':
            return self.cassette_config.n_r_usable
        elif self.assign_to=='b':
            return self.cassette_config.n_b_usable
        elif self.assign_to=='single':
            return max(self.cassette_config.n_r_usable,
                       self.cassette_config.n_b_usable)
        else:
            return (self.cassette_config.n_r_usable +
                    self.cassette_config.n_b_usable)

    @property
    def n_needed_fibers(self):
        """number of fibers desired by the setup's field"""
        return len(self.field.skys)+len(self.field.targets)

    def writemap(self, dir='./'):
        """
        [setup]
        field & config info
        [assignments]
        header
        records
        [guides]
        header
        records
        [unused]
        header
        records
        """
        filename=os.path.join(dir, '{}.fibermap'.format(self.name)).replace(':','-')
        with open(filename,'w') as fp:
    
            fp.write("[setup]\n")

            d=self.info
            import datetime
            d['mapdate']=str(datetime.datetime.now())
            d['deadfibers']=', '.join(DEAD_FIBERS())
            d['nused']='{}'.format(self.cassette_config.n_used)
            for r in _format_attrib_nicely(d):
                fp.write(r)
    
            #Fibers assigned and unassigned
            fp.write("[assignments]\n")

            def dicter(fiber):
                """ convert a fiber assignment into a dictlist record """
                if not fiber.target:
                    return {'fiber':fiber.name,
                            'id':'unplugged',
                            'type':'I'}
                elif fiber.target not in self.field.all_targets:
                    if (fiber.target.field.ra==self.field.ra and
                        fiber.target.field.dec==self.field.dec):
                        return fiber.target.dict
                    else:
                        import ipdb;ipdb.set_trace()
                        return {'fiber':fiber.name,
                                'id':'unassigned',
                                'type':'U'}
                else:
                    return fiber.target.dict

            #Grab fibers
            dl=[dicter(f) for f in self.cassette_config.fibers]
            recs=_dictlist_to_records(dl,
                                      col_first=REQUIRED_PLUGGED_SECTION_KEYS)
            for r in recs:
                fp.write(r)
    
            #Write guides and acquisitions
            fp.write("[guides]\n")
            dl=[t.dict for t in self.field.guides+self.field.acquisitions]
            recs=_dictlist_to_records(dl, col_first=REQUIRED_GUIDE_SECTION_KEYS)
            for r in recs:
                fp.write(r)

            #All the other targets
            fp.write("[unused]\n")
            dl=[t.dict for t in self.field.skys+self.field.targets
                if not t.fiber]
            recs=_dictlist_to_records(dl, col_first=REQUIRED_UNUSED_SECTION_KEYS)
            for r in recs:
                fp.write(r)
            #TODO: target record for any targets not on plate on unassigned

    def write(self,dir='./'):
        """ Call to write the outputs after calling assign"""
        self.writemap(dir=dir)
        filename=os.path.join(dir,self.name+'.m2fs').replace(':','-')
        self.config.write_plist(filename)
    
#        for s in self.assign_with:
#            s.writemap(dir=dir)
#            s.writeplist(dir=dir)








_KNOWN_SETUPS={}
_load_setups()



