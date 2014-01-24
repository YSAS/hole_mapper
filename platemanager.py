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
from holesxy import get_plate_holes
from target import Target
from hole import Hole
log=getLogger('plateplanner.foo')


COLOR_SEQUENCE=['red','blue','pink','green','black','teal','purple','orange']

MIN_GUIDES=2
MIN_ACQUISITIONS=3


#deltara=np.rad2deg*arccos(cos(180*np.deg2rad/3600)*sec(dec)**2 - tan(dec)**2)

class Manager(object):
    """ Class for I don't know what yet"""
    def __init__(self):
        self.plate=None
#        self.fields=[]
#        self.selected_fields=[]
        log.info('Started Manager')
#        self.plate_holes=[]
#        mech=get_plate_holes()
#        for i in range(len(mech.x)):
#            t=Target(type=mech.type[i])
#            t.hole=Hole(mech.x[i],mech.y[i],mech.z[i],mech.d[i],t)
#            self.plate_holes.append(t)

    def load(self, file):
        """ 
        Routine to a file

        At present only .setup files are supported.
        """
        try:
            self.setups=load_dotsetup(file)
            log.info("Loaded {}")
        except IOError as e:
            log.warn(str(e))

    def clear(self):
        for s in self.setups:
            setup.reset()

    def get_holes(self, holeIDs):
        ret=[]
        for setup in self.setups:
            for f in setup.field:
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

    def draw(self, canvas):
        
        #Make a circle of appropriate size in the window
        canvas.drawCircle( (0,0) , PLATE_RADIUS)
        canvas.drawCircle( (0,0) , SH_RADIUS)
        
        for i,f in enumerate(self.selected_setup):

            c=COLOR_SEQUENCE[i%len(COLOR_SEQUENCE)]
            for h in f.holes():
                if h.target.conflicting !=None:
                    log.warn('{} conflicts with {}'.format(
                                         h.target, h.target.conflicting_ids))
                fcolor=c if h.target.conflicting else 'White'
                self._drawHole(h, canvas, color=c, fcolor=fcolor)

    def select_setup(self, name):
        self.selected_setup=[s for s in self.setups if s.name == name][0]
        self.selected_setup.assign()

#    def select_fields(self,field_names):
#        ndxs=[i for i,f in enumerate(self.fields) if f.name in field_names]
#        self.selected_fields=[self.fields[i] for i in ndxs]
#        self._determine_conflicts()

#    def _determine_conflicts(self):
#        targs = [t for f in self.selected_fields
#                        for t in f.get_drillable_targets() ]
#        holes=([h for t in targs for h in t.holes()]+
#               [h for t in self.plate_holes for h in t.holes()])
#        x=[h.x for h in holes]
#        y=[h.y for h in holes]
#        d=[h.d for h in holes]
#        coll_graph=build_overlap_graph_cartesian(x,y,d,overlap_pct_r_ok=0.9)
#
#    
#        #priorityies must first be redistributed onto the same scale
#        #must keeps > wants> filler guides and acq should generally have
#        # lowest priority
#        #
#        #Go though collision graph and flag all the targets with issues
#        #import ipdb;ipdb.set_trace()
#        
#        while not coll_graph.is_disconnected:
#        
#            coll_ndx = coll_graph.get_colliding_node()
#            
#            coll_targ=holes[coll_ndx].target
#            
#            if coll_targ.is_standard:
#                #Drop the standard
#                conflicts=coll_graph.drop(coll_ndx)
#                conflicts=set([holes[i].target for i in conflicts])
#                holes[coll_ndx].target.conflicting=conflicts
#            elif coll_targ.is_guide:
#                if len(coll_targ.field.usable_guides)>MIN_GUIDES:
#                    #Drop the guide
#                    conflicts=coll_graph.drop(coll_ndx)
#                    conflicts=set([holes[i].target for i in conflicts])
#                    holes[coll_ndx].target.conflicting=conflicts
#                else:
#                    #Drop everything that conflicts with the guide
#                    dropped=coll_graph.drop_conflicting_with(coll_ndx)
#                    for i in dropped:
#                        holes[i].target.conflicting=holes[coll_ndx].target
#            elif coll_targ.is_acquisition:
#                if (len(coll_targ.field.usable_acquisitions)>MIN_ACQUISITIONS):
#                    #Drop the acquisition
#                    conflicts=coll_graph.drop(coll_ndx)
#                    conflicts=set([holes[i].target for i in conflicts])
#                    holes[coll_ndx].target.conflicting=conflicts
#                else:
#                    #Drop everything that conflicts with the acquistion
#                    dropped=coll_graph.drop_conflicting_with(coll_ndx)
#                    for i in dropped:
#                        holes[i].target.conflicting=holes[coll_ndx].target
#            elif coll_targ.is_sky or coll_targ.is_target:
#                collwith_ndxs=coll_graph.collisions(coll_ndx)
#                conflicts=set([holes[i].target for i in collwith_ndxs])
#                if coll_targ.priority < max(t.priority for t in conflicts):
#                    #Drop the target
#                    coll_targ.conflicting=conflicts
#                    coll_graph.drop(coll_ndx)
#                else:
#                    #Drop everything that conflicts with it
#                    dropped=coll_graph.drop_conflicting_with(coll_ndx)
#                    for i in dropped:
#                        holes[i].target.conflicting=holes[coll_ndx].target
#            else:
#                log.warn('Collision with {}'.format(coll_targ))


#    def plate_drillable_dictlist(self):
#        return [{'id':t.id,
#            'x':'{:.5f}'.format(t.hole.x),
#            'y':'{:.5f}'.format(t.hole.y),
#            'z':'{:.5f}'.format(t.hole.z),
#            'd':'{:.5f}'.format(t.hole.d),
#            'type':t.type} for t in self.plate_holes if not t.conflicting]

#    def save_selected_as_plate(self, name):
#        """
#        Write out a .plate file with the selected fields
#        
#        plate=name
#        key=value
#        [Field1]
#        key=value
#        [Field1:Drilled]
#        header
#        targets
#        [Field1:Undrilled]
#        header
#        targets
#        ....
#        """
#        import write_dotplate
#        
#        ph=self.plate_drillable_dictlist()
#        write_dotplate.write(name, ph, self.selected_fields)
#        write_dotplate.write_drill(name, ph, self.selected_fields)

