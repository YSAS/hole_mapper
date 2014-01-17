'''
Created on Dec 12, 2009

@author: one
'''
#from Hole import *

import operator
import os.path
from logger import getLogger
from dimensions import PLATE_RADIUS, SH_RADIUS
from field import load_dotfield
from graphcollide import build_overlap_graph_cartesian


log=getLogger('plateplanner.foo')


COLOR_SEQUENCE=['red','blue','pink','green','black','teal','purple','orange']

MIN_GUIDES=2
MIN_ACQUISITIONS=3


#deltara=np.rad2deg*arccos(cos(180*np.deg2rad/3600)*sec(dec)**2 - tan(dec)**2)

class Manager(object):
    """ Class for I don't know what yet"""
    def __init__(self):
        self.fields=[]
        self.selected_fields=[]
        log.info('Started Manager')
        self.plate_holes=[]

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
        rad=hole.r*radmult
        
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

    def draw(self, canvas):
        
        #Make a circle of appropriate size in the window
        canvas.drawCircle( (0,0) , PLATE_RADIUS)
        canvas.drawCircle( (0,0) , SH_RADIUS)
        
        for i,f in enumerate(self.selected_fields):
            if not f.isProcessed():
                f.process()
            
            c=COLOR_SEQUENCE[i%len(COLOR_SEQUENCE)]
            for h in f.holes():
                if h.target.conflicting !=None:
                    log.warn('{} conflicts with {}'.format(
                                         h.target, h.target.conflicting_ids))
                fcolor=c if h.target.conflicting else 'White'
                self._drawHole(h, canvas, color=c, fcolor=fcolor)

    def select_fields(self,field_names):
        ndxs=[i for i,f in enumerate(self.fields) if f.name in field_names]
        self.selected_fields=[self.fields[i] for i in ndxs]
        self._determine_conflicts()

    def _determine_conflicts(self):
        platetargs = [t for f in self.selected_fields
                        for t in f.get_drillable_targets() ]
        holes=[h for t in platetargs for h in t.holes()]+self.plate_holes
        x=[h.x for h in holes]
        y=[h.y for h in holes]
        r=[h.r for h in holes]
        coll_graph=build_overlap_graph_cartesian(x,y,r,overlap_pct_r_ok=0.9)

    
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
            elif coll_targ.is_guide:
                if len(coll_targ.field.usable_guides)>MIN_GUIDES:
                    #Drop the guide
                    conflicts=coll_graph.drop(coll_ndx)
                    conflicts=set([holes[i].target for i in conflicts])
                    holes[coll_ndx].target.conflicting=conflicts
                else:
                    #Drop everything that conflicts with the guide
                    dropped=coll_graph.drop_conflicting_with(coll_ndx)
                    for i in dropped:
                        holes[i].target.conflicting=holes[coll_ndx].target
            elif coll_targ.is_acquisition:
                if (len(coll_targ.field.usable_acquisitions)>MIN_ACQUISITIONS):
                    #Drop the acquisition
                    conflicts=coll_graph.drop(coll_ndx)
                    conflicts=set([holes[i].target for i in conflicts])
                    holes[coll_ndx].target.conflicting=conflicts
                else:
                    #Drop everything that conflicts with the acquistion
                    dropped=coll_graph.drop_conflicting_with(coll_ndx)
                    for i in dropped:
                        holes[i].target.conflicting=holes[coll_ndx].target
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
        import write_dotplate
        write_dotplate.write(name, self.plate_holes, self.selected_fields)

