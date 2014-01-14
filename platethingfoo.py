'''
Created on Dec 12, 2009

@author: one
'''
#from Hole import *
#import ImageCanvas
#from plateHoleInfo import plateHoleInfo
import operator
#import Cassette
import os.path
import logger
log=logger.getLogger('plateplanner.foo')

from dimensions import PLATE_RADIUS, SH_RADIUS
from field import load_dotfield

COLOR_SEQUENCE=['red','blue','pink','green','black','teal','purple','orange']

#SCALE=14.25 #also change in plateHoleInfo.py

#RADIUS=1.0 # 14.25/SCALE


#deltara=np.rad2deg*arccos(cos(180*np.deg2rad/3600)*sec(dec)**2 - tan(dec)**2)


def gen_hole_hash(hole):
    return str(hole.__hash__())

class Foo(object):
    """ Class for I don't know what yet"""
    def __init__(self):
        self.fields=[]
        self.selected_fields={}

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
                self.fields.append(load_dotfield(f))
        
        except IOError as e:
            log.warn(str(e))

    def clear(self):
        self.fields=[]
        self.selected_fields={}

    def get_holes(self, holeIDs):
        ret=[]
        for f in self.fields:
            for h in f.holes():
                if gen_hole_hash(h) in holeIDs:
                    ret.append(h)
        return ret

    def _drawHole(self, hole, canvas, color=None, fcolor='White', radmult=1.0):
        
        drawimage=False
        
        pos=hole['x'],hole['y']
        rad=hole['r']*radmult
        
        hashtag="."+gen_hole_hash(hole)
        
        if drawimage:
            canvas.drawCircle(pos, rad, outline=color, fill=fcolor)
        else:
            if canvas.find_withtag(hashtag):
                log.info("drawing dupe in dark green @ {} IDs: {}".format(
                    pos,gen_hole_hash(hole)))
                fcolor='DarkGreen'
            canvas.drawCircle(pos, rad,
                              outline=color, fill=fcolor, tags=('hole',hashtag),
                              activefill='Green', activeoutline='Green',
                              disabledfill='Orange', disabledoutline='Orange')

    def draw(self, canvas):
        
        #Make a circle of appropriate size in the window
        canvas.drawCircle( (0,0) , PLATE_RADIUS)
        
        canvas.drawCircle( (0,0) , SH_RADIUS)
        
        for i,f in enumerate(self.selected_fields.itervalues()):
            if not f.isProcessed():
                f.process()
            for h in f.holes():
                self._drawHole(h, canvas,
                               color=COLOR_SEQUENCE[i%len(COLOR_SEQUENCE)])

    def select_fields(self,field_names):

        fnames=[f['name'] for f in self.fields]
        for i,name in enumerate(fnames):
            if name in field_names and name not in self.selected_fields:
                self.selected_fields[name]=self.fields[i]

    def save_selected_as_plate(self):
        """Write out a .plate file with the selected fields"""



    
