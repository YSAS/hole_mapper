import operator
import os.path
from logger import getLogger
from dimensions import PLATE_RADIUS, SH_RADIUS, DRILLABLE_PCT_R_OVERLAP_OK
from readerswriters import _dictlist_to_records, _format_attrib_nicely
from field import load_dotfield
from graphcollide import build_overlap_graph_cartesian
from holesxy import get_plate_holes
from target import Target,ConflictDummy
from hole import Hole
import tkMessageBox
from errors import ConstraintError
log=getLogger('plateplanner.foo')
from settings import MIN_GUIDES, MIN_ACQUISITIONS

COLOR_SEQUENCE=['red','blue','purple','green','black','teal','pink','orange']



PLATEHOLE_REQUIRED_COLS=['id','type','x','y','z','d']
UNDRILLABLE_REQUIRED_COLS=['id','ra','dec','epoch','pm_ra','pm_dec','priority',
                           'type', 'conflicts']
STANDARDS_REQUIRED_COLS=['id','ra','dec','epoch','priority','pm_ra','pm_dec',
                         'type']
DRILLABLE_REQUIRED_COLS=['id','ra','dec','epoch','pm_ra','pm_dec', 'priority',
                         'type', 'x','y', 'z','d']
DRILLFILE_REQUIRED_COLS=['x','y','z','d','type','id']


#deltara=np.rad2deg*arccos(cos(180*np.deg2rad/3600)*sec(dec)**2 - tan(dec)**2)

def write_dotplate(name, plate_holes, fields, dir='./'):
    filename=os.path.join(dir,'{}.plate'.format(name))

#    if os.path.exists(filename):
#        raise IOError('File exists')

    #get list of crap for the plate
    with open(filename,'w') as fp:
    
        #Write the [Plate] section
        fp.write("[Plate]\n")

        for r in _format_attrib_nicely({'name':name,
                       'fields':', '.join([f.name for f in fields])}):
            fp.write(r)

        #Write out mechanical holes
        fp.write("[PlateHoles]\n")
        recs=_dictlist_to_records(plate_holes, PLATEHOLE_REQUIRED_COLS)
        for r in recs:
            fp.write(r)
        
        #Write out the fields
        for i,f in enumerate(fields):

            #Write out field info section
            fp.write("[Field{}]\n".format(i))
            
            #Write out the field attributes
            for r in _format_attrib_nicely(f.get_info_dict()):
                fp.write(r)
            
            #Write out holes not drilled on the plate
            fp.write("[Field{}:Undrilled]\n".format(i))
            recs=_dictlist_to_records(f.undrillable_dictlist(),
                                      UNDRILLABLE_REQUIRED_COLS)
            for r in recs:
                fp.write(r)

            #Write out holes drilled on the plate
            fp.write("[Field{}:Drilled]\n".format(i))
            recs=_dictlist_to_records(f.drillable_dictlist(),
                                      DRILLABLE_REQUIRED_COLS)
            for r in recs:
                fp.write(r)

            #Write out standard stars
            fp.write("[Field{}:Standards]\n".format(i))
            recs=_dictlist_to_records(f.standards_dictlist(),
                                      STANDARDS_REQUIRED_COLS)
            for r in recs:
                fp.write(r)


def write_drill(name, plate_holes, fields, dir='./'):
    """ Write drill files for vince """
    file_fmt_str='{}{}_All_Holes_{}.txt'
    
    dicts=[d for f in fields for d in f.drillable_dictlist()]+plate_holes
    diams=set(d['d'] for d in dicts)
    
    for diam in diams:
        dicts_for_file=[d for d in dicts if d['d']==diam]
        
        #warn if duplicate holes only unique holes to file
        hole_tuples=[]
        dicts_for_file_filtered=[]
        for d in dicts_for_file:
            ht=(d['x'],d['y'],d['z'],d['d'])
            try:
                ndx=hole_tuples.index(ht)
                print 'Hole for {} {} already written for {}'.format(d['type'],d['id'],dicts_for_file[ndx]['id'])
            except ValueError:
                dicts_for_file_filtered.append(d)
            hole_tuples.append(ht)
        dicts_for_file=dicts_for_file_filtered
        
        with open(file_fmt_str.format(dir, name, diam),'w') as fp:

            recs=_dictlist_to_records(dicts_for_file, DRILLFILE_REQUIRED_COLS,
                                      required_only=True)
            for r in recs[1:]:
                fp.write(r)



class Manager(object):
    """ Class for I don't know what yet"""
    def __init__(self):
        self.fields=[]
        self.selected_fields=[]
        log.info('Started Manager')
        self.plate_holes=[]
        mech=get_plate_holes()
        for i in range(len(mech.x)):
            t=Target(type=mech.type[i])
            t.hole=Hole(mech.x[i],mech.y[i],mech.z[i],mech.d[i],t)
            if t.is_standard:
                t.id='STANDARD'
            self.plate_holes.append(t)

    def load(self, file):
        """ 
        load .field file(s)
        """
        if not os.path.isfile(file):
            files=[os.path.join(dirpath, f)
                   for dirpath, dirnames, files in os.walk(file)
                   for f in files if os.path.splitext(f)[1].lower()=='.field']
        else:
            files=[file]

        try:
            for f in files:
                if f in [x.full_file for x in self.fields]:
                    log.info("Skipping {}. Already loaded".format(f))
                    continue
                
                field=load_dotfield(f)
                if [x for x in self.fields if
                    x.name==field.name
                    and x.full_file!=field.full_file]:
                    exist=[x for x in self.fields if x.name==field.name][0]
                    log.error("Duplicate field names found")
                    tkMessageBox.showerror('Duplicate field name',
                                           '{} & {}'.format(os.path.basename(f),
                                           os.path.basename(exist.file)))
                else:
                    log.info("Loaded {}".format(field.name))
                    self.fields.append(field)
        
        except IOError as e:
            log.warn(str(e))

    def get_field(self, name):
        try:
            return [f for f in self.fields if f.name == name][0]
        except IndexError:
            return None

    def reset(self):
        for t in self.plate_holes: t.conflicting=None
        for f in self.fields: f.reset()

    def clear(self):
        self.fields=[]
        self.selected_fields=[]

    def get_holes(self, holeIDs):
        ret=[]
        for f in self.selected_fields:
            for h in f.holes():
                if str(hash(h)) in holeIDs:
                    ret.append(h)
        return ret

    def _drawHole(self, hole, canvas, color=None, fcolor='White', radmult=1.0):
        
        drawimage=False
        
        pos=hole.x,hole.y
        rad=hole.d*radmult/2.0
        
        hashtag="."+str(hash(hole))
        
        if drawimage:
            canvas.drawCircle(pos, rad, outline=color, fill=fcolor)
        else:
#            if canvas.find_withtag(hashtag):
#                log.info("drawing dupe in dark green @ {} IDs: {}".format(
#                    pos, str(hash(hole))))
#                fcolor='DarkGreen'
            canvas.drawCircle(pos, rad,
                              outline=color, fill=fcolor, tags=('hole',hashtag),
                              activefill='Green', activeoutline='Green',
                              disabledfill='Orange', disabledoutline='Orange')

    def draw(self, canvas, show_conflicts=True):
        
        #Make a circle of appropriate size in the window
        canvas.drawCircle( (0,0) , PLATE_RADIUS)
        canvas.drawCircle( (0,0) , SH_RADIUS)
        
        #Draw Plate holes
        for t in self.plate_holes:
            if show_conflicts and t.conflicting:
                self._drawHole(t.hole, canvas, color='black', fcolor='black')
            elif not t.conflicting:
                self._drawHole(t.hole, canvas, color='black')
    
        #Draw fields
        for i,f in enumerate(self.selected_fields):
            if not f.is_processed: f.process()
            
            c=COLOR_SEQUENCE[i%len(COLOR_SEQUENCE)]
            for h in f.holes():
                fcolor=c if h.target.conflicting else 'White'
                if h.target.conflicting !=None:
#                    log.warn('{} conflicts with {}'.format(
#                                         h.target, h.target.conflicting_ids))
                    if show_conflicts:
                        self._drawHole(h, canvas, color=c, fcolor=fcolor)
                else:
                    self._drawHole(h, canvas, color=c, fcolor=fcolor)
    
    def select_fields(self, field_names):
        old=set([f.name for f in self.selected_fields])

        self.reset()
        ndxs=[i for i,f in enumerate(self.fields) if f.name in field_names]
        self.selected_fields=[self.fields[i] for i in ndxs]
        
        #Get all the holes that might go on the plate
        targs = [t for f in self.selected_fields
                   for t in f.get_drillable_targets() ]
        holes=[t.hole for t in targs] + [t.hole for t in self.plate_holes]
        

        #Determine the conflicts
        self._determine_conflicts(holes)
    
        #go through and make sure all the mutkeep targets were kept all the
        #fields have atleast minsky
        # were lost due to minsky
        # if some were lost due to minsky then constrainterror

        for f in self.selected_fields:
            if f.n_drillable_skys<f.minsky:
                raise ConstraintError("A feud between undroppable targets and "
                                      "the minsky={} precludes these "
                                      "fields from coexisting.".format(f.minsky))
            if f.n_mustkeep_conflicts:
                raise ConstraintError("A feud between undroppable targets "
                                      "precludes these fields from coexisting.")

            if f.n_drillable_acquisitions<MIN_ACQUISITIONS:
                err='{} has only {} drillable acquisitons in this combination.'
                err=err.format(f.field_name, f.n_drillable_acquisitions)
                log.warning(err)
#                raise ConstraintError(err)
            if f.n_drillable_guides<MIN_GUIDES:
                err='{} has only {} drillable guides in this combination.'
                err=err.format(f.field_name, f.n_drillable_guides)
                log.warning(err)
#                raise ConstraintError(err)
            report='Field {}: {:2} Guides {:2} Acq {:4} Targets {:4} Skys'
            report=report.format(f.field_name, f.n_drillable_guides,
                                 f.n_drillable_acquisitions,
                                 f.n_drillable_targs,
                                 f.n_drillable_skys)
            log.info(report)

        #Set excess skys as conflicting
        for f in self.selected_fields:
            #grab non-conflicting skys
            skys=[s for s in f.skys if not s.conflicting]
            if len(skys) <= f.maxsky:
                continue
            
            #group by priority
            from itertools import groupby
            skys.sort(key=lambda x:x.priority, reverse=True)
            sky_groups=[list(g) for k,g in groupby(skys,lambda x:x.priority)]
          
            #take min(n_in_priority, maxsky) randomly from priority groups
            # in order of decreasing priority until maxsky  obtained.
            keep=[]
            import random
            random.seed(0)
            for sg in sky_groups:
                if len(keep) < f.maxsky:
                    keep.extend(random.sample(sg,
                                              min(len(sg), f.maxsky-len(keep))))
                else:
                    break
            
            #for skys left set a conflict dummy
            for t in (t for t in skys if t not in keep):
                t.conflicting=ConflictDummy(id='maxsky')



    def _determine_conflicts(self, holes):
        """
        determines conflits within the set of holes accounting for 
        interfield issues
        """
        ALLOW_PERFECT=True
        
        x=[h.x for h in holes]
        y=[h.y for h in holes]
        d=[h.conflict_d for h in holes]
        
        #Nothing can conflict with guides or acquisitions
        coll_graph=build_overlap_graph_cartesian(x,y,d,
                                                 allow_perfect=ALLOW_PERFECT)

        #Take care of Guides & Acquisitions
        to_keep=[]
        discard=[]
        
        #Guides
        #this only decides to keep or drop guides in each field, it does not
        # go through and decide what to do about conflicts
        # after this code we could well have decided to keep guide a
        # in field A and and guide b in field B and have a & b be fundamentally
        # incompatible. this is handled later
        for f in self.selected_fields:
            #sort guides according to number of collisions
            #take all with no collisions and as many with collisions needed
            #until have at least min required
            # do not take any that conflict with something that can't be dropped

            #get guide hole indicies & number of collisions
            hndxs=[(i,len(coll_graph.collisions(i)))
                   for i,h in enumerate(holes)
                   if h.target.is_guide and h.target.field==f]

            #Sort by number of conflicts
            hndxs.sort(key=lambda x: x[1])
            
            #Figure out which guides to keep
            no_coll=[]#[i for i,ncoll in hndxs if not ncoll]
            with_coll=[]#[i for i,ncoll in hndxs if ncoll]
            while hndxs:
                ndx, ncoll=hndxs.pop(0)
                if ncoll: with_coll.append(ndx)
                else: no_coll.append(ndx)
            
            #Keep all those without collisions
            keep=no_coll
            
            #Keep those with collisions if don't have enough
            if len(keep) < min(MIN_GUIDES, len(f.guides)):
                #Keep min guides, we can't keep the guide if it conflicts
                # with a target in a field with mustkeep set
                while with_coll:
                    i=with_coll.pop(0)
                    #See if we must drop the guide
                    drop_guide=False
                    for j in coll_graph.collisions(i):
                        drop_guide|=holes[j].target.must_be_drilled
                        if drop_guide: break
                    #Deal with the outcome
                    if drop_guide:
                        discard.append(i)
                    else:
                        keep.append(i)
                        if len(keep) >=MIN_GUIDES:
                            discard+=with_coll
                            break
            else:
                discard+=with_coll
            
            if len(keep) < min(MIN_GUIDES, len(f.guides)):
                raise ConstraintError("Can't keep enough guides for {} due to collisions with undroppable targets".format(f.name))
    
            #Keep the guides from the field
            to_keep+=keep

        foo_guides=[h.target for h in holes if h.target.is_guide]
        foo_processed=[holes[i].target for i in to_keep+discard]
        
        assert len(set(foo_guides))==len(foo_guides)
        assert len(set(foo_processed))==len(foo_processed)
        
        assert len(foo_processed)==len(foo_guides)
        for t in foo_processed:
            assert t in foo_guides
        
        
        #I guess technically I should update the graph here
        # a guide that was dropped (because it interfered with some other guide)
        #may have also interfered with an acquisituon
        
        #Acquisitions
        for f in self.selected_fields:
            #sort acquisitions according to number of collisions
            #take all with no collisions and as many with collisions needed
            #until have at least MIN_ACQUISITIONS

            #get guide hole indicies & number of collisions
            hndxs=[(i,len(coll_graph.collisions(i)))
                   for i,h in enumerate(holes)
                   if h.target.is_acquisition and h.target.field==f]
            
            
            hndxs.sort(key=lambda x: x[1])
            
            #Figure out which guides to keep
            no_coll=[]
            with_coll=[]
            while hndxs:
                ndx, ncoll=hndxs.pop(0)
                if ncoll: with_coll.append(ndx)
                else: no_coll.append(ndx)
        
            #Keep acquisitions without collisions
            keep=no_coll
            
            if len(keep) < MIN_ACQUISITIONS:
                #Keep min acquisitions, we can't keep them if it conflicts
                # with a target in a field with mustkeep set
                while with_coll:
                    i=with_coll.pop(0)
                    #See if we must drop it
                    drop=False
                    for j in coll_graph.collisions(i):
                        drop|=holes[j].target.must_be_drilled
                        if drop: break
                    #Deal with the outcome
                    if drop:
                        discard.append(i)
                    else:
                        keep.append(i)
                        if len(keep) >= MIN_ACQUISITIONS:
                            discard+=with_coll
                            break
            else:
                discard+=with_coll
                            
            if len(keep) < min(MIN_ACQUISITIONS, len(f.acquisitions)):
                import ipdb;ipdb.set_trace()
                raise ConstraintError("Can't keep enough acquisitions for {} due to collisions with undroppable targets".format(f.name))
            
            #Keep the guides from the field
            to_keep+=keep
    
        for ndx in to_keep:
            if ndx in discard:
                import ipdb;ipdb.set_trace()
    
        #Update the graph & flag the targets that had conflicts
        for ndx in discard:
            conflictors=coll_graph.drop(ndx)
            holes[ndx].target.conflicting=[holes[i].target for i in conflictors]
                
        for ndx in to_keep:
            dropped=coll_graph.drop_conflicting_with(ndx)
            discard.extend(dropped)
            for d in dropped:
                holes[d].target.conflicting=holes[ndx].target

        ######################

        #Now repeat the process using only sky and targets
        holes=[h for i, h in enumerate(holes) if i not in discard+to_keep]
        x=[h.x for h in holes]
        y=[h.y for h in holes]
        d=[h.conflict_d for h in holes]

        #Make certain there are no guides or acquisitions in holes under
        # consideration
        assert len([h for h in holes
                    if h.target.is_guide or h.target.is_acquisition])==0
        
        #Rebuild the graph allowing partial overlap
        coll_graph=build_overlap_graph_cartesian(x, y, d, overlap_pct_r_ok=
                                                 DRILLABLE_PCT_R_OVERLAP_OK,
                                                 allow_perfect=ALLOW_PERFECT)


        #Redistribute priorities onto the same scale
        #must keeps (highest priority in a field) > wants > filler
        
        #Grab only the skys and targets
        pri_holes=[h for h in holes if h.target.is_sky or h.target.is_target]
        for h in (h for h in holes if h.target.is_standard):
            #standards are filler
            h.target.fm_priority=0

        #Create a new attribute to store the computed priority
        for h in pri_holes: h.target.fm_priority=None
        
        #must keeps (max pri if mustkeep set) get fm_pri=1e9
        #filler (min pri if filler_targ set and min pri !=max pri) get fm_pri=1
        
        #For each of the fields for which there is a sky or target
        for f in list(set(h.target.field for h in pri_holes)):
            #for each of the holes which belong to that field
            for h in (x for x in holes if x.target.field==f):
                if h.target.must_be_drilled:
                    h.target.fm_priority=1e9
                if (h.target.field.filler_targ and
                    f.max_priority!=f.min_priority and
                    h.target.priority==f.min_priority):
                    h.target.fm_priority=1
    
        #Assign all non mustkeep skys as filler, we will respect minsky later
        filler_sky=[h for h in pri_holes
                    if h.target.fm_priority is None and h.target.is_sky]
        for h in filler_sky: h.target.fm_priority=1
        
        #all the targets left neither must keep nor filler
        need_fm_pri=[h.target for h in pri_holes
                     if h.target.fm_priority is None]
        
        #break need_fm_pri into groups by field
        from itertools import groupby
        grouping_iter=groupby(sorted(need_fm_pri, key=lambda x:x.field),
                              lambda x:x.field)
        field_fm_pri_group=[list(g) for k,g in grouping_iter]
        
        #sort each group by priority
        for x in field_fm_pri_group: x.sort(key=lambda x:x.priority)

        next_priority=sum(len(x) for x in field_fm_pri_group)+10
        pri_group=0
        while sum(len(x) for x in field_fm_pri_group)>0:
            #cycle through groups taking highest pri target
            t=field_fm_pri_group[pri_group].pop()
            t.fm_priority=next_priority
            next_priority-=1

            #Remove empty groups
            if len(field_fm_pri_group[pri_group])==0:
                field_fm_pri_group.pop(pri_group)
                pri_group-=1

            #Determine the next group to sample
            pri_group=0 if pri_group>=len(field_fm_pri_group)-1 else pri_group+1
        
        #Go though collision graph and flag all the targets with issues

        #rank each sky by -sum of weights of things it interferes with
        # to penalize skys that interfere with things the most
        #this is acually the exact opposite of what you want need to get rid of
        #the negative. see note at l588
        sky_pri=[-sum([holes[i].target.fm_priority for i in
                      coll_graph.collisions(holes.index(s))])
                 for s in filler_sky]
        for s,p in zip(filler_sky,sky_pri): s.target.fm_priority=p
        
        
        while not coll_graph.is_disconnected: #Edges are holes too close together

            #need to go through the collisions lowest priority first with minsky
            # because drop choice is no longer local to a conflict group
            # could have dropped a bunch of skys elsewhere then get a sky
            # interfereing with a mustkeep that we could have otherwise dropped.
            coll_ndxs=coll_graph.get_colliding_nodes()
            coll_ndxs.sort(key=lambda x: holes[x].target.fm_priority)
            coll_ndx=coll_ndxs[0]

            coll_targ=holes[coll_ndx].target
            
            if coll_targ.is_standard: #Drop the standard star hole
                conflicts=coll_graph.drop(coll_ndx)
                conflicts=[holes[i].target for i in conflicts]
                holes[coll_ndx].target.conflicting=conflicts
            elif coll_targ.is_sky or coll_targ.is_target:
                #Get conflicting holes
                collwith_ndxs=coll_graph.collisions(coll_ndx)
                conflicts=set([holes[i].target for i in collwith_ndxs])
                #use fm_priority not priority, also the <= is critical here
                if ((coll_targ.fm_priority <=
                     max(t.fm_priority for t in conflicts)) and
                    ((not coll_targ.is_sky) or
                     coll_targ.field.n_drillable_skys>coll_targ.field.minsky)):
                    #is this thing less important that the most important thing
                    # it interferes with and it is not a sky or minsky is met
                    #otherwise we take the other branch greedily takeing the sky
                    #We are going through low fm_priority to high so the first
                    #test should always be met, but this implies that the most
                    #desirable skys should have the lowest fm_priority, which is
                    # both backwards and not what is presently coded
                    
                    #Drop the target
                    coll_targ.conflicting=conflicts
                    coll_graph.drop(coll_ndx)
                else:
                    #Drop everything that conflicts with it
                    #this is the rare branch
                    dropped=coll_graph.drop_conflicting_with(coll_ndx)
                    for i in dropped:
                        holes[i].target.conflicting=holes[coll_ndx].target
            else:
                raise Exception(' impossible collision')
#                log.warn('Collision with {}'.format(coll_targ))

        #Warn if no standard holes left
        ok_stds=[h for h in holes
                 if h.target.is_standard and not h.target.conflicting]
        if len(ok_stds)<4:
            if len(ok_stds)>0:
                log.info('Lost {}'.format(4-len(ok_stds))+
                         ' standard holes to collsions')
            else:
                log.warning('Lost all standard holes to collsions')

    def plate_drillable_dictlist(self):
        ret=[]
        for t in (t for t in self.plate_holes if not t.conflicting):
            d={'id':t.id,'type':t.type}
            d.update(t.hole.holeinfo)
            ret.append(d)
        return ret

    def save_selected_as_plate(self, name):
        """
        Write out a .plate file with the selected fields
        
        plate=name
        key=value
        [Field1]
        key=value
        [Field1:Drilled]
        header
        targets
        [Field1:Undrilled]
        header
        targets
        ....
        """
        ph=self.plate_drillable_dictlist()
        write_dotplate(name, ph, self.selected_fields)
        write_drill(name, ph, self.selected_fields)

