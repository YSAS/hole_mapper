#!/usr/bin/env python
import Tkinter
import ttk
import BetterCanvas
import os
import argparse
import platemanager
import pathconf
from dimensions import PLATE_RADIUS
from ttkcalendar import date_time_picker
from setup import get_all_setups
import argparse
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
        self.manager=platemanager.Manager()
        self._initialize_main()
        self._initialize_projector()
        self.setup_info_window()
    
    def _initialize_projector(self):
        # create a second window and make it cover the entire projector screen
        self.proj_win=Tkinter.Toplevel(self.parent)
        self.proj_win.overrideredirect(1)
        self.proj_win.geometry("768x768+1494+0")

        self.moving={'stat':False}
        self.proj_win.bind("<Button-1>",self._start_proj_win_move)
        self.proj_win.bind("<ButtonRelease-1>",self._stop_proj_win_move)
        self.proj_win.bind("<B1-Motion>", self._move_proj_win)
        
        self.proj_can=BetterCanvas.BetterCanvas(self.proj_win, 768, 768,
                                                PLATE_RADIUS, PLATE_RADIUS,
                                                bg='Black')
        self.proj_can.place(x=-3,y=-3)

    def _start_proj_win_move(self,event):
        self._proj_moving={'stat':True, 'xs':event.x_root, 'ys':event.y_root,
                           'xi':self.proj_win.winfo_rootx(),
                           'yi':self.proj_win.winfo_rooty()}

    def _stop_proj_win_move(self,event):
        self._proj_moving['stat']=False

    def _move_proj_win(self,event):
        if self._proj_moving['stat']:
            dx=event.x_root-self._proj_moving['xs']
            dy=event.y_root-self._proj_moving['ys']
            xnew=self._proj_moving['xi']+dx
            ynew=self._proj_moving['yi']+dy
            self.proj_win.geometry("768x768+%i+%i"%(xnew,ynew))

    def _initialize_main(self):
        
        #Basic window stuff
        swid=120
        bhei=55
        whei=935
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
                                              1.05*PLATE_RADIUS,
                                              1.05*PLATE_RADIUS,
                                              bg='White')
        self.canvas.place(x=swid,y=0)
        self.canvas.bind("<Button-1>", self.canvasclick)

        #Buttons
        Tkinter.Button(frame, text="Open Picker",
                       command=self.setup_info_window).pack()
        Tkinter.Button(frame, text="Make plug",
                       command=self.make_plug).pack()
        Tkinter.Button(frame, text="Toggle Conflicts",
                       command=self.toggle_conflicts).pack()
        self.show_conflicts=True

        #Info output
        self.info_str=Tkinter.StringVar(value=self.status_string())
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
        self.proj_can.clear()
        self.info_str.set(self.status_string())
        self.manager.draw(self.canvas)
        self.manager.draw_image(self.proj_can)

    def setup_info_window(self):
    
        new=Tkinter.Toplevel(self)
        
        cols=('Nneeded', 'Nusable')
        tree = ttk.Treeview(new, columns=cols)
        
        tree.heading('#0',text='Name')
        for c in cols:
            tree.heading(c,text=c)
        
        for setup in get_all_setups():
            tree.insert('', 'end', setup.name, text=setup.name, tags=(),
                        values=(setup.n_needed_fibers, setup.n_usable_fibers))
        tree.bind(sequence='<<TreeviewSelect>>', func=self.pick_setups)
        tree.pack()
        tree.focus()

    def pick_setups(self, event):
        log.info('Selecting {}'.format(event.widget.selection()))
        self.manager.pick_setups(event.widget.selection())
        self.show()

    def make_plug(self):
        self.manager.save_plug_and_config(self.canvas)


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

def parse_cl():
    parser = argparse.ArgumentParser(description='Quadrant merger',
                                     add_help=True)
    parser.add_argument('-d','--dir', dest='dir',
                        action='store', required=False, type=str,
                        help='source dir for plate data',default='./')
    return parser.parse_args()


if __name__ == "__main__":
    log.info('Starting...')
    args=parse_cl()
    pathconf.ROOT=args.dir
    app = App(None)
    app.title('Hole Mapper')
    app.mainloop()
