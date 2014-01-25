'''
Created on Dec 12, 2009

@author: one
'''
#from Hole import *

import operator
import os.path
from logger import getLogger
from dimensions import PLATE_RADIUS, SH_RADIUS
from readerswriters import _dictlist_to_records, _format_attrib_nicely
from field import load_dotfield
from graphcollide import build_overlap_graph_cartesian
from holesxy import get_plate_holes
from target import Target
from hole import Hole
log=getLogger('plateplanner.foo')


COLOR_SEQUENCE=['red','blue','pink','green','black','teal','purple','orange']

MIN_GUIDES=2
MIN_ACQUISITIONS=3

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
    filename='{}{}.plate'.format(dir, name)

    #get list of crap for the plate
    with open(filename,'w') as fp:
    
        #Write the [Plate] section
        fp.write("[Plate]\n")

        for r in _format_attrib_nicely({'name':name}):
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
            self.plate_holes.append(t)

    def load(self, file):
        """ 
        Routine to a file

        At present only .field files are supported.
        """
        
        if not os.path.isfile(file):
            files=[os.path.join(dirpath, f)
                   for dirpath, dirnames, files in os.walk(file)
                   for f in files if os.path.splitext(f)[1].lower()=='.field']
        else:
            files=[file]

        try:
            for f in files:
                field=load_dotfield(f)
                log.info("Loaded {}")
                if field.name in [f.name for f in self.fields]:
                    log.error("field already loaded")
                else:
                    self.fields.append(field)
        
        except IOError as e:
            log.warn(str(e))

    def clear(self):
        self.fields=[]
        self.selected_fields=[]

    def get_holes(self, holeIDs):
        ret=[]
        for f in self.fields:
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
            if canvas.find_withtag(hashtag):
                log.info("drawing dupe in dark green @ {} IDs: {}".format(
                    pos, str(hash(hole))))
                fcolor='DarkGreen'
            canvas.drawCircle(pos, rad,
                              outline=color, fill=fcolor, tags=('hole',hashtag),
                              activefill='Green', activeoutline='Green',
                              disabledfill='Orange', disabledoutline='Orange')

    def draw(self, canvas, show_conflicts=True):
        
        #Make a circle of appropriate size in the window
        canvas.drawCircle( (0,0) , PLATE_RADIUS)
        canvas.drawCircle( (0,0) , SH_RADIUS)
        
        for i,f in enumerate(self.selected_fields):
            if not f.is_processed:
                f.process()
            
            c=COLOR_SEQUENCE[i%len(COLOR_SEQUENCE)]
            for h in f.holes():
                fcolor=c if h.target.conflicting else 'White'
                if h.target.conflicting !=None:
                    log.warn('{} conflicts with {}'.format(
                                         h.target, h.target.conflicting_ids))
                    if show_conflicts:
                        self._drawHole(h, canvas, color=c, fcolor=fcolor)
                else:
                    self._drawHole(h, canvas, color=c, fcolor=fcolor)
    
    def select_fields(self,field_names):
        ndxs=[i for i,f in enumerate(self.fields) if f.name in field_names]
        self.selected_fields=[self.fields[i] for i in ndxs]
        
        #Determine the conflicts
        targs = [t for f in self.selected_fields
                   for t in f.get_drillable_targets() ]
        holes=([h for t in targs for h in t.holes] +
               [h for t in self.plate_holes for h in t.holes])
        self._determine_conflicts(holes)
    
        #TODO: Verify that enough guides and acquistions can be plugged
        #simultaneously for each field

    def _determine_conflicts(self, holes):

        x=[h.x for h in holes]
        y=[h.y for h in holes]
        d=[h.d for h in holes]
        
        #Nothing can conflict with guides or acquisitions
        coll_graph=build_overlap_graph_cartesian(x,y,d)

        #Take care of Guides & Acquisitions
        keep=[]
        discard=[]
        import ipdb
        #Guides
        for f in self.selected_fields:
            #sort guides according to number of collisions
            #take all with no collisions and as many with collisions needed
            #until have at least two

#onc154 ngc2264_a:gui12
#ngc2264_a:gui10 ONC_a:ali1

#            ipdb.set_trace()
            #get guide hole indicies & number of collisions
            hndxs=[(i,len(coll_graph.collisions(i)))
                   for i in range(len(holes)) if holes[i].target.is_guide and holes[i].target.field==f]
#            ipdb.set_trace()
            #sum up collisions for the holes for each guide
            tmp=[]
            for g in f.guides:
                hole_ndxs=[]
                total_collisions=0
                for i,nc in ((i, nc) for i,nc in hndxs if holes[i] in g.holes):
                    hole_ndxs.append(i)
                    total_collisions+=nc
                tmp.append((hole_ndxs,total_collisions))
#            ipdb.set_trace()
            tmp.sort(key=lambda x: x[1])
            
            #Figure out which guides to keep
            no_coll=[]
            with_coll=[]
            while tmp:
                ndxs, tc=tmp.pop(0)
                if tc:
                    with_coll.append(ndxs)
                else:
                    no_coll.append(ndxs)
#            ipdb.set_trace()
            keep+=no_coll
            
            if len(no_coll) <MIN_GUIDES:
                keep+=with_coll[:MIN_GUIDES-len(keep)]
                discard+=with_coll[MIN_GUIDES-len(keep):]
            else:
                discard+=with_coll
#        ipdb.set_trace()
        #Now Acquisitions
        for f in self.selected_fields:
            #sort acquisitions according to number of collisions
            #take all with no collisions and as many with collisions needed
            #until have at least MIN_ACQUISITIONS

            #get guide hole indicies & number of collisions
            hndxs=[(i,len(coll_graph.collisions(i)))
                   for i in range(len(holes))
                   if holes[i].target.is_acquisition and
                   holes[i].target.field==f]
            
            
            hndxs.sort(key=lambda x: x[1])
            
            #Figure out which guides to keep
            no_coll=[]
            with_coll=[]
            while hndxs:
                ndx, tc=hndxs.pop(0)
                if tc:
                    with_coll.append([ndx])
                else:
                    no_coll.append([ndx])
        
            keep+=no_coll
            
            if len(no_coll) <MIN_ACQUISITIONS:
                keep+=with_coll[:MIN_ACQUISITIONS-len(keep)]
                discard+=with_coll[MIN_ACQUISITIONS-len(keep):]
            else:
                discard+=with_coll
    
        #Update the graph & flag the targets that had conflicts
        for to_drop in discard:
            conflictors=[]
            for ndx in to_drop:
                #If you conflict with one hole in a guide,
                # you conflict with them all
                conflictors+=coll_graph.drop(ndx)
            holes[ndx].target.conflicting=[holes[i].target for i in conflictors]
                
        for to_keep in keep:
            for ndx in to_keep:
                dropped=coll_graph.drop_conflicting_with(ndx)
                discard.append(dropped)
                for d in dropped:
                    holes[d].target.conflicting=holes[ndx]

#        ipdb.set_trace()

        #Now finally dump the processed things from holes
        discard=[i for l in discard+keep for i in l]
        holes=[h for i, h in enumerate(holes) if i not in discard]
        x=[h.x for h in holes]
        y=[h.y for h in holes]
        d=[h.d for h in holes]

        assert len([h for h in holes
                    if h.target.is_guide or h.target.is_acquisition])==0
        
        #Now rebuild the graph deal with science targets
        coll_graph=build_overlap_graph_cartesian(x,y,d,overlap_pct_r_ok=0.9)

    
        #priorityies must first be redistributed onto the same scale
        #must keeps > wants> filler guides and acq should generally have
        # lowest priority
        #
        #Go though collision graph and flag all the targets with issues
        #import ipdb;ipdb.set_trace()
        
        while not coll_graph.is_disconnected:
        
            coll_ndx = coll_graph.get_colliding_node()
            coll_targ=holes[coll_ndx].target
            
            if coll_targ.is_standard:
                #Drop the standard
                conflicts=coll_graph.drop(coll_ndx)
                conflicts=set([holes[i].target for i in conflicts])
                holes[coll_ndx].target.conflicting=conflicts
            elif coll_targ.is_sky or coll_targ.is_target:
                collwith_ndxs=coll_graph.collisions(coll_ndx)
                conflicts=set([holes[i].target for i in collwith_ndxs])
                if coll_targ.priority < max(t.priority for t in conflicts):
                    #Drop the target
                    coll_targ.conflicting=conflicts
                    coll_graph.drop(coll_ndx)
                else:
                    #Drop everything that conflicts with it
                    dropped=coll_graph.drop_conflicting_with(coll_ndx)
                    for i in dropped:
                        holes[i].target.conflicting=holes[coll_ndx].target
            else:
                log.warn('Collision with {}'.format(coll_targ))
                

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

