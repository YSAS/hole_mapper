'''
Created on Dec 12, 2009

@author: one
'''
#from Hole import *

import operator
import os.path
from logger import getLogger
from dimensions import PLATE_RADIUS, SH_RADIUS
from setup import load_dotsetup
from graphcollide import build_overlap_graph_cartesian
from holesxy import get_plate_holes
import math
from hole import Hole
import numpy as np
log=getLogger('plateplanner.platemanager')


COLOR_SEQUENCE=['red','blue','pink','green','black','teal','purple','orange']
GUIDE_COLOR_SEQUENCE=['green','purple','orange','yellow']


LABEL_MAX_Y=.7*PLATE_RADIUS
MIN_LABEL_Y_SEP=0.05*PLATE_RADIUS #must be < 2*LABEL_MAX_Y/16
LABEL_RADIUS=0.95*PLATE_RADIUS
PROJ_PLATE_LABEL_Y=.95*PLATE_RADIUS


def distribute(x, min_x, max_x, min_sep):
    """
    Adjust x such that all x are min_space apart,
    near original positions, and within min_x & max_x
    """
    return np.linspace(min_x, max_x, len(x))


#deltara=np.rad2deg*arccos(cos(180*np.deg2rad/3600)*sec(dec)**2 - tan(dec)**2)

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
        self.selected_setup=None

    def load(self, file):
        """ 
        Routine to a file

        At present only .setup files are supported.
        """
        try:
            self.selected_setup=load_dotsetup(file, load_awith=True)
            #import ipdb;ipdb.set_trace()
            self.selected_setup.assign()
            log.info("Loaded {}")
        except IOError as e:
            log.warn(str(e))

    def get_holes(self, holeIDs):
        ret=[h for h in self.selected_setup.plate.all_holes if h.id in holeIDs]
        return ret

    def save_plug_and_config(self):
        """Write .plug and .m2fs of the loaded setup"""
        for s in [self.selected_setup]+self.selected_setup.assign_with:
            s.write(dir='./')

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
        setup=self.selected_setup
        
        #Make a circle of appropriate size in the window
        canvas.drawCircle( (0,0) , PLATE_RADIUS)
        canvas.drawCircle( (0,0) , SH_RADIUS)
        
        self._draw_with_assignements(setup, canvas)
        
        #Guides an Acquisitions
        for t in setup.field.guides+setup.field.acquisitions:
            self._draw_hole(t.hole, canvas, color='Yellow',fcolor='Yellow')
        
        #Standards
        for t in setup.plate.plate_holes:
            self._draw_hole(t.hole, canvas, color='Magenta',fcolor='Magenta')
        
        #Draw holes for everything else
        for h in self.inactive_holes(showing_b=True, showing_r=True):
            self._draw_hole(h, canvas)

    def draw_image(self, canvas, channel='all',radmult=.75):
            #the active setup
            setup=self.selected_setup
            
            plate_name=setup.name

            #Draw the plate name and active setup
            canvas.drawText((0,PROJ_PLATE_LABEL_Y), setup.name,
                            color=GUIDE_COLOR_SEQUENCE[0],center=0)
            for i,aw in enumerate(setup.assign_with):
                canvas.drawText((0,PROJ_PLATE_LABEL_Y-(i+1)*0.05*PLATE_RADIUS),
                                aw.name,
                                color=GUIDE_COLOR_SEQUENCE[i+1],center=0)

            #Shack Hartman
            self._draw_hole(Hole(x=0,y=0,d=2*SH_RADIUS), canvas,
                            color='Magenta',fcolor='Magenta',
                            radmult=radmult)

            #Assignments
            self._draw_with_assignements(self.selected_setup, canvas,
                                         radmult=radmult, lblcolor='white')
            
            #Guides an Acquisitions
            for t in setup.field.guides+setup.field.acquisitions:
                self._draw_hole(t.hole, canvas, radmult=radmult,
                                color=GUIDE_COLOR_SEQUENCE[0],
                                fcolor=GUIDE_COLOR_SEQUENCE[0])


            for i,aw in enumerate(setup.assign_with):
                for t in aw.field.guides+aw.field.acquisitions:
                    self._draw_hole(t.hole, canvas, radmult=radmult,
                                    color=GUIDE_COLOR_SEQUENCE[i+1],
                                    fcolor=GUIDE_COLOR_SEQUENCE[i+1])

            #Standards
            for t in setup.plate.plate_holes:
                self._draw_hole(t.hole, canvas,
                                color='Magenta',fcolor='Magenta',
                                radmult=radmult)

            #Draw little white dots where all the other holes are
            for h in self.inactive_holes(showing_b=True, showing_r=True):
                pos=self.proj_coord_shift.shift(h.position)
                canvas.drawSquare(pos, h.d/6.0, fill='White', outline='White')

    def inactive_holes(self, showing_b=False, showing_r=False):
        """ return iterable of the holes that should be drawn as little 
        white dots"""
        
        #Compile all active holes
        active_holes=[]
        
        #Get the assigned targets
        if showing_b:
            targ=self.selected_setup.cassette_config.assigned_targets(side='b')
            active_holes.extend([t.hole for t in targ])
        if showing_r:
            targ=self.selected_setup.cassette_config.assigned_targets(side='r')
            active_holes.extend([t.hole for t in targ])
        
        #Get the guide and acquisition
        targ=(self.selected_setup.field.guides+
              self.selected_setup.field.acquisitions)
        active_holes.extend([t.hole for t in targ])
        
        for aw in self.selected_setup.assign_with:
            targ=aw.field.guides+aw.field.acquisitions
            active_holes.extend([t.hole for t in targ])
        
        #Get the plate holes
        targ=self.selected_setup.plate.plate_holes
        active_holes.extend([t.hole for t in targ])
        
        #Find all the inactive holes
        all_holes=self.selected_setup.plate.all_holes
        

        return [h for h in all_holes if h not in active_holes]

    def _draw_with_assignements(self, setup, canvas, radmult=1.0,
                                lblcolor='black'):
        """Does not draw holes for color if not selected"""
        drawred=True
        drawblue=True
        
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

