'''
Created on Dec 12, 2009

@author: one
'''
#from Hole import *

import operator
import os.path
from logger import getLogger
from dimensions import PLATE_RADIUS, SH_RADIUS
from setup import get_all_setups, get_setup
from graphcollide import build_overlap_graph_cartesian
from holesxy import get_plate_holes
import math
from hole import Hole
import numpy as np
from assign import assign
from pathconf import OUTPUT_DIR

log=getLogger('plateplanner.platemanager')


GUIDE_COLOR_SEQUENCE=['seagreen','black','deeppink','teal','purple','green4'
                      'maroon', 'peachpuff4', 'navy', 'orange', 'saddlebrown']
def guide_color(i):
    return GUIDE_COLOR_SEQUENCE[i % len(GUIDE_COLOR_SEQUENCE)]

LABEL_MAX_Y=.7*PLATE_RADIUS
MIN_LABEL_Y_SEP=0.05*PLATE_RADIUS #must be < 2*LABEL_MAX_Y/16
LABEL_RADIUS=0.925*PLATE_RADIUS
PROJ_PLATE_LABEL_Y=.95*PLATE_RADIUS


def distribute(x, min_x, max_x, min_sep):
    """
    Adjust x such that all x are min_space apart,
    near original positions, and within min_x & max_x
    """
    return np.linspace(min_x, max_x, len(x))


class CoordShift(object):
    def __init__(self, D=64.0, R=50.68, rm=13.21875, a=0.03):
        self.enabled=False
        self.D=D
        self.R=R
        self.rm=rm
        self.a=a

    def shift(self, (x,y), force=False):
        """ 
        Shifts x and y to their new positions in scaled space,
        if self.doCoordShift is True or force is set to True.
        out=in otherwise
        """
        if (x==0.0 and y==0.0) or not (self.enabled or force):
            return (x,y)
        else:
            r=math.hypot(x, y)
            #psi = angle clockwise from vertical
            #psi=90.0 - math.atan2(y,x)
            cpsi=y/r
            spsi=x/r
            d=math.sqrt(self.R**2 - r**2) - math.sqrt(self.R**2 - self.rm**2)
            dr=d*r/(self.D+d)
            rp=(r-dr)*(1.0+self.a*cpsi)

            return (rp*spsi, rp*cpsi)


class Manager(object):
    """ Class for I don't know what yet"""
    def __init__(self):
        log.info('Started Manager')
        self.proj_coord_shift=CoordShift()
        self.selected_setups=None

    def pick_setups(self, setup_names):

        self.selected_setups=[get_setup(s) for s in setup_names]
#        setups=get_all_setups()
#        self.selected_setups=[s for s in setups if s.name in setup_names]

        #Assign setups
        assign(self.selected_setups)

    def get_holes(self, holeIDs):
        ret=[h for s in self.selected_setups for h in s.plate.all_holes
             if h.id in holeIDs]
        return ret

    def save_plug_and_config(self, canvas=None):
        """Write .plug and .m2fs of the loaded setup
        saves an eps of the canvas if passed
        """
        for s in self.selected_setups:
            s.write(dir=OUTPUT_DIR())
        if canvas:
            fname='_'.join([s.name for s in self.selected_setups])
            file=os.path.join(OUTPUT_DIR(),fname+'.eps').replace(':','-')
            canvas.postscript(file=file, colormode='color')

    def _draw_hole(self, hole, canvas, color=None, fcolor='White', radmult=1.0):
        
        pos=self.proj_coord_shift.shift(hole.position)
        rad=hole.d*radmult/2.0
        hashtag="."+hole.id
        
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
        
        #Draw holes for everything else
        for h in self.inactive_holes(showing_b=True, showing_r=True):
            self._draw_hole(h, canvas)

        #Standards
        for t in self.selected_setups[0].plate.plate_holes:
            self._draw_hole(t.hole, canvas, color='chocolate',
                            fcolor='chocolate')
        
        self._draw_with_assignements(self.selected_setups[0], canvas)
        
        #Guides and Acquisitions
        for i,s in enumerate(self.selected_setups):
            for t in s.field.guides+s.field.acquisitions:
                self._draw_hole(t.hole, canvas, color=guide_color(i),
                                fcolor=guide_color(i))
        
        for i, setup in enumerate(self.selected_setups):
            canvas.drawText((0,PROJ_PLATE_LABEL_Y-(i)*0.05*PLATE_RADIUS),
                            setup.name, color=guide_color(i),center=0)


    def draw_image(self, canvas, channel='all',radmult=.75):
        
            #What to show
            show_b=True
            show_r=True
            if channel == 'b': show_r=False
            if channel == 'r': show_b=False
        
            #Draw the setup names
            for i, setup in enumerate(self.selected_setups):
                canvas.drawText((0,PROJ_PLATE_LABEL_Y-(i)*0.05*PLATE_RADIUS),
                                setup.name, color=guide_color(i),center=0)

            #Assignments
            self._draw_with_assignements(self.selected_setups[0], canvas,
                                         radmult=radmult, lblcolor='white',
                                         show_b=show_b, show_r=show_r)
            
            #Guides an Acquisitions
            for setup in self.selected_setups:
                for t in setup.field.guides+setup.field.acquisitions:
                    self._draw_hole(t.hole, canvas, radmult=radmult,
                                    color=guide_color(i), fcolor=guide_color(i))

            #Shack Hartman
            self._draw_hole(Hole(x=0,y=0,d=2*SH_RADIUS), canvas,
                            color='Magenta',fcolor='Magenta', radmult=radmult)

            #Standards & thumbscres, etc
            for t in setup.plate.plate_holes:
                self._draw_hole(t.hole, canvas, color='Magenta',
                                fcolor='Magenta', radmult=radmult)

            #Draw little white dots where all the other holes are
            for h in self.inactive_holes(showing_b=show_b, showing_r=show_r):
                pos=self.proj_coord_shift.shift(h.position)
                canvas.drawSquare(pos, h.d/6.0, fill='White', outline='White')

    def inactive_holes(self, showing_b=False, showing_r=False):
        """ return iterable of the holes that should be drawn as little 
        white dots"""
        
        #Compile all active holes
        active_holes=[]
        setup=self.selected_setups[0]
        
        #Get the assigned targets
        if showing_b:
            targ=setup.cassette_config.assigned_targets(side='b')
            active_holes.extend([t.hole.id for t in targ])
        if showing_r:
            targ=setup.cassette_config.assigned_targets(side='r')
            active_holes.extend([t.hole.id for t in targ])
        
        #Get the guide and acquisition
        targ=[t for s in self.selected_setups
                for t in s.field.guides + s.field.acquisitions]
        active_holes.extend([t.hole.id for t in targ])
        
        #Get the plate holes
        targ=setup.plate.plate_holes
        active_holes.extend([t.hole.id for t in targ])
        
        #Find all the inactive holes
        all_holes=setup.plate.all_holes
        
        inactive=[h for h in all_holes if h.id not in active_holes]
        try:
            assert set([h.id for h in inactive]).isdisjoint(
                        t.hole.id for s in self.selected_setups
                        for t in s.to_assign if t.is_assigned)
        except AssertionError:
            import ipdb;ipdb.set_trace()
        return inactive

    def _draw_with_assignements(self, setup, canvas, radmult=1.0,
                                lblcolor='black', show_b=True, show_r=True):
        """Does not draw holes for color if not selected"""
        drawred=show_r
        drawblue=show_b
        
        #List of cassette labels and first hole positions
        labeldata=[]
        
        #Draw all the cassettes
        for cassette in setup.cassette_config:
            #canvas.drawCircle(cassette.pos, .02, outline='pink', fill='pink')
            if not cassette.used:
                continue
            
            if drawred and cassette.side=='r':
                #Draw the cassette
                self._draw_cassette(cassette, canvas, radmult=radmult)
                #Add the label, color, and start pos to the pot
                labeldata.append(('red',
                                  cassette.ordered_targets[0].hole.position,
                                  cassette.label,
                                  cassette.on_right))

            if drawblue and cassette.side=='b':
                #Draw the cassette
                self._draw_cassette(cassette, canvas, radmult=radmult)
                #Add the label, color, and start pos to the pot
                labeldata.append(('blue',
                                  cassette.ordered_targets[0].hole.position,
                                  cassette.label,
                                  cassette.on_right))
        
        labeldata.sort(key=lambda x:x[1][1])
        
        #Figure out where all the text labels should go
        labelpos=range(len(labeldata))
        
        #Left side positions
        lefts=filter(lambda i:labeldata[i][3]==False, range(len(labeldata)))
        y=distribute([labeldata[i][1][1] for i in lefts],
                     -LABEL_MAX_Y, LABEL_MAX_Y, MIN_LABEL_Y_SEP)
        x=np.sqrt(LABEL_RADIUS**2 - y**2)
        for i in range(len(lefts)):
            labelpos[lefts[i]]=x[i], y[i]

        #Right side positions
        rights=filter(lambda i:labeldata[i][3]==True, range(len(labeldata)))
        y=distribute([labeldata[i][1][1] for i in rights],
                     -LABEL_MAX_Y, LABEL_MAX_Y, MIN_LABEL_Y_SEP)
        x=-np.sqrt(LABEL_RADIUS**2 - y**2)
        for i in range(len(rights)):
            labelpos[rights[i]]=x[i], y[i]
        
        #Kludge for image cavas
#        if isinstance(canvas, ImageCanvas.ImageCanvas):
#            for i in range(len(labeldata)):
#                label=labeldata[2]
#                side=labeldata
#                if not side: #on right
#                    labelpos[i][0]-=canvas.getTextSize(label)
#                else:
#                    labelpos[i][0]-=2*canvas.getTextSize(label)

        #Draw the labels
        for i in range(len(labeldata)):
            color,hpos,label,side=labeldata[i]
            tpos=labelpos[i]

            #Draw the label
            canvas.drawText(tpos, label, color=lblcolor)

            #Connect label to cassette path
            canvas.drawLine(tpos, self.proj_coord_shift.shift(hpos),
                            fill=color, dashing=1)

    def _draw_cassette(self, cassette, canvas, radmult=1.0):
    
        if cassette.side=='r':
            color='red'
        else:
            color='blue'
        
        if cassette.used==0:
            return

        pluscrosscolor='Lime'

        holes=[t.hole for t in cassette.ordered_targets]
        
        #Draw an x across the first hole
        x,y=self.proj_coord_shift.shift(holes[0].position)
        r=2*0.08675
        canvas.drawLine((x-r,y+r),(x+r,y-r), fill=pluscrosscolor)
        canvas.drawLine((x-r,y-r),(x+r,y+r), fill=pluscrosscolor)
        
        #Draw a + over the last hole
        x,y=self.proj_coord_shift.shift(holes[-1].position)
        r=1.41*2*0.08675
        canvas.drawLine((x-r,y),(x+r,y), fill=pluscrosscolor)
        canvas.drawLine((x,y-r),(x,y+r), fill=pluscrosscolor)

        #Draw the holes in the cassette
        for h in holes:
            self._draw_hole(h, canvas, color=color, fcolor=color,
                            radmult=radmult)

        if cassette.used==1:
            return

        #Draw the paths between each of the holes
        for i in range(len(holes)-1):
            p0=holes[i].position
            p1=holes[i+1].position
            canvas.drawLine(self.proj_coord_shift.shift(p0),
                            self.proj_coord_shift.shift(p1),
                            fill=color)

