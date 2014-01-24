#!/usr/bin/env python
import Tkinter
import ttk
import BetterCanvas
import os
import argparse
import fieldmanager
from dimensions import PLATE_RADIUS
from ttkcalendar import date_time_picker

from logger import getLogger
log=getLogger('plateplanner')


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


class HoleInfoDialog:
        
    def __init__(self, parent, canvas, holes):
        self.canvas=canvas
        self.parent=parent
        
        if len(holes) > 1:
            self.initializeSelection(holes)
        else:
            self.initializeSingle(holes[0])
            
    def initializeSelection(self, holes):
        
        self.dialog=Tkinter.Toplevel(self.parent)
        self.dialog.bind("<FocusOut>", self.defocusCallback)
        self.dialog.bind("<Destroy>", self.destroyCallback)
        
        for i,hole in enumerate(holes):
            
            #self.canvas.itemconfigure('.'+id, state=Tkinter.DISABLED)

            lbl_str=' '.join(['{}={}'.format(k,v)
                              for k,v in hole.info.iteritems()])

            def cmd():
                self.close()
                self.initializeSingle(hole)
            item=Tkinter.Label(self.dialog, text=lbl_str)
            item.grid(row=i,column=0)
            item=Tkinter.Button(self.dialog,text='Select', command=cmd)
            item.grid(row=i,column=1)

    def initializeSingle(self, hole):

        #self.canvas.itemconfigure('.'+holeID,state=Tkinter.DISABLED)
        self.dialog=Tkinter.Toplevel(self.parent)
        self.dialog.bind("<FocusOut>", self.defocusCallback)
        self.dialog.bind("<Destroy>", self.destroyCallback)
        
        
        recs=['{}={}'.format(k,v) for k,v in hole.info.iteritems()]
        
        for txt in recs:
            Tkinter.Label(self.dialog, text=txt).pack()
        
        Tkinter.Button(self.dialog,text='Done',command=self.ok).pack()

    def defocusCallback(self, event):
        pass
        #self.ok()
    
    def ok(self):
        self.save()
        self.close()
    
    def destroyCallback(self, event):
        pass
        #self.resetHoles()

    def save(self):
        pass    
    
    def close(self):
        self.dialog.destroy()
        
    def resetHoles(self):
        if isinstance(self.holeID, str):
            self.canvas.itemconfig('.'+self.holeID,state=Tkinter.NORMAL)
        else:
            for id in self.holeID:
                self.canvas.itemconfig('.'+id,state=Tkinter.NORMAL)



class App(Tkinter.Tk):
    def __init__(self, parent):
        Tkinter.Tk.__init__(self, parent)
        self.parent = parent
        self.initialize()

    def initialize(self):
        
        self.manager=fieldmanager.Manager()
        
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
        Tkinter.Button(frame, text="Make Plate",
                       command=self.make_plate).pack()
        Tkinter.Button(frame, text="Toggle Conflicts",
                       command=self.toggle_conflicts).pack()
        self.show_conflicts=True

        #Info output
        self.info_str=Tkinter.StringVar(value='Red: 000  Blue: 000  Total: 0000')
        Tkinter.Label(frame2, textvariable=self.info_str).pack(anchor='w')
    
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
            holes=self.manager.get_holes(holeIDs)
            HoleInfoDialog(self.parent, self.canvas, holes)

    def toggle_conflicts(self):
        self.show_conflicts=not self.show_conflicts
        self.show()

    def show(self):
        self.canvas.clear()
        self.info_str.set(self.status_string())
        self.manager.draw(self.canvas, show_conflicts=self.show_conflicts)

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
        cols=('RA', 'Dec', 'nT+S', 'nConflict', 'Plate')
        tree = ttk.Treeview(new, columns=cols)
        
        tree.heading('#0',text='Name')
        for c in cols:
            tree.heading(c,text=c)
        
        for f in self.manager.fields:
            tree.insert('', 'end', f.name, text=f.name,
                        values=(f.sh.ra.sexstr,
                                f.sh.dec.sexstr,
                                len(f.targets)+len(f.skys),
                                0,''),
                        tags=())
        tree.bind(sequence='<<TreeviewSelect>>', func=self.select_fields)
        tree.pack()
    #    tree.tag_configure('ttk', background='yellow')
    #    tree.tag_bind('ttk', '<1>', itemClicked); # the item clicked can be found via tree.focus()

    def select_fields(self, event):
        log.info('Selecting {}'.format(event.widget.selection()))
        self.manager.select_fields(event.widget.selection())
        self.show()

    def make_plate(self):
        w=PopupWindow(self, get=str, query="Plate Name?")
        self.wait_window(w.top)
        self.manager.save_selected_as_plate(w.value)


class PopupWindow(object):
    def __init__(self, master, get=str, query="No query specified"):
        top=self.top=Tkinter.Toplevel(master)
        self.l=Tkinter.Label(top,text=query)
        self.l.pack()
        if get == str:
            self.e=Tkinter.Entry(top)
            self.e.pack()
            self.value=''
        self.b=Tkinter.Button(top,text='Ok',command=self.cleanup)
        self.b.pack()

    def cleanup(self):
        self.value=self.e.get()
        self.top.destroy()


if __name__ == "__main__":
    log.info('Starting...')
    app = App(None)
    app.title('Hole Mapper')
    app.mainloop()
