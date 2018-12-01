#!/usr/bin/env python
"""Current Changes:
    1. region around line 240 was decreased from 2. This should decrease
    the odds of multiple holes being selected on click.
    2. Added in an option to control column widths for field data
    near the end of the program. Also changed what information is displayed.
    3. Changed the procedure for outputting target data when a hole was selected.
    Now only certain information will be outputted (and in a specific order). The
    format for the multiple hole information display was also updated.
    4. Directory selection was altered to only select .field files from within
    the first directory. Additionally, multiple directories can be selected (hit
    cancel to end selection).
    5. Clear button now clears currently selected directories. This replaces the
    reset button who's purpose was unclear.
    6.Info display now includes more information including field specific
    information. Colors should match plotted colors.
    7. Added new buttons to toggle skies, alignments, and everything at once. They will update their name based on if their selection is currently visible.
    8. Added a plate name button that allow you to update the file with a plate
        name.
    9. Modified the save plate button to have more options and take advantage of
    the plate name button.
    10. Added a quit button.
    11. Added the ability to highlight object by entering their ID.
"""


import Tkinter
import ttk
import BetterCanvas
import os
import argparse
import fieldmanager
from dimensions import PLATE_RADIUS
from ttkcalendar import date_time_picker
import tkFileDialog
from datetime import datetime
from logger import getLogger
from errors import ConstraintError
import tkMessageBox
log=getLogger('plate_driller')


def parse_cl():
    parser = argparse.ArgumentParser(description='Plate Planner',
                                     add_help=True)
    parser.add_argument('-o','--out', dest='outdir',default='./',
                        action='store', required=False, type=str,
                        help='Output directory')
    parser.add_argument('--log', dest='LOG_LEVEL',
                        action='store', required=False, default='',
                        type=str,
                        help='')
    return parser.parse_args()


class FieldSettingsDialog(object):
    def __init__(self, parent, field):
        self.parent=parent
        self.field=field
        self.dialog=Tkinter.Toplevel(self.parent)
        self.dialog.title(field.name)
        

        
#        lframe=Tkinter.Frame(frame)
#        lframe.pack()
#        
#        recs=['{}={}'.format(k,v) for k,v in hole.info.iteritems()]
#        
#        for txt in recs:
#            Tkinter.Label(self.dialog, text=txt).pack()

#        Tkinter.Label(lframe, text='Setup #:').grid(row=0,column=0)


        self.mustkeep = Tkinter.IntVar(value=int(field.mustkeep))
        Tkinter.Checkbutton(self.dialog, text="Must Keep",
                            variable=self.mustkeep).pack()
        if field.obsdate:
            now=field.obsdate.strftime('%Y-%m-%d %H:%M:%S')
        else:
            now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.date_str=Tkinter.StringVar(value=now)
        Tkinter.Entry(self.dialog, validate='focusout', width=20,
                      invcmd=lambda:tkMessageBox.showerror('Bad Time',
                                                           'Y-m-d H:M:S'),
                      vcmd=self.vet_obsdate, textvariable=self.date_str).pack()
        
        
#        Tkinter.Button(self.dialog,text='Done',command=self.ok).pack()
#        item.grid(row=i,column=0)

        self.dialog.bind("<FocusOut>", self.defocusCallback)
        self.dialog.bind("<Destroy>", self.destroyCallback)

    def defocusCallback(self, event):
        pass
    
    def vet_obsdate(self):
        try:
            datetime.strptime(self.date_str.get(), '%Y-%m-%d %H:%M:%S')
            return True
        except ValueError:
            return False
    
    def destroyCallback(self, event):
        if self.save():
            self.dialog.destroy()

    def save(self):
        try:
            self.field.obsdate=datetime.strptime(self.date_str.get(),
                                                 '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return False
        self.field.mustkeep=bool(self.mustkeep.get())
        return True

class HoleInfoDialog:
        
    def __init__(self, parent, canvas, holes):
        #This definition determines if a hole is alone or with a group.
        #It then assigns the appropriate following actions.
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
            #                  for k,v in hole.info.iteritems()])
            #This reorganizes the key/values to only include certain pairs
            #and in a certain order
            #ADD IN FIELD NAME INTO INTERESTING KEYS
            interesting_keys = ('priority', 'field', 'dec', 'ra', 'epoch', 'id', 'type')
            lbl_str_sub = {k: hole.info[k] for k in interesting_keys if k in hole.info}
            lbl_str_sorted = ['{}={}\n\n'.format(k,v) for k,v in sorted(lbl_str_sub.iteritems(), key=lambda x: x[0] in interesting_keys and interesting_keys.index(x[0]) or len(interesting_keys)+1)]
            
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
        self.initialize()

    def initialize(self):
        
        self.manager=fieldmanager.Manager()
        
        #Basic window stuff
        swid=325
        bhei=55
        whei=735
        chei=whei-bhei
        wwid=chei+swid
        self.geometry("%ix%i"%(wwid,whei))
        self.title("Plate Driller")
        self.name = '' #Used for plotting the name of the field if needed
        
        #The sidebar
        frame = Tkinter.Frame(self, width=swid, bd=0, bg=None)#None)
        frame.place(x=0,y=0)

        #Info display
        self.frame2 = Tkinter.Frame(self, height=bhei, bd=0, bg=None)#None)
        self.frame2.place(x=0,y=swid)
        
        #The canvas for drawing the plate
        self.canvas=BetterCanvas.BetterCanvas(self, chei, chei,
                                              1.01*PLATE_RADIUS,
                                              1.01*PLATE_RADIUS,
                                              bg='White')
        self.canvas.place(x=swid,y=0)
        self.canvas.bind("<Button-1>", self.canvasclick)

        #Buttons
        Tkinter.Button(frame, text="Select Field Dirs",
                       command=self.load_fields).pack()
        Tkinter.Button(frame, text="Clear",
                       command=self.reset).pack()
        Tkinter.Button(frame, text="Select Fields",
                       command=self.field_info_window).pack()
        Tkinter.Button(frame, text="Plate Name",
                       command=self.plate_name).pack()
        Tkinter.Button(frame, text="Save Plate Info",
                       command=self.make_plate).pack()
                       
        self.align_str = Tkinter.StringVar(value='Hide Alignments')
        self.show_aligns=True
        Tkinter.Button(frame, textvariable=self.align_str,
                       command=self.toggle_aligns).pack()
                       
        self.sky_str = Tkinter.StringVar(value='Hide Skies')
        self.show_skies=True
        Tkinter.Button(frame, textvariable=self.sky_str,
                       command=self.toggle_skies, background='blue').pack()
                       
        self.conflict_str = Tkinter.StringVar(value='Show Conflicts')
        self.show_conflicts=False
        Tkinter.Button(frame, textvariable=self.conflict_str,
                       command=self.toggle_conflicts, bg='black').pack()
                       
        Tkinter.Button(frame, text="Toggle All", command=self.toggle_all).pack()
        Tkinter.Button(frame, text="Highlight Object",
                       command=self.highlight).pack()
        Tkinter.Button(frame, text="Quit", command=self.confirm_quit).pack()
        
        #Info output
        self.total_info_str=Tkinter.StringVar(value='Total Holes: 0')
        Tkinter.Label(self.frame2, textvariable=self.total_info_str).pack(anchor='w')

        self.tar_sky_info_str=Tkinter.StringVar(value='Total Targets + Skies: 0')
        Tkinter.Label(self.frame2, textvariable=self.tar_sky_info_str).pack(anchor='w')

        self.conflict_info_str=Tkinter.StringVar(value='Total Conflicts: 0')
        Tkinter.Label(self.frame2, textvariable=self.conflict_info_str).pack(anchor='w')
        Tkinter.Label(self.frame2,text='').pack() #Adds a blank line

        #The following produces up to 20 individual field outputs
        #However, there are currently only 10 unique colors defined in fieldmanager.py
        self.counter = range(0, 20)
        self.fname = [None]*len(self.counter)
        for i in self.counter:
            self.fname[i] = Tkinter.StringVar(value='')
            color=fieldmanager.COLOR_SEQUENCE[i%len(fieldmanager.COLOR_SEQUENCE)]
            Tkinter.Label(self.frame2, textvariable=self.fname[i], foreground=color).pack(anchor='w')
    
    def total_status_string(self):
        """
        The number of total holes includes duplicates (e.g. S shared btwn fields)
        """
        nholes=sum([len(x.drillable_dictlist())
                    for x in self.manager.selected_fields])
        nholes+=len(self.manager.plate_drillable_dictlist())
        return 'Total Holes: {}'.format(nholes)

    def individual_field_string(self):
        """
        Produces a hole count for each individual field. Counter loops
        were setup to prevent repeated labeling.
        """
        all_single = []
        for x in self.manager.selected_fields:
            group=[x.field_name, len(x.drillable_dictlist())]
            all_single.append('{} Holes: {}'.format(*group))
        if 0 <= self.count < len(all_single):
            return(all_single[self.count])
        else:
            return('')

    def conflict_status_string(self):
        """
        The total number of conflicts
        """
        return 'Total Conflicts: {}'.format(self.manager.nconflicts)

    def tar_sky_status_string(self):
        """
            The total number of targets and skies
        """
        ntar_sky=sum([x.n_drillable_targs + x.n_drillable_skys
                    for x in self.manager.selected_fields])
        return 'Total Targets + Skies: {}'.format(ntar_sky)
    
    def reset(self):
        self.name='' #Resets name
        self.manager.clear()
        self.show()
    
    def canvasclick(self, event):
        #Get holes that are within a few pixels of the mouse position
        region=.15
        items=self.canvas.find_overlapping(event.x-region,
                                           event.y-region,
                                           event.x+region,
                                           event.y+region)
        items=filter(lambda a: 'hole' in self.canvas.gettags(a), items)
            
        #This where data (like dec and ra) are assigned the corresponding holes
        if items:
            holeIDs=tuple([tag[1:] for i in items
                                   for tag in self.canvas.gettags(i)
                                   if tag[-1].isdigit()])
            holes=self.manager.get_holes(holeIDs)
            HoleInfoDialog(self.parent, self.canvas, holes)

    def toggle_conflicts(self):
        self.show_conflicts=not self.show_conflicts
        self.show()

    def toggle_skies(self):
        self.show_skies=not self.show_skies
        self.show()

    def toggle_aligns(self):
        self.show_aligns=not self.show_aligns
        self.show()

    def toggle_all(self):
        self.show_conflicts=not self.show_conflicts
        self.show_skies=not self.show_skies
        self.show_aligns=not self.show_aligns
        self.show()
    
    def highlight(self):
        """
        Highlights object with the same ID. If user selects the "clear" button
        the program returns a ID of clear. This prompts fieldmanager to erase
        the last highlighted object.
        """
        if len(self.manager.selected_fields) == 1:
            #Determines is a premade field name should be present
            current_field = self.manager.selected_fields[0].field_name
        else:
            current_field = ''
        w=PopupWindow(self, get=str, query="Enter Object ID", clear=1, optional=1,
                      optional_premade=current_field)
        self.wait_window(w.top)
        id = w.value
        field_id = w.optional_value
        if id: #This allows the cancel button to bypass execution
            self.manager.highlight_hole(self.canvas, id, field_id)

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

    def show(self):
        self.canvas.clear()
        
        #These change based on the current toggle mode
        self.align_str.set('Hide Alignments' if self.show_aligns else
                           'Show Alignments')
        self.sky_str.set('Hide Skies' if self.show_skies else
                         'Show Skies')
        self.conflict_str.set('Hide Conflicts' if self.show_conflicts else
                              'Show Conflicts')
        
        #These update total info display
        self.total_info_str.set(self.total_status_string())
        self.tar_sky_info_str.set(self.tar_sky_status_string())
        self.conflict_info_str.set(self.conflict_status_string())
        
        #This update individual field information
        for self.count in self.counter:
            self.fname[self.count].set(self.individual_field_string())
        
        self.manager.draw(self.canvas, show_conflicts=self.show_conflicts,
                          show_skies=self.show_skies, show_aligns=self.show_aligns, show_name = self.name)


    def load_fields(self):
        """
            Selection of field directories occurs here. Multiple
            directories can be selected. Subdirectories are not
            automatically included.
        """
        tkMessageBox.showinfo('Multiple Directory Selection',
                              'Directory selection continues until cancel is hit')
        dirselect = tkFileDialog.Directory(initialdir='./')
        dirs = []
        while True:
            d = dirselect.show(initialdir='./')
            if not d: break
            dirs.append(d)
        #file=tkFileDialog.askdirectory(initialdir='./')
        for file in dirs:
            file=os.path.normpath(file)
            log.info('Looking for .field files in {}'.format(file))
            if file:
                self.manager.load(file)

    def field_info_window(self):
        """
        This definition controls the information shown alongside each
        field in the select menu (including the formatting)
        """
        new=Tkinter.Toplevel(self)
        
            #cols=('RA', 'Dec', 'nT','nS', 'nLost', 'Drillable Targ', 'Drillable Sky')
        cols=('RA', 'Dec', 'nTarget','nSkies', 'nGuides', 'nAligns',
        'Targs_Drilled', 'Skies_Drilled', 'Guides_Drilled', 'Aligns_Drilled')
        self.tree = tree = ttk.Treeview(new, columns=cols)
        
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
        for c in cols:
            tree.heading(c,text=c,
                         command=lambda c=c: tree_col_sort(tree, False, col=c))
        #Here the data for the targets is actually inserted
        for f in self.manager.fields:
            try:
                tree.insert('', 'end', f.name, text=f.name, tags=(),
                        values=(f.sh.ra.sexstr, f.sh.dec.sexstr,
                                len(f.targets),len(f.skys), len(f.guides),len(f.acquisitions),
                                f.n_drillable_targs,f.n_drillable_skys,f.n_drillable_guides,f.n_drillable_acquisitions))
            except:
                log.info("Skipping {}. Already loaded".format(f))

            for c in cols: #This loop assigns proper widths to the columns
                if c == "RA" or c == "Dec":
                    tree.column(c, width = 120)
                elif (c=='Targs_Drilled' or c=='Skies_Drilled' or
                      c=='Guides_Drilled' or c=='Aligns_Drilled'):
                    tree.column(c, width = 85)
                else:
                    tree.column(c, width = 55)

        tree.bind('<Button-2>', self.field_settings)
        tree.bind('<ButtonRelease-1>', func=self.select_fields)
        tree.pack(fill=Tkinter.BOTH, expand=1)
        tree.focus()
    #    tree.tag_configure('ttk', background='yellow')
    #    tree.tag_bind('ttk', '<1>', itemClicked); # the item clicked can be found via tree.focus()

    def choose_fields(self):
        self.field_info_window(self.select_fields)

    def field_settings(self, event):
        name=event.widget.identify_row(event.y)
        field=self.manager.get_field(name)
        w=FieldSettingsDialog(self, field)
        self.wait_window(w.dialog)
    
    def select_fields(self, event):
        log.info('Selecting {}'.format(event.widget.selection()))
        try:
            self.manager.select_fields(event.widget.selection())
        except ConstraintError as e:
            tkMessageBox.showerror('Selection Error', str(e))
            
        #update treview nconflict column
        #f.name is the selection, followed by the column name, then the value
        for f in self.manager.selected_fields:
            #self.tree.set(f.name, 'nLost', f.n_conflicts)
            self.tree.set(f.name, 'Targs_Drilled', f.n_drillable_targs)
            self.tree.set(f.name, 'Skies_Drilled', f.n_drillable_skys)
            self.tree.set(f.name, 'Guides_Drilled', f.n_drillable_guides)
            self.tree.set(f.name, 'Aligns_Drilled', f.n_drillable_acquisitions)

        self.show()

    def plate_name(self):
        """
        Creates a plate name at top left.
        """
        w=PopupWindow(self, get=str, query="Enter Plate Name", premade=self.name)
        self.wait_window(w.top)
        if not w.value == 'cancel_command': #Keeps saved name when user cancels
            self.name = w.value
        self.show()


    def make_plate(self):
        """
        Name of saved plate. If a plate name is already defined, it will be
        offered as the default name.
        """
        w=PopupWindow(self, get=str, query="Enter Plate Name",
                      premade=self.name)
        self.wait_window(w.top)
        if not w.value == 'cancel_command':
            self.name = w.value
        self.manager.save_selected_as_plate(self.name)
        self.canvas.postscript(file=self.name+'.eps', colormode='color')

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


if __name__ == "__main__":
    log.info('Starting...')
    app = App(None)
    app.title('Hole Mapper')
    app.mainloop()
