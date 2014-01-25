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

log=getLogger('plateplanner.platemanager')


COLOR_SEQUENCE=['red','blue','pink','green','black','teal','purple','orange']


LABEL_MAX_Y=.7
MIN_LABEL_Y_SEP=0.05 #must be < 2*LABEL_MAX_Y/16
LABEL_RADIUS=0.95*PLATE_RADIUS
#PROJ_PLATE_LABEL_Y=.95


def distribute(x, min_x, max_x, min_sep):
    """
    Adjust x such that all x are min_space apart,
    near original positions, and within min_x & max_x
    """
    import numpy as np
    return np.linspace(min_x, max_x, len(x))


#deltara=np.rad2deg*arccos(cos(180*np.deg2rad/3600)*sec(dec)**2 - tan(dec)**2)

class Manager(object):
    """ Class for I don't know what yet"""
    def __init__(self):
        log.info('Started Manager')
        self.do_coord_shift=False

    def load(self, file):
        """ 
        Routine to a file

        At present only .setup files are supported.
        """
        try:
            self.setups=load_dotsetup(file, load_awith=True)
            self.selected_setup=self.setups[0]
            self.selected_setup.assign()
            log.info("Loaded {}")
        except IOError as e:
            log.warn(str(e))

    def clear(self):
        for s in self.setups:
            setup.reset()

    def get_holes(self, holeIDs):
        ret=[]
        for setup in self.setups:
            for h in setup.field.holes():
                if h.id in holeIDs:
                    ret.append(h)
        return ret
    
    def select_setup(self, name):
        self.selected_setup=[s for s in self.setups if s.name == name][0]
        self.selected_setup.assign()


    def save_plug_and_config(self):
        """Write .plug and .m2fs of the loaded setup"""
        #TODO


    def _draw_hole(self, hole, canvas, color=None,
                   fcolor='White', radmult=1.0, drawimage=False):
        
        pos=hole.x,hole.y
        rad=hole.d*radmult/2.0
        
        hashtag="."+hole.id
        
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
        
        
#        inactiveHoles=setup.plate..difference(setup['unused_holes'])
#        inactiveHoles.difference_update(setup['holes'])
#        
#        inactiveHoles.add(self.plateHoleInfo.standard['hole'])
#        inactiveHoles.add(self.plateHoleInfo.sh_hole)
#        
#        #Draw the holes that aren't in the current setup
#        for h in inactiveHoles:
#            self.drawHole(h, canvas)

        
        self._draw_with_assignements(self.selected_setup, canvas)
        
#        for g in setup.field.guides:
#            if not g.conflicting::.conflicting)
#        
#        for i,f in enumerate(self.selected_setup):
#
#            c=COLOR_SEQUENCE[i%len(COLOR_SEQUENCE)]
#            for h in f.holes():
#                if h.target.conflicting !=None:
#                    log.warn('{} conflicts with {}'.format(
#                                         h.target, h.target.conflicting_ids))
#                fcolor=c if h.target.conflicting else 'White'
#                self._draw_hole(h, canvas, color=c, fcolor=fcolor)

    def _draw_with_assignements(self, setup, canvas, lblcolor='black'):
        """Does not draw holes for color if not selected"""
        drawred=True
        drawblue=True
        drawimage=False
        
        #List of cassette labels and first hole positions
        labeldata=[]
        
        #Draw all the cassettes
        for cassette in setup.cassette_config:
            #canvas.drawCircle(cassette.pos, .02, outline='pink', fill='pink')
            if not cassette.used:
                continue
            
            if drawred and cassette.side=='r':
                #Draw the cassette
                self._draw_cassette(cassette, canvas, drawimage=drawimage)
                #Add the label, color, and start pos to the pot
                labeldata.append(('red',
                                  cassette.ordered_targets[0].hole.position,
                                  cassette.label,
                                  cassette.on_right))

            if drawblue and cassette.side=='b':
                #Draw the cassette
                self._draw_cassette(cassette, canvas, drawimage=drawimage)
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
        x=LABEL_RADIUS**2 - y**2
        for i in range(len(lefts)):
            labelpos[lefts[i]]=x[i], y[i]

        #Right side positions
        rights=filter(lambda i:labeldata[i][3]==True, range(len(labeldata)))
        y=distribute([labeldata[i][1][1] for i in rights],
                     -LABEL_MAX_Y, LABEL_MAX_Y, MIN_LABEL_Y_SEP)
        x=-(LABEL_RADIUS**2 - y**2)
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
            canvas.drawLine(tpos, self.plate_coord_shift(hpos),
                            fill=color, dashing=1)

    def _draw_cassette(self, cassette, canvas,  drawimage=False):
    
        if cassette.side=='r':
            color='red'
        else:
            color='blue'
        
        if cassette.used==0:
            return

        pluscrosscolor='Lime'


        holes=[t.hole for t in cassette.ordered_targets]
        
        #Draw an x across the first hole
        x,y=self.plate_coord_shift(holes[0].position)
        r=2*0.08675
        canvas.drawLine((x-r,y+r),(x+r,y-r), fill=pluscrosscolor)
        canvas.drawLine((x-r,y-r),(x+r,y+r), fill=pluscrosscolor)
        
        #Draw a + over the last hole
        x,y=self.plate_coord_shift(holes[-1].position)
        r=1.41*2*0.08675
        canvas.drawLine((x-r,y),(x+r,y), fill=pluscrosscolor)
        canvas.drawLine((x,y-r),(x,y+r), fill=pluscrosscolor)

        #Draw the holes in the cassette
        for h in holes:
            self._draw_hole(h, canvas, color=color, fcolor=color,
                            drawimage=drawimage)

        if cassette.used==1:
            return

        #Draw the paths between each of the holes
        for i in range(len(holes)-1):
            p0=holes[i].position
            p1=holes[i+1].position
            canvas.drawLine(self.plate_coord_shift(p0),
                            self.plate_coord_shift(p1),
                            fill=color)

    def plate_coord_shift(self, (x, y), force=False):
        """ Shifts x and y to their new positions in scaled space,
            if self.doCoordShift is True or force is set to True.
            out=in otherwise"""
        if (not self.do_coord_shift and
            not force or (x==0.0 and y==0.0)):
            return (x,y)
        else:
            D=self.coordShift_D
            a=self.coordShift_a
            R=self.coordShift_R
            rm=self.coordShift_rm
            
            r=math.hypot(x, y)
            #psi = angle clockwise from vertical
            #psi=90.0 - math.atan2(y,x)
            cpsi=y/r
            spsi=x/r
            d=math.sqrt(R**2 - r**2) - math.sqrt(R**2 - rm**2)
            dr=d*r/(D+d)
            
            rp=(r-dr)*(1.0+a*cpsi)

            return (rp*spsi, rp*cpsi)

