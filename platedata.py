""""
goals

low memory, prompt, interface to the functionality of the functions below,
motivated by other programs.

For plugController:
    fibermap.get_platenames_for_known_fibermaps()
    fibermap.get_fibermap_names_for_plate(plate_name)
    fibermap.get_fibermap_for_setup(setup_name)

For targetWeb
    get_metadata_by_file
    get_all_plate_names

"""

#import hashlib
#
#def hash_bytestr_iter(bytesiter, hasher, ashexstr=False):
#    for block in bytesiter:
#        hasher.update(block)
#    return (hasher.hexdigest() if ashexstr else hasher.digest())
#
#def file_as_blockiter(afile, blocksize=65536):
#    with afile:
#        block = afile.read(blocksize)
#        while len(block) > 0:
#            yield block
#            block = afile.read(blocksize)


import logger, plate, fibermap
import os
import cPickle as pickle

_log=logger.getLogger('platedata')
_file_mtimes={}
_plate_metadata_cache={}
_fibermap_metadata_cache={}

class FibermapMetadata(object):
    def __init__(self, fibermap):
        self.name=fibermap.name
        self.file=fibermap.file
        self.sha1=fibermap.sha1
        self.platename=fibermap.platename

class TargetMetadata(object):
    def __init__(self, name, ra, dec, pm_ra, pm_dec, epoch, *args, **kwargs):
        self.ra=ra
        self.dec=dec
        self.pm_ra=pm_ra
        self.pm_dec=pm_dec
        self.epoch=epoch
        self.name=name

    @property
    def id(self):
        return self.name

class StandardMetadata(TargetMetadata):
    pass

class FieldMetadata(TargetMetadata):
    def __init__(self, *args, **kwargs):
        super(FieldMetadata, self).__init__(*args, **kwargs)
        standards=args[-1]
        self.standards=[StandardMetadata(t.id, t.ra, t.dec,
                                         t.pm_ra, t.pm_dec, t.epoch)
                        for t in standards]

class PlateMetadata(object):
    def __init__(self, plate):
        """
        give a full plate (or a plate loaded with the metadata flag set
        extracts metadata
        """
        self.name=plate.name
        self.sha1=plate.sha1
        self.fields=[FieldMetadata(f.name, f.ra, f.dec, f.pm_ra, f.pm_dec,
                                   f.epoch, f.standards)
                     for f in plate.fields]


def _update_fibermap_metadata_cache():
    """
    build/maintain a cache of the info in the .fibermap files
    only load files whose file sys mod time differes from the last call
    """
    global _fibermap_metadata_cache, _file_mtimes
    
    #Get list of all fibermap files
    files=fibermap.fibermap_files()
    
    #Go through list and load any that have been modified
    cache_dirty=False
    for f in files:
        mtime=os.stat(f).st_mtime
        if mtime!=_file_mtimes.get(f,None):
            _log.info('Refreshing metadata for {}'.format(f))
            try:
                fm=fibermap.load_dotfibermap(f, usecache=False,
                                             metadata_only=True)
                _fibermap_metadata_cache[f]=FibermapMetadata(fm)
                del fm
                cache_dirty=True
                _file_mtimes[f]=mtime
            except (IOError, fibermap.FibermapError) as e:
                _log.warn('Skipped {} due to {}'.format(f,str(e)))



def _update_plate_metadata_cache(cachefile=None):
    """
    build/maintain a cache of the info in the platefiles
    only load files whose file sys mod time differes from the last call
    """
    global _plate_metadata_cache, _file_mtimes
    
    #Get list of all platefiles
    platefile=plate.get_all_plate_filenames()
    
    if _plate_metadata_cache is None and cachefile is not None:
        try:
            with open(cachefile,'r') as f:
                cache,mtimes = pickle.load(f)
            _plate_metadata_cache = cache
            _file_mtimes = mtimes
        except Exception:
            _log.warning('Unable to load plate metadata cache file {}'.format(cachefile))
    
    #Go through list and load any that have been modified
    cache_dirty=False
    for f in platefile:
        mtime=os.stat(f).st_mtime
        if mtime!=_file_mtimes.get(f,None):
#        if _plate_metadata_cache.get(f, None) is None:
            _log.info('Refreshing metadata for {}'.format(f))
            p=plate.load_dotplate(f, usecache=False, metadata_only=True)
            _plate_metadata_cache[f]=PlateMetadata(p)
            del p
            cache_dirty=True
            _file_mtimes[f]=mtime

    if cache_dirty and cachefile is not None:
        try:
            with open(cachefile,'w') as f:
                pickle.dump((_plate_metadata_cache, _file_mtimes), f, protocol=2)
        except Exception as e:
            _log.warning('Unable to save plate metadata cache')

def get_all_plate_names(cachefile=None):
    """ 
    return a list of all known plate names
    refreshes the platemetadata cache
    
    interface consumes significantly less memory than that in plate.py
    """
    _update_plate_metadata_cache(cachefile=cachefile)
    names=[p.name for p in _plate_metadata_cache.values()]
    names.sort(key = lambda x:x.lower())
    return names

def get_metadata(platenameOrList, cachefile=None):
    """
    platenameOrList - a plate name or list of plate names
    
    returns none if plate not found
    
    returns list of results if given a list
    
    return object that has .name, & .fields.
    .fields is indexable iterable with objects with
        .name, .ra, .dec, .pm_ra, .pm_dec, .epoch,, & .standards
        
    .standards is and indexable iteralble with .id .ra .dec,
        .pm_ra, .pm_dec, .epoch,
        
    refreshes the platemetadata cache

    """
    _update_plate_metadata_cache(cachefile=cachefile)
    if type(platenameOrList) in (list,tuple):
        ret=[]
        for platename in platenameOrList:
            try:
                ret.append([p for p in _plate_metadata_cache.values()
                        if p.name==platename][0])
            except IndexError as e:
                ret.append(None)
    
        return ret
    else:
        platename=platenameOrList
        try:
            return [p for p in _plate_metadata_cache.values()
                    if p.name==platename][0]
        except IndexError:
            return None

def get_metadata_by_file(file):
    """
    file - a plate file name including path 
    
    returns none if plate not found
    
    return object that has .name, & .fields.
    .fields is indexable iterable with objects with
        .name, .ra, .dec, .pm_ra, .pm_dec, .epoch,, & .standards
        
    .standards is and indexable iteralble with .id .ra .dec,
        .pm_ra, .pm_dec, .epoch,
        
    refreshes the platemetadata cache
    """
    _update_plate_metadata_cache()
    try:
        return _plate_metadata_cache[file]
    except KeyError:
        return None

def get_platenames_for_known_fibermaps():
    """
    same as in fibermap.py but much more memory effecient
    """
    _update_fibermap_metadata_cache()
    fmnames=[fmd.platename for fmd in _fibermap_metadata_cache.values()]
    return list(set(fmnames))

def get_fibermap_names_for_plate(platename):
    """
    same as in fibermap.py but much more memory effecient
    """
    _update_fibermap_metadata_cache()
    fmnames=[fmd.name for fmd in _fibermap_metadata_cache.values()
             if fmd.platename==platename]
    ret=list(set(fmnames))
    if len(fmnames) != len(fmnames):
        _log.warning('Duplicate fibermap names found. Check files.')
    return ret

def get_fibermap_for_setup(setup_name):
    """
    same as in fibermap.py but much more memory effecient
    """
    try:
        fmfile=[fmd.file for fmd in _fibermap_metadata_cache.values()
                if fmd.name==setup_name][0]
    except IndexError:
        raise ValueError()
    return fibermap.load_dotfibermap(fmfile, usecache=False)



#import hole_mapper.pathconf
#hole_mapper.pathconf.ROOT='/Users/one/Desktop/platestemp/'
#import hole_mapper.platedata
#import hole_mapper.plate
#pd=hole_mapper.platedata
#pf=hole_mapper.plate.get_all_plate_filenames()
#pd._update_plate_metadata_cache()
#sys.getsizeof(pd._plate_metadata_cache)
#for f in pf: hole_mapper.plate.load_dotplate(f)
#sys.getsizeof(hole_mapper.plate._PLATE_CACHE)
