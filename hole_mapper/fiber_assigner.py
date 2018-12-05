#!/usr/bin/env python2
import Tkinter
import ttk
import os
import argparse
import tkMessageBox
import tkFileDialog
from hole_mapper.logger import getLogger
from hole_mapper import BetterCanvas
from hole_mapper import platemanager
from hole_mapper import pathconf
from hole_mapper.dimensions import PLATE_RADIUS
from hole_mapper.setup import get_all_setups
from hole_mapper import errors

log=getLogger('fiber_assigner')


class HoleInfoDialog:
        
    def __init__(self, parent, canvas, holes):
        self.canvas=canvas
        self.parent=parent
        
        if len(holes) > 1:
            self.initializeSelection(holes)
        else:
            self.initializeSingle(holes[0])
            
    def initializeSelection(self, holes):
        #This definition runs if two or more holes are within close proximity.
        #It then outputs all of their data
        self.dialog=Tkinter.Toplevel(self.parent)
        self.dialog.bind("<FocusOut>", self.defocusCallback)
        self.dialog.bind("<Destroy>", self.destroyCallback)
        
        for i,hole in enumerate(holes):
            
            #self.canvas.itemconfigure('.'+id, state=Tkinter.DISABLED)
            #lbl_str=' '.join(['{}={}'.format(k,v)
            #for k,v in hole.info.iteritems()])
            #This reorganizes the key/values to only include certain pairs
            #and in a certain order
            #ADD IN FIELD NAME INTO INTERESTING KEYS
            interesting_keys = ('priority', 'field', 'dec', 'ra',
                                'epoch', 'id', 'type')
            lbl_str_sub = {k: hole.info[k] for k in interesting_keys if k in hole.info}
            lbl_str_sorted = ['{}={}\n\n'.format(k,v) for k,v in
                              sorted(lbl_str_sub.iteritems(), key=lambda x: x[0]
                                     in interesting_keys and
                                     interesting_keys.index(x[0]) or
                                     len(interesting_keys)+1)]
        
            def cmd():
                self.close()
                self.initializeSingle(hole)
            
            item=Tkinter.Label(self.dialog, text=''.join(map(str,lbl_str_sorted)))
            item.grid(row=0,column=i)
            item=Tkinter.Button(self.dialog,text='Select', command=cmd)
            item.grid(row=1,column=i)
    
    def initializeSingle(self, hole):
        #This definition runs if extra holes are not nearby
        #self.canvas.itemconfigure('.'+holeID,state=Tkinter.DISABLED)
        self.dialog=Tkinter.Toplevel(self.parent)
        self.dialog.bind("<FocusOut>", self.defocusCallback)
        self.dialog.bind("<Destroy>", self.destroyCallback)
        
        #This extracts the desired items from the hole dictionary
        #For some reason the first key becomes the last so priority is listed first
        interesting_keys = ('priority', 'field', 'dec', 'ra', 'epoch', 'id', 'type')
        recs_sub = {k: hole.info[k] for k in interesting_keys if k in hole.info}
        recs_sorted = ['{}={}'.format(k,v) for k,v in sorted(recs_sub.iteritems(),key=lambda x: x[0] in interesting_keys and interesting_keys.index(x[0]) or len(interesting_keys)+1)]
        #recs=['{}={}'.format(k,v) for k,v in recs_sub.iteritems()]
        for txt in recs_sorted:
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
#        self._initialize_projector()
    
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
        swid=515
        bhei=55
        whei=685
        chei=whei-bhei
        wwid=chei+swid
        self.geometry("%ix%i"%(wwid,whei))
        self.title("Selection Window")
        
        #The sidebar
        frame = Tkinter.Frame(self, width=swid, bd=0, bg=None)#None)
        frame.place(x=0,y=0)

        #Info display
        frame2 = Tkinter.Frame(self, height=bhei, bd=0, bg=None)#None)
        frame2.place(x=0,y=whei-300)

        #The canvas for drawing the plate        
        self.canvas=BetterCanvas.BetterCanvas(self, chei, chei,
                                              1.05*PLATE_RADIUS,
                                              1.05*PLATE_RADIUS,
                                              bg='White')
        self.canvas.place(x=swid,y=0)
        self.canvas.bind("<Button-1>", self.canvasclick)

        #Buttons
        Tkinter.Label(frame,text='Directory Selection',font=("Helvetica",
                                                             16)).pack()
        Tkinter.Button(frame, text="Select a Main Dir",
                       command=self.preprepared_dir).pack()
        Tkinter.Label(frame,text='').pack()
        Tkinter.Label(frame,text='Indiv Subdir Selection',font=("Helvetica",
                                                                16)).pack()
        Tkinter.Button(frame, text="Select Run Parameters Dir",
                       command=self.select_run_params).pack()
        Tkinter.Button(frame, text="Select M2FS Parameters Dir",
                        command=self.select_m2fs_params).pack()
        Tkinter.Button(frame, text="Select Setup Dir",
                        command=self.select_setup_dir).pack()
        Tkinter.Button(frame, text="Select Output Dir",
                        command=self.select_output_dir).pack()
        Tkinter.Label(frame,text='').pack()
        Tkinter.Label(frame,text='Program Tools',font=("Helvetica",
                                                                16)).pack()
        Tkinter.Button(frame, text="Selection Window",
                       command=self.setup_info_window).pack()
        Tkinter.Button(frame, text="Save Assignment",
                       command=self.make_plug).pack()
        Tkinter.Button(frame, text="Quit", command=self.confirm_quit).pack()
        self.show_conflicts=True

        #Info output
        self.info_str=Tkinter.StringVar(value=self.status_string())
        Tkinter.Label(frame2, textvariable=self.info_str).pack(anchor='w')
    
        self.run_params_str=Tkinter.StringVar(value=pathconf.run_params_dir)
        Tkinter.Label(frame2, text='Run Parameters Dir:').pack(anchor='w')
        Tkinter.Label(frame2, textvariable=self.run_params_str).pack(anchor='w')

        self.m2fs_params_str=Tkinter.StringVar(value=pathconf.m2fs_params_dir)
        Tkinter.Label(frame2, text='M2FS Parameters Dir:').pack(anchor='w')
        Tkinter.Label(frame2, textvariable=self.m2fs_params_str).pack(anchor='w')
  
        self.setups_str=Tkinter.StringVar(value=pathconf.setups_dir)
        Tkinter.Label(frame2, text='Setups Dir:').pack(anchor='w')
        Tkinter.Label(frame2, textvariable=self.setups_str).pack(anchor='w')
  
        self.output_str=Tkinter.StringVar(value=pathconf.output_dir)
        Tkinter.Label(frame2, text='Output Dir:').pack(anchor='w')
        Tkinter.Label(frame2, textvariable=self.output_str).pack(anchor='w')
        self.show_paths()
  
  
    def status_string(self):
        return ''
    
    def canvasclick(self, event):
        #Get holes that are within a few pixels of the mouse position
        region=.15
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

    def show(self):
        """ Updates the canvas """
        self.canvas.clear()
        self.info_str.set(self.status_string())
        self.manager.draw(self.canvas)
    
    def update_string(self, directory, dir_name):
        """
            Updates text for desired directory on the program display
        """
        if directory:
            if os.path.exists(directory):
                return(directory)
            else:
                return('Not Selected')
        elif dir_name == 'output': #output always has a default directory
            if os.path.exists(os.path.join(os.getcwd(),dir_name)+os.sep):
                return(os.path.join(os.getcwd(),dir_name)+os.sep)
            else:
                return(os.path.join(os.getcwd())+os.sep)
        else:
            if os.path.exists(os.path.join(os.getcwd(),dir_name)+os.sep):
                return(os.path.join(os.getcwd(),dir_name)+os.sep)
            else:
                return('Not Selected')

    def show_paths(self):
        """
            Updates the text for program paths on the display
        """
        self.info_str.set(self.status_string())
        self.run_params_str.set(self.update_string(pathconf.run_params_dir, 'Run_Params'))
        self.m2fs_params_str.set(self.update_string(pathconf.m2fs_params_dir, 'M2FS_Params'))
        self.setups_str.set(self.update_string(pathconf.setups_dir, 'setups'))
        self.output_str.set(self.update_string(pathconf.output_dir, 'output'))

    def preprepared_dir(self):
        """
        Allows the user to specify a directory containing the default
        subdirectories (m2fs params, output, run_params, setups). If this is run
        all user defined paths are reset automatically
        """
        pathconf.run_params_dir=None
        pathconf.m2fs_params_dir=None
        pathconf.setups_dir=None
        pathconf.output_dir=None
        tkMessageBox.showinfo('Select Preprepared Directory Location',
                              'Directory must contain "M2FS_Params" (must contain configs), "output", "Run_Params" (must contain  "deadfibers.txt"), and "setups" subdirectories. The names given are the exact names searched for.\n\nNote that all subdirectory paths are reset by running this and must be manually re-entered if desired.')
        path_preprepared_dir=tkFileDialog.askdirectory(initialdir='./')
        if not path_preprepared_dir == '':
            os.chdir(path_preprepared_dir) #Changes work directory to selected one
        self.show_paths()

    def select_run_params(self):
        selected_dir1=tkFileDialog.askdirectory(initialdir='./')
        if not selected_dir1 == '':
            pathconf.run_params_dir = selected_dir1
        self.show_paths()

    def select_m2fs_params(self):
        selected_dir2=tkFileDialog.askdirectory(initialdir='./')
        if not selected_dir2 == '':
            pathconf.m2fs_params_dir = selected_dir2
        self.show_paths()

    def select_setup_dir(self):
        selected_dir3=tkFileDialog.askdirectory(initialdir='./')
        if not selected_dir3 == '':
            pathconf.setups_dir = selected_dir3
        self.show_paths()

    def select_output_dir(self):
        selected_dir4=tkFileDialog.askdirectory(initialdir='./')
        if not selected_dir4 == '':
            pathconf.output_dir = selected_dir4
        self.show_paths()

    def setup_info_window(self):
    
        new=Tkinter.Toplevel(self)
        
        cols=('Nneeded', 'Nusable')
        tree = ttk.Treeview(new, columns=cols)
        
        def tree_col_sort(tv, reverse, col=''):
            if col=='#0':
                l=[(k,k) for k in tv.get_children('')]
            else:
                l = [(tv.set(k, col), k) for k in tv.get_children('')]
            
            #sort like numbers if possible
            try:
                l=[(float(x[0]),x[1]) for x in l]
            except ValueError:
                pass
    
            l.sort(reverse=reverse)

            # rearrange items in sorted positions
            for index, (val, k) in enumerate(l): tv.move(k, '', index)

            # reverse sort next time
            tv.heading(col, command=lambda: tree_col_sort(tv, not reverse,
                                                          col=col))
        
        tree.heading('#0',text='Name',
                     command=lambda: tree_col_sort(tree, False, col='#0'))
        tree.column('#0', width=500)
        for c in cols:
            tree.heading(c,text=c,
                         command=lambda c=c: tree_col_sort(tree, False, col=c))
            tree.column(c, width=55)
        
        for setup in get_all_setups():
            tree.insert('', 'end', setup.name, text=setup.name, tags=(),
                        values=(setup.n_needed_fibers, setup.n_usable_fibers))
        tree.bind(sequence='<<TreeviewSelect>>', func=self.pick_setups)
        tree.pack(fill=Tkinter.BOTH, expand=1)
        tree.focus()

    def pick_setups(self, event):
        log.info('Selecting {}'.format(event.widget.selection()))
        try:
            self.manager.pick_setups(event.widget.selection())
        except errors.ConstraintError as e:
            log.critical('Selection failed: {}'.format(e))
            tkMessageBox.showerror('Mapping Error', str(e))
        self.show()

    def make_plug(self):
        self.manager.save_plug_and_config(self.canvas)

    def confirm_quit(self):
        """
        Allows the user to quit the program
        """
        quit_window=Tkinter.Toplevel()
        quit_label=Tkinter.Label(quit_window,text="           Are you sure?           ")
        quit_label.pack()
        confirm=Tkinter.Button(quit_window,text='Yes, quit',command=self.actually_quit)
        confirm.pack()
        cancel=Tkinter.Button(quit_window,text='No, cancel',
                              command=quit_window.destroy)
        cancel.pack()

    def actually_quit(self):
        """Executes the quit (as there were issues doing this in line"""
        quit()

class PopupWindow(object):
    def __init__(self, master, get=str, query="No query specified", premade='',
                 optional_premade='', clear=0, optional=0):
        self.optional = optional
        top=self.top=Tkinter.Toplevel(master)
        self.l=Tkinter.Label(top,text=query)
        self.l.pack()
        if get == str:
            self.e=Tkinter.Entry(top)
            self.e.insert(0, premade) #Adds a premade entry if provided
            self.e.pack()
            self.value=''
            if optional: #Used for optional second entry line (like for highlight)
                self.ol=Tkinter.Label(top,text='Optional: Enter Field Name')
                self.ol.pack()
                self.o=Tkinter.Entry(top)
                self.o.insert(0, optional_premade)
                self.o.pack()
            self.optional_value=None
        self.b=Tkinter.Button(top,text='Confirm',command=self.cleanup)
        self.b.pack()
        if clear:
            self.a=Tkinter.Button(top,text='Clear Previous Highlight',
                                  command=self.clear)
            self.a.pack()
        self.c=Tkinter.Button(top,text='Cancel',command=self.cancel)
        self.c.pack()
    
    def clear(self): #Clears last input (like for highlight feature)
        self.value='clear_command'
        self.top.destroy()
    
    def cleanup(self):
        self.value=self.e.get()
        if self.optional:
            self.optional_value = self.o.get()
        self.top.destroy()
    
    def cancel(self): #Cancel without altering any features
        self.value = 'cancel_command'
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
    app.title('Fiber Assigner')
    app.mainloop()
