from collections import defaultdict
import os
from astropy.time import Time
from jbastro.astroLib import sexconvert
from datetime import datetime
import holesxy
from logger import getLogger
from hole import Hole
from target import Target,ConflictDummy
from target import GUIDEREF_TYPE, GUIDE_TYPE, ACQUISITION_TYPE, SH_TYPE
from graphcollide import build_overlap_graph_cartesian
from dimensions import PLATE_TARGET_RADIUS_LIMIT
from readerswriters import _parse_header_row, _parse_record_row, _dictlist_to_records
from errors import ConstraintError
import numpy as np
import re

REQUIRED_FIELD_KEYS=['ra', 'dec', 'epoch', 'id', 'type', 'priority']
FIELD_KEYS=REQUIRED_FIELD_KEYS+['pm_ra','pm_dec']
REQUIRED_FIELD_RECORD_ENTRIES=['ra', 'dec', 'epoch', 'type']

log=getLogger('plateplanner.field')

class FieldCatalog(object):
    def __init__(self, file='', name='', obsdate=None,
                 sh=None, user=None, guides=None, targets=None,
                 acquisitions=None, skys=None, standards=None):
        """sh should be a target"""
        
        self.file=file
        self.field_name=name
        self._obsdate=obsdate
        self.sh=sh if sh else Target(type='C')
        self.user=user if user else {}
        self.guides=guides if guides else []
        self.targets=targets if targets else []
        self.acquisitions=acquisitions if acquisitions else []
        self.skys=skys if skys else []
        self.standards=standards if standards else []
        
        self.holesxy_info=None
        self.keep_all=False
        self._processed=False
    
    @property
    def obsdate(self):
        return self._obsdate
    
    @obsdate.setter
    def obsdate(self, value):
        self._processed=False
        self._obsdate=value
    
    @property
    def name(self):
        if self.field_name:
            return self.field_name
        else:
            return self.sh.id

    def ra(self):
        print 'Not correcting field ra with PM'
        return self.sh.ra

    def dec(self):
        print 'Not correcting field dec with PM'
        return self.sh.dec

    def add_target(self,targ):
        if targ.is_sky:
            self.skys.append(targ)
        elif targ.is_target:
            self.targets.append(targ)
        elif targ.is_guide:
            self.guides.append(targ)
        elif targ.is_acquisition:
            self.acquisitions.append(targ)
        elif targ.is_standard:
            self.standards.append(targ)
        elif targ.is_sh:
            self.sh=targ
        else:
            raise ValueError('Target {} of unknown type'.format(targ))

        targ.field=self

    def process(self):
        """
        Process the targets in the field to find their update xyz positions
        """
        obs_date=self.obsdate
        
        targs=self.guides+self.targets+self.acquisitions+self.skys
        ras=[t.ra.float for t in targs]
        decs=[t.dec.float for t in targs]
        
        pmra=[t.pm_ra for t in targs]
        pmdec=[t.pm_dec for t in targs]
        

        #compute  time delta for each tar
        obtime=Time(self.obsdate,scale='utc')
        delta=[obtime-Time('J{}'.format(t.epoch) if t.epoch!=1950 else
                           'B{}'.format(t.epoch), scale='utc') for t in targs]
        
        for i in range(len(targs)):
            conversion=delta[i].value/365.0/3600.0
            ras[i]+=pmra[i]*conversion
            decs[i]+=pmdec[i]*conversion
        
        
        #Correct sh pm
        shdelta=obtime-Time('J{}'.format(t.epoch) if self.sh.epoch!=1950 else
                            'B{}'.format(t.epoch), scale='utc')
        field_ra=self.sh.ra.float+self.sh.pm_ra*shdelta.value/365.0/3600.0
        field_dec=self.sh.dec.float+self.sh.pm_dec*shdelta.value/365.0/3600.0
        
        epochs=[t.epoch for t in targs]
        targ_types=[t.type for t in targs]
        
        guide_ndxs=[i for i,t in enumerate(targ_types) if t=='G']
        
        pos, guideref, info=holesxy.compute_hole_positions(field_ra,
                                field_dec, self.sh.epoch, self.obsdate,
                                ras, decs, epochs, targ_types)
        
        #Store the info
        for i,t in enumerate(targs):
            t.hole=Hole(pos.x[i],pos.y[i],pos.z[i],pos.d[i],t)
        
        for i,ndx in enumerate(guide_ndxs):
            holes=[Hole(guideref.x[3*i+j], guideref.y[3*i+j],
                        guideref.z[3*i+j], guideref.d[3*i+j], targs[ndx])
                   for j in range(3)]
            targs[ndx].additional_holes=holes


        self.holesxy_info=info

        self._processed=True

    def get_info_dict(self):
        """ return a dictionary of field information """

        sh_dict=self.sh.info
        sh_dict.pop('field', None)
        sh_dict.pop('type', None)
        sh_dict.pop('dec', None)
        sh_dict.pop('ra', None)
        sh_dict.pop('priority', None)
        sh_rec=_dictlist_to_records([sh_dict],
                                    ['id','epoch','pm_ra','pm_dec'])

        ret={'name':self.name,
             'file':self.file,
             'obsdate':str(self.obsdate),
             '(ra, dec)':'{} {}'.format(self.sh.ra.sexstr,self.sh.dec.sexstr),
             '(az, el)':'{:3f} {:3f}'.format(self.holesxy_info.az,
                                             self.holesxy_info.el),
             '(ha, st)':'{:3f} {:3f}'.format(self.holesxy_info.ha,
                                             self.holesxy_info.st),
             'airmass':'{:2f}'.format(self.holesxy_info.airmass),
             'sh_hdr':sh_rec[0][:-1], #remove the /n
             'sh_rec':sh_rec[1][:-1]}

        for k,v in self.user.iteritems():
            if k in ret:
                ret['user_'+k]=str(v)
            else:
                ret[k]=str(v)
        return ret

    def reset(self):
        self._drillable_targets=None
        for t in self.all_targets:
            t.conflicting=None

    def get_drillable_targets(self):
        """
        Return all targets (S,T,G,A) in the catalog that can be drilled
        parial overlaps between S-T, S-S, & T-T allowed
        """
        try:
            if not self._drillable_targets:
                raise AttributeError
            return self._drillable_targets
        except AttributeError:
            pass
        
        if not self._processed:
            self.process()
        
        
        #Get data needed for collision graph
        holes=[t.hole for t in self.all_targets]+[self.sh.hole]
        x=[h.x for h in holes]
        y=[h.y for h in holes]
        
        #First exclude anything not actually on the plate
        exclude,=np.where(np.array(x)**2+np.array(y)**2 >
                          PLATE_TARGET_RADIUS_LIMIT**2)
        
        for i in exclude:
            holes[i].target.conflicting=ConflictDummy(id='offplate')

        holes=[h for h in holes if not h.target.conflicting]
        x=[h.x for h in holes]
        y=[h.y for h in holes]
        d=[h.conflict_d for h in holes]


        #Per Mario:
        #No overlap with guides/acquisitions/sh
        coll_graph=build_overlap_graph_cartesian(x,y,d, overlap_pct_r_ok=0.0)
        #Drop everything conflicting with the sh, guides or acquisitions
        ndxs=[i for i, h in enumerate(holes) if h.target.type in
              [GUIDE_TYPE, ACQUISITION_TYPE, SH_TYPE]]
              
        to_drop=[]
        for n in ndxs:
            dropped=coll_graph.drop_conflicting_with(n)
            to_drop+=dropped
            for i in dropped:
                holes[i].target.conflicting=holes[n].target
        
        #Remove Sahck-Hartman from further consideration
        to_drop+=[len(holes)-1]

        holes=[h for i,h in enumerate(holes) if i not in to_drop]
        x=[h.x for h in holes]
        y=[h.y for h in holes]
        d=[h.conflict_d for h in holes]
        pri=[h.target.priority for h in holes]

        #Now do it again but allowing some overlap
        coll_graph=build_overlap_graph_cartesian(x, y, d, overlap_pct_r_ok=-0.05)


        keep, drop=coll_graph.crappy_min_vertex_cover_cut(weights=pri,
                                                          retdrop=True)
        
        #Now go through and figure out which targets are(not) usable
        drillable=[holes[i].target for i in keep]
        undrillable=[holes[i].target for i in drop]
        
        #determine cause of conflict
        for d, t in zip(drop, undrillable):
            t.conflicting=[holes[i].target for i in coll_graph.collisions(d)]

        assert len(set(drillable))==len(drillable)

        #undrillable=set(undrillable)
    
        self._drillable_targets=drillable

        return self._drillable_targets
    
    @property
    def is_processed(self):
        return self._processed

    @property
    def usable_guides(self):
        return [g for g in self.guides if not g.conflicting]

    @property
    def usable_acquisitions(self):
        return [g for g in self.acquisitions if not g.conflicting]

    @property
    def all_targets(self):
        return (self.skys+self.targets+self.guides+self.acquisitions)

    def holes(self):
        """ return a list of all the holes the field would like on a plate """
        try:
            return [hole for t in self.all_targets for hole in t.holes]
        except AttributeError:
            log.warning('field.holes() called before processing')
            return []

    def drillable_dictlist(self):
        ret=[]
        for t in (t for t in self.all_targets
                  if not t.conflicting and t.on_plate):
            d=t.hole.info
            d.pop('field','')
            ret.append(d)
            if t.type==GUIDE_TYPE:
                #Change type code for guide refs
                for h in t.additional_holes:
                    d=h.info
                    d.pop('field','')
                    d['type']=GUIDEREF_TYPE
                    ret.append(d)
        return ret

    @property
    def n_conflicts(self):
        return len([t.info for t in self.skys+self.targets if t.conflicting])

    def undrillable_dictlist(self, flat=False):
        ret=[t.info for t in self.all_targets
             if t.conflicting or not t.on_plate]
        map(lambda x: x.pop('field',''), ret)
        return ret

    def standards_dictlist(self):
        return [t.info for t in self.standards]


def load_dotfield(file):
    """
    returns FieldCatalog() or raises error if file has issues.
    """
    
    field_cat=FieldCatalog(file=os.path.basename(file))

    try:
        lines=open(file,'r').readlines()
    except IOError as e:
        raise e

    #Clean up the lines
    lines=[l.strip() for l in lines]

    have_name=False


    #Go through all lines with soemthing in them
    for l in (l for l in lines if l):
    
        #Skip comments
        if l[0] =='#':
            continue
        elif l[0] not in '+-0123456789' and not l.lower().startswith('ra'):
        
            try:
                k,_,v=l.partition('=')
                k=k.strip().lower()
                if k=='field':
                    k='name'
                v=v.strip()
                assert v != ''
            except Exception as e:
                raise IOError('Failed on line '
                        '{}: {}\n  Bad key=value formatting:{}'.format(
                        lines.index(l), l ,str(e)))

            if k=='obsdate':
                field_cat.obsdate=datetime(*map(int,re.split('\W+', v)))
            elif k=='name':
                field_cat.field_name=v
            elif k=='keep_all':
                field_cat.keep_all=True if v.lower()!='false' else False
            else:
                field_cat.user[k]=v
                
        elif l.lower().startswith('ra'):
            try:
                keys=_parse_header_row(l.lower(), REQUIRED=REQUIRED_FIELD_KEYS)
                user_keys=[k for k in keys if k not in FIELD_KEYS]
            except Exception as e:
                raise IOError('Failed on line {}: {}\n  {}'.format(
                               lines.index(l), l ,str(e)))
        else:
            try:
                rec=_parse_record_row(l, keys, user_keys,
                                      REQUIRED=REQUIRED_FIELD_RECORD_ENTRIES)
                field_cat.add_target(Target(**rec))
            except Exception as e:
                raise IOError('Failed on line {}: {}\n  {}'.format(
                               lines.index(l), l ,str(e)))

    return field_cat


class Field(object):
    def __init__(self, field_info=None, drilled=None, undrilled=None,
                 standards=None):
        """
        drilled, undrilled, & standards should be lists of target
        """

        self.info=field_info #Dict, see keys returned by fieldcatalog.info
        self.name=field_info['name']
        self.undrilled=undrilled
        self.standards=standards

        guides=[g for g in drilled if g.type in [GUIDE_TYPE, GUIDEREF_TYPE] ]
        for id in set(g.id for g in guides):
            refs=[g for g in guides if g.id==id and g.type==GUIDEREF_TYPE]
            guide=[g for g in guides if g.id==id and g.type==GUIDE_TYPE][0]
            for r in refs:
                guides.remove(r)
            guide.additional_holes=[r.hole for r in refs]

        self.guides=guides
            
        self.targets=[g for g in drilled if g.is_target]
        self.acquisitions=[g for g in drilled if g.is_acquisition]
        self.skys=[g for g in drilled if g.is_sky]

    @property
    def ra(self):
        return self.info['(ra, dec)'].split()[0]
    
    @property
    def dec(self):
        return self.info['(ra, dec)'].split()[1]
    
    @property
    def epoch(self):
        return 2000.0
    
    @property
    def pm_ra(self):
        return 0.0
    
    @property
    def pm_dec(self):
        return 0.0
    
    @property
    def all_targets(self):
        return (self.skys+self.targets+self.guides+self.acquisitions)

    @property
    def holes(self):
        """ return a list of all the holes the field has on the plate """
        return [hole for t in self.all_targets for hole in t.holes]

