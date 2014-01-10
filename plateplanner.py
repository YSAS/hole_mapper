#!/usr/bin/env python
import Tkinter
import ttk
import BetterCanvas
import os
import argparse
import platethingfoo
from dimensions import PLATE_RADIUS
from ttkcalendar import date_time_picker

import logger
log=logger.getLogger('plateplanner')

def parse_cl():
    parser = argparse.ArgumentParser(description='Help undefined',
                                     add_help=True)
    parser.add_argument('-p','--port', dest='PORT',
                        action='store', required=False, type=int,
                        help='')
    parser.add_argument('--log', dest='LOG_LEVEL',
                        action='store', required=False, default='',
                        type=str,
                        help='')
    return parser.parse_args()

def getPath(sequence):
    dir=os.path.os.path.join(*sequence)
    if os.name is 'nt':
        dir='C:\\'+dir+os.path.sep
    else:
        dir=os.path.expanduser('~/')+dir+os.path.sep
    return dir



class App(Tkinter.Tk):
    def __init__(self, parent):
        Tkinter.Tk.__init__(self, parent)
        self.parent = parent
        self.initialize()

    def initialize(self):
        
        #Basic window stuff
        swid=120
        bhei=55
        whei=735
        chei=whei-bhei
        wwid=chei+swid
        self.geometry("%ix%i"%(wwid,whei))
        self.title("Foo Bar")
        
        #The sidebar
        frame = Tkinter.Frame(self, width=swid, bd=0, bg=None)#None)
        frame.place(x=0,y=0)

        #Info display
        frame2 = Tkinter.Frame(self, height=bhei, bd=0, bg=None)#None)
        frame2.place(x=0,y=whei-45-1)

        #The canvas for drawing the plate        
        self.canvas=BetterCanvas.BetterCanvas(self, chei, chei,
                                              1.01*PLATE_RADIUS,
                                              1.01*PLATE_RADIUS,
                                              bg='White')
        self.canvas.place(x=swid,y=0)
        self.canvas.bind("<Button-1>", self.canvasclick)

        #Buttons
        Tkinter.Button(frame, text="Load Fields",
                       command=self.load_fields).pack()
        Tkinter.Button(frame, text="Select Fields",
                       command=self.field_info_window).pack()

        #Info output
        self.info_str=Tkinter.StringVar(value='Red: 000  Blue: 000  Total: 0000')
        Tkinter.Label(frame2, textvariable=self.info_str).pack(anchor='w')
    
        self.manager=platethingfoo.Foo()
    
    def status_string(self):
        return 'Foobar'
    
    def canvasclick(self, event):
        #Get holes that are within a few pixels of the mouse position
        region=2
        items=self.canvas.find_overlapping(event.x-region,
                                           event.y-region,
                                           event.x+region,
                                           event.y+region)
        items=filter(lambda a: 'hole' in self.canvas.gettags(a), items)
            
        if items:
            holeIDs=tuple([tag[1:] for i in items
                                   for tag in self.canvas.gettags(i)
                                   if tag[-1].isdigit()])
            #HoleInfoDialog(self.parent, self.canvas, self.plate, holeIDs)

    def show(self):
        self.canvas.clear()
        self.info_str.set(self.status_string())
        self.manager.draw(self.canvas)

    def load_fields(self):
        from tkFileDialog import askopenfilename

        dir=getPath(('hole_mapper','plates'))
        file=askopenfilename(initialdir=dir,
                             filetypes=[('field files', '.field')])
        file=os.path.normpath(file)
        print file
        if file:
            self.manager.load(file)


    def field_info_window(self):
        print self
        new=Tkinter.Toplevel(self)
        tree = ttk.Treeview(new, columns=('size', 'modified'))
        tree['columns'] = ('RA', 'Dec', 'nT+S', 'nConflict', 'Plate')

        for f in self.manager.fields:
            tree.insert('', 'end', f['name'], text=f['name'],
                        values=(f.ra(), f.dec(),f.nfib_needed(), 0,''),
                        tags=())
        tree.bind(sequence='<<TreeviewSelect>>',func=self.select_fields)
        tree.pack()
    #    tree.tag_configure('ttk', background='yellow')
    #    tree.tag_bind('ttk', '<1>', itemClicked); # the item clicked can be found via tree.focus()

    def select_fields(self, event):
        log.info('Selecting {}'.format(event.widget.selection()))
        self.manager.select_fields(event.widget.selection())
#        for name,field in self.manager.selected_fields.iteritems():
#            if not field['obsdate']:
#                def setdatetime(obsdate):
#                    print ('Setting {} obsdate to {}'.format(field['name'],
#                                                               obsdate))
#                    field['obsdate']=obsdate
#                date_time_picker(field['name'], setdatetime)
        #TODO: Update conflicting count
        self.manager.draw(self.canvas)

def collision_detect(x,y,r):
    #build KD Tree at all xy
    tree=spatial.KDTree(zip(x, y))
    #For each point get the two nearest neighbors, (itself and next closest)
    MAX_MIN_SEP=type_clearance('G','G')
    dists,nearest_ndx=tree.query(pts,2,eps=0,p=2,
                                  distance_upper_bound=MAX_MIN_SEP)
    #Dist is distance from hole i to nearest hole nearest_ndx[i]
    dists=dists[:,1] #Don't care about self
    nearest_ndx=nearest_ndx[:,1] #Don't care about self

    
    #Check each hole type
    for t1 in hole_types:
        #Flag all x,y with type G and having a nearest neighpor
        # closer than allowed with type G
        pot_conflict=dists < clearance(t1,'G') & isG
        #
        conflict_ndx[pot_conflict]
        r[pot_conflict & ]==t1


if __name__ == "__main__":
    app = App(None)
    app.title('Hole Mapper')
    app.mainloop()
