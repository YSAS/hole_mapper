import Tkinter
import bettercanvas2
import imagecanvas
import Plate

class HoleInfoDialog:
        
    def __init__(self, parent, canvas, plate, setup, holeIDs):
        self.canvas=canvas
        self.parent=parent
        self.getHoleInfo=lambda a:plate.getHoleInfo(a)
        self.getHoleFiber=lambda a:plate.getFiberforHole(a, setup=setup)
        
        if len(holeIDs) > 1:
            self.initializeSelection(holeIDs)
        else:
            self.initializeSingle(holeIDs[0])
            
    def initializeSelection(self, holeIDs):
        
        self.dialog=Tkinter.Toplevel(self.parent)
        self.dialog.bind("<FocusOut>", self.defocusCallback)
        self.dialog.bind("<Destroy>", self.destroyCallback)
        
        self.holeID=holeIDs
        
        for i,id in enumerate(holeIDs):
            
            self.add_callback_for_id(id)
            
            self.canvas.itemconfigure('.'+id, state=Tkinter.DISABLED)

            info=self.getHoleInfo(id)
            
            Tkinter.Label(self.dialog, text=id+' additional info, strvar'+', '.join(info)).grid(row=i,column=0)
            
            Tkinter.Button(self.dialog,text='Select',command=getattr(self,'cb'+id)).grid(row=i,column=1)
                

    def initializeSingle(self, holeID):
        info=self.getHoleInfo(holeID)
        self.canvas.itemconfigure('.'+holeID,state=Tkinter.DISABLED)
        self.holeID=holeID
        self.dialog=Tkinter.Toplevel(self.parent)
        self.dialog.bind("<FocusOut>", self.defocusCallback)
        self.dialog.bind("<Destroy>", self.destroyCallback)
        Tkinter.Label(self.dialog, text=holeID).pack()
        for i in info:
            Tkinter.Label(self.dialog, text=i).pack()
        Tkinter.Label(self.dialog, text="Assigned Fiber: "+self.getHoleFiber(holeID)).pack()
        Tkinter.Button(self.dialog,text='Done',command=self.ok).pack()


    def add_callback_for_id(self, holeID):
        def innercb():
            self.close()
            self.initializeSingle(holeID)
        innercb.__name__ = "cb"+holeID
        setattr(self,innercb.__name__,innercb)
        

    def defocusCallback(self, event):
        self.ok()
    
    def ok(self):
        self.save()
        self.close()
    
    def destroyCallback(self, event):
        self.resetHoles()

    def save(self):
        pass    
    
    def close(self):   
        self.resetHoles()
        self.dialog.destroy()
        
    def resetHoles(self):
        if isinstance(self.holeID, str):
            self.canvas.itemconfig('.'+self.holeID,state=Tkinter.NORMAL)
        else:
            for id in self.holeID:
                self.canvas.itemconfig('.'+id,state=Tkinter.NORMAL)
        
        
class App(Tkinter.Tk):
    wh=710
    ww=610
    ih=100
    def __init__(self, parent):
        Tkinter.Tk.__init__(self, parent)
        self.parent = parent
        self.initialize()

    def initialize(self):

        self.plate=Plate.Plate()
        self.file_str=Tkinter.StringVar(value='No File Loaded')
        
        #Basic window stuff
        swid=120
        bhei=55
        whei=855
        chei=whei-bhei
        wwid=chei+swid
        self.geometry ("%ix%i"%(wwid,whei))
        self.title("Hole App")
        
        
        #The sidebar
        frame = Tkinter.Frame(self, width=swid, bd=0, bg=None)#None)
        frame.place(x=0,y=0)

        #Info display
        frame2 = Tkinter.Frame(self, height=bhei, bd=0, bg=None)#None)
        frame2.place(x=0,y=whei-45-1)

        #The canvas for drawing the plate        
        self.canvas=bettercanvas2.BetterCanvas2(self, chei, chei, 1.01, 1.01, bg='White')
        self.canvas.place(x=swid,y=0)
        self.canvas.bind("<Button-1>",self.canvasclick)


        #Buttons
        Tkinter.Button(frame, text="Show Holes", command=self.show).pack()
        Tkinter.Button(frame, text="Show Red", command=self.showRed).pack()
        Tkinter.Button(frame, text="Show Blue", command=self.showBlue).pack()
        Tkinter.Button(frame, text="Regionify", command=self.makeRegions).pack()
        Tkinter.Button(frame, text="Make Image", command=self.makeImage).pack()
        Tkinter.Button(frame, text="Make R Image", command=self.makeImageRed).pack()
        Tkinter.Button(frame, text="Make B Image", command=self.makeImageBlue).pack()
        Tkinter.Button(frame, text="Load Holes", command=self.load).pack()
        Tkinter.Button(frame, text="Write Map", command=self.writeMap).pack()
        Tkinter.Button(frame, text="Toggle Coord", command=self.toggleCoord).pack()
       
        #Input
        #Setup input
        self.setup_str=Tkinter.StringVar(value='1')
        
        lframe=Tkinter.Frame(frame)
        lframe.pack()
        
        Tkinter.Label(lframe, text='Setup #:').grid(row=0,column=0)
        Tkinter.Entry(lframe, validate='focusout', width=2, invalidcommand=self.invsetupen,
            vcmd=self.validatesetupen, textvariable=self.setup_str).grid(row=0,column=1)
   
        #Coordinate shift input

        self.Dparam_str=Tkinter.StringVar(value='61')
        self.rmparam_str=Tkinter.StringVar(value='13.21875')
        self.aparam_str=Tkinter.StringVar(value='0.01')
        self.Rparam_str=Tkinter.StringVar(value='50.68')
        
        paramw=4
        pframe=Tkinter.LabelFrame(frame,text='Coord. Params',relief='flat')
        pframe.pack()
        Dframe=Tkinter.LabelFrame(pframe,text='D',relief='flat')
        Dframe.grid(row=0,column=0)
        Tkinter.Entry(Dframe, validate='focusout', width=paramw,
            vcmd=lambda:self.plate.validCoordParam_D(self.Dparam_str.get()),
            textvariable=self.Dparam_str).pack()#grid(row=1,column=3)
            
        rmframe=Tkinter.LabelFrame(pframe,text='rm',relief='flat')
        rmframe.grid(row=0,column=1)
        Tkinter.Entry(rmframe, validate='focusout', width=paramw,
            vcmd=lambda:self.plate.validCoordParam_rm(self.rmparam_str.get()),
            textvariable=self.rmparam_str).pack()#grid(row=1,column=3)

        Rframe=Tkinter.LabelFrame(pframe,text='R',relief='flat')
        Rframe.grid(row=1,column=0)
        Tkinter.Entry(Rframe, validate='focusout', width=paramw,
            vcmd=lambda:self.plate.validCoordParam_R(self.Rparam_str.get()),
            textvariable=self.Rparam_str).pack()#grid(row=1,column=3)

        aframe=Tkinter.LabelFrame(pframe,text='a',relief='flat')
        aframe.grid(row=1,column=1)
        Tkinter.Entry(aframe, validate='focusout', width=paramw,
            vcmd=lambda:self.plate.validCoordParam_a(self.aparam_str.get()),
            textvariable=self.aparam_str).pack()#grid(row=1,column=3)
        

        #Info output
        self.info_str=Tkinter.StringVar(value='Red: 000  Blue: 000  Total: 0000')
        Tkinter.Label(frame2, textvariable=self.info_str).pack(anchor='w')
        Tkinter.Label(frame2, textvariable=self.file_str).pack(anchor='w')
        
        self.testinit()

    def toggleCoord(self):
        self.plate.toggleCoordShift()
        self.show()

    def testinit(self):
        #put some holes in the plate
        #self.load()
        self.show()

    def canvasclick(self, event):
        #Get holes that are within a few pixels of the mouse position
        items=self.canvas.find_overlapping(event.x - 2, event.y-2, event.x+2, event.y+2)
        items=filter(lambda a: 'hole' in self.canvas.gettags(a), items)
            
        if items:
            holeIDs=tuple([tag[1:] for i in items for tag in self.canvas.gettags(i) if tag[-1].isdigit()])
            
            HoleInfoDialog(self.parent, self.canvas, self.plate, self.getActiveSetup(), holeIDs)

    def invsetupen(self):
        import tkMessageBox
        tkMessageBox.showerror('Bad Setup','Not a valid setup.')

    def getActiveSetup(self):
        return "Setup "+self.setup_str.get()

    def validatesetupen(self):
        ret=self.plate.isValidSetup(self.getActiveSetup())
        return ret 

    def show(self):
        self.canvas.clear()
        self.info_str.set(self.plate.getInfo(self.getActiveSetup()))
        self.plate.draw(self.canvas, active_setup=self.getActiveSetup())
        
    def showRed(self):
        self.canvas.clear()
        self.info_str.set(self.plate.getInfo(self.getActiveSetup()))
        self.plate.draw(self.canvas,channel='armR',
                            active_setup=self.getActiveSetup())
    def showBlue(self):
        self.canvas.clear()
        self.info_str.set(self.plate.getInfo(self.getActiveSetup()))
        self.plate.draw(self.canvas,channel='armB',
                            active_setup=self.getActiveSetup())

    def makeRegions(self):
        self.plate.regionify(active_setup=self.getActiveSetup())
        self.show()

    def load(self):
        from tkFileDialog import askopenfilename
        from os.path import basename
        dir='/Users/one/Documents/Mario_research/plate_routing/Plates/'
        file=askopenfilename()

        self.plate.loadHoles(file)
        self.file_str.set(basename(file))
        self.show()
        
    def writeMap(self):
        dir='/Users/one/Documents/Mario_research/plate_routing/Plates/'
        self.plate.writeMapFile(dir, self.getActiveSetup())
        
    def makeImage(self):
        #The image canvas for drawing the plate to a file
        dir='/Users/one/Documents/Mario_research/plate_routing/Plates/'
        imgcanvas=imagecanvas.ImageCanvas(768, 768, 1.0, 1.0)
        self.plate.drawImage(imgcanvas, active_setup=self.getActiveSetup())
        imgcanvas.save(dir+self.file_str.get()+'_'+self.getActiveSetup()+'.bmp')

    def makeImageRed(self):
        #The image canvas for drawing the plate to a file
        dir='/Users/one/Documents/Mario_research/plate_routing/Plates/'
        imgcanvas=imagecanvas.ImageCanvas(768, 768, 1.0, 1.0)
        self.plate.drawImage(imgcanvas, channel='armR',
                            active_setup=self.getActiveSetup())
        imgcanvas.save(dir+self.file_str.get()+'_'+self.getActiveSetup()+'_red.bmp')

    def makeImageBlue(self):
        #The image canvas for drawing the plate to a file
        dir='/Users/one/Documents/Mario_research/plate_routing/Plates/'
        imgcanvas=imagecanvas.ImageCanvas(768, 768, 1.0, 1.0)
        self.plate.drawImage(imgcanvas, channel='armB',
                            active_setup=self.getActiveSetup())
        imgcanvas.save(dir+self.file_str.get()+'_'+self.getActiveSetup()+'_blue.bmp')
                            
    
if __name__ == "__main__":
    app = App(None)
    app.title('Hole Mapper')
    app.mainloop()
