'''
Created on Dec 12, 2009

@author: one
'''
from Hole import *
import ImageCanvas
from plateHoleInfo import plateHoleInfo
import operator
import Cassette

def distribute(x, min_x, max_x, min_sep):
    """
    Adjust x such that all x are min_space apart,
    near original positions, and within min_x & max_x
    """
    import numpy as np
    return np.linspace(min_x, max_x, len(x))


def condense_cassette_assignemnts(cassette_dict):
    #Grab cassettes with available fibers
    non_full=[c for c in cassette_dict.itervalues()
              if c.n_avail()>0 and c.used>0]
              
    to_check=list(non_full)
    to_check.sort(key= lambda x: x.n_avail())
    
    while to_check:
        
        trial=to_check.pop()
        
    
        #Try to reassign all holes to non full cassettes
        holes=list(trial.holes)
        for h in holes:
            #If hole can't be assigned then screw it
            if not h.isAssignable():
                break
            #Try assigning the hole to another tetris
            recomp_non_full=False
            for c in non_full:
                if h.isAssignable(cassette=c):
                    trial.unassign_hole(h)
                    c.assign_hole(h)
                    recomp_non_full=True
                    break
            if recomp_non_full:
                #Redetermine what is full
                recomp_non_full=False
                non_full=[c for c in non_full if c.n_avail()>0]
    
        #If we were emptied the cassette then don't add anything to it
        if trial.used == 0:
            try:
                non_full.remove(trial)
            except ValueError,e:
                #it is possible that trial filled up, was dropped from non_full
                # or something like that
                pass
    
        #Update sort of to check
        to_check.sort(key= lambda x: x.n_avail())

def rejigger_cassette_assignemnts(cassette_dict):
    """Go through the cassettes swapping holes to eliminate
    verticle excursions"""
    cassettes=cassette_dict.values()
    cassettes.sort(key=lambda c: c.pos[1])
    for i in range(len(cassettes)-1):
        cassette=cassettes[i]
        higer_cassettes=cassettes[i:]

        swappable_cassette_holes=[h for h in cassette.holes
                                  if h.isAssignable()]

        swappable_higher_cassette_holes=[h
                                         for c in higer_cassettes
                                         for h in c.holes
                                         if h.isAssignable(cassette=cassette)]
        if len(swappable_higher_cassette_holes) ==0:
            continue
        
        holes=swappable_cassette_holes+swappable_higher_cassette_holes
        holes.sort(key=operator.attrgetter('y'))
        #Find index of lowest hole not in the cassette
        sort_ndxs=[holes.index(h) for h in swappable_cassette_holes]
        for i in range(len(sort_ndxs)):
            if i not in sort_ndxs:
                first_higher_hole_ndx=i
                break
        #For holes not at start of sorted list
        for i in sort_ndxs:
            if i > first_higher_hole_ndx:
                low_hole=holes[i]
                #attempt exchange with lower holes
                for j in range(first_higher_hole_ndx, i):
                    #nb high cassette might be same
                    high_cassette=cassette_dict[holes[j].assigned_cassette()]
                    if high_cassette==cassette:
                        continue
                    if (holes[j].isAssignable(cassette=cassette) and
                        low_hole.isAssignable(cassette=high_cassette)):
                        #Unassign
                        high_cassette.unassign_hole(holes[j])
                        cassette.unassign_hole(low_hole)
                        #Assign
                        high_cassette.assign_hole(low_hole)
                        cassette.assign_hole(holes[j])
                        break



SCALE=14.25 #also change in plateHoleInfo.py

LABEL_MAX_Y=.7
MIN_LABEL_Y_SEP=0.05 #must be < 2*LABEL_MAX_Y/16

PROJ_PLATE_LABEL_Y=.95

class Plate(object):
    '''Class for fiber plug plate'''
    SCALE=SCALE
    RADIUS=1.0 # 14.25/Plate.SCALE
    LABEL_RADIUS=0.95*RADIUS
    SH_RADIUS=0.1875
    HOLE_R_MULT=1.25


    def __init__(self):
        #self.h=0.4039727532995173
        #x1,y1 = 0.4863742535097986, 0.19906175954231559
        #x2,y2 = 0.36245210964697655, 0.6497646036144594
        self.holeSet=set()
        self.setups={}
        self.plate_name=''
        self.doCoordShift=True
        self.coordShift_D=64.0
        self.coordShift_R=50.68
        self.coordShift_rm=13.21875
        self.coordShift_a=0.03

    def getHole(self, holeID):
        for h in self.holeSet:
            if h.hash == long(holeID):
                return h
        return None

    def getSetupsUsingHole(self, hole):
        ret=[]
        for k in self.setups:
            v=self.setups[k]
            if hole in v['unused_holes'] or hole in v['holes']:
                ret.append(k)
        return ret

    def getHoleInfo(self, holeID):
        """
        Returns a dictionary of information for hole
            corresponding to holeID. Valid keys are:'RA',
            'DEC','ID','MAGNITUDE','COLOR','SETUPS',
            'HOLEID', and 'TYPE'.
            An invalid holeID is an exception.
        """
        hole=self.getHole(holeID)
        if not hole:
            raise Exception('Invalid holeID')
        ret={'RA':hole.ra_string(),'DEC':hole.de_string(),
             'ID':hole['ID'],'MAGNITUDE':hole['MAGNITUDE'],
             'COLOR':hole['COLOR'],'TYPE':hole['TYPE'],
             'SETUPS':self.getSetupsUsingHole(hole),'HOLEID':holeID,
             'IDSTR':hole.idstr,'CUSTOM':hole['CUSTOM']}
        return ret

    def getChannelForHole(self, holeID, setupName):
        """ Returns the channel of a hole for a given setup.
            Returns '' for Holes without a channel. An invalid
            setup is an exception. An invalid holeID is an exception."""
        
        hole=self.getHole(holeID)
        if not hole:
            raise Exception('Invalid holeID')
        if setupName not in self.setups:
            raise Exception('Invalid setupName')
        
        ret=''

        if hole in self.setups[setupName]['holes']:
            color=hole.assigned_color()
            if color !=None:
                ret=color
        
        return ret
    
    def getFiberForHole(self, holeID, setupName):
        """
        Returns the Fiber which is mapped to a
        specified holeID. "None" is returned if
        there is no mapping. A nonexistent setup
        is an exception, as is an invalid holeID
        """
        hole=self.getHole(holeID)
        if not hole:
            raise Exception('Invalid holeID')
        if setupName not in self.setups:
            raise Exception('Invalid setupName')
        
        if hole['FIBER'] !='':
            return hole['FIBER']
        else:
            return 'None'

    def getSetupInfo(self,setupName):
        nr=0
        nb=0
        ns=0
        
        #TODO fix total calculation
        nt=len(self.holeSet)-len(self.getHolesNotInAnySetup())
        for s in self.setups:
            nt-=len(self.setups[s]['unused_holes'])

        if setupName in self.setups:
            setup=self.setups[setupName]
            nr=len([h for h in setup['holes'] if 'R' in h['FIBER']])
            nb=len([h for h in setup['holes'] if 'B' in h['FIBER']])
            ns=len(setup['holes'])
        ret='Red: %03d  Blue: %03d  Setup: %03d  Total: %04d'%(nr,nb,ns,nt)
        ret=ret+' {} Setups'.format(len(self.setups))
        return ret

    def getHolesNotInAnySetup(self):
        otherholes=[]
        #gather all the holes not in any setup
        for h in self.holeSet:
            flag=1
            for s in self.setups:
                if (h in self.setups[s]['unused_holes'] or
                    h in self.setups[s]['holes']):
                    flag=0
                if flag == 0:
                    break
            if flag:
                otherholes.append(h)
        return otherholes
    
    def initializeSetup(self, setupName):
        """Initializes a setup dictionary with name 
           setupName"""
        #if setupName is not of the form "Setup #" raise an exception
        
        setup={'plate':self.plate_name, 
               'setup':setupName,
               'unused_holes':[],
               'channels':{},
               'groups':[]}
        return setup
    
    @staticmethod
    def initializeGroup( fiberBundle, holes, region, side, channel):
        return {'fiber_group':fiberBundle, 
                'holes':holes,
                'region':region,
                'side':side, 
                'path':[],
                'channel':channel}

    def load(self,file):
        ''' Routine to load holes from a file 

        File should have all the holes on the plate
        separated into groups specifying the setup number.
        valid lines are of format x y z diam type arbit_fiber channel'''

        self.clear()
        
        self.plateHoleInfo=plateHoleInfo(file)
        self.plate_name=self.plateHoleInfo.name
        curr_setup=''
        
        self.holeSet=self.plateHoleInfo.holeSet
        self.setups=self.plateHoleInfo.setups
        
        #Add the SH to the global set
        self.holeSet.add(Hole(0.0, 0.0, 0.0, Plate.SH_RADIUS/Plate.SCALE,
                              idstr='Shack-Hartman'))
  
    def clear(self):
        self.setups={}
        self.holeSet=set()

    def regionify(self, active_setup='Setup 1'):
        if active_setup in self.setups:
            self.assignFibers(self.setups[active_setup])

    def writeMapFile(self, out_dir, active_setup):
        if active_setup in self.setups:
            ofile=''.join([out_dir,self.plate_name,'_',active_setup,'.map'])
            print 'Writing mapfile:'+ofile
            with open( ofile, "w" ) as fout:
                fout.write(''.join(['Code Version: Nov 13\n',
                                    self.plate_name,'\n']))
                for l in self.setups[active_setup]['setupNfo']:
                    fout.write(l)
                cassettes=self.setups[active_setup]['cassetteConfig'].values()
                for c in cassettes:
                    for h in c.holes:
                        fout.write(h.maprecord()+'\n')

    def toggleCoordShift(self):
        self.doCoordShift = not self.doCoordShift
        return self.doCoordShift

    def assignFibers(self, setup):
        """
        load holes from file, by default assume all are on same slit and no pattern
        
        
        break holes into sets based on slit requirements
        
        get cassets for each set of holes based on specification
        compute number of cassets needed for each set based on fiber pattern for
        
        
        for each set of holes assign holes to nearest suitable casset (with free fibers)
        assign holes in order of increasing closeness to suitable, non-full cassets
        compute clossness as sum of distances to relevant casset vertices
        
        Consider swapping after algorithm by computing convex hull for each casset and
        finding interlopers then swapping them
        
        
        #Consider making each hole have a number of targets associated with it
        # the targets would contain the fiber and target info instead of the hole object
        # and the hole could be associated with multiple targets (1 per setup)
        
        All science & sky holes are loaded, holes with file-specifed fibers or
        arm/cassette/fiberno and slit constrains are set
        Cassette slit widths, usable fibers are set. slit widths must be assigned
        beforehand to prevent a sparse configuration from happening e.g. all but 16
        furthest are same slit assign 16 furthest -> no available cassettes for rest
        
        #    Assign holes without channel to r or b channel
        #        get holes without channel
        #        break holes into groups based on required slit
        #        get number of available fibers on each channel, given slit and filter reqs
        #        if all fit on one channel, do it, otherwise divide randomly??

        #Barring preassignment, we would like to distribute sky fibers evenly over
        #cassette groups, where a group is a set of cassettes with same color & slit
        for i,h in enumerate(skys):
            h.assignment.cassette=cassette_groups[i mod len(cassette_groups)]

        for each hole w/o preassigned fiber:
            get cassets available to hole (cassets with correct slit and free fibers)
            compute distance to each cassette vertex & sum for available vertices
        
        sort science holes by distance metric
        
        while there are science holes w/o assigned cassette:
            get first hole
            get cassets available to hole (cassets with correct slit and free fibers)
            assign to nearest available casset
            update cassette availability for each hole (a cassette may have filled)
            recompute distance metric for each hole
            sort remaining holes by distance metric
            
        swap between cassettes as needed
        
        for each cassette
            assign fiber numbers with x coordinate of holes
        """
        
        #Grab all skys and objects that don't have assignments
        unassigned_skys=[h for h in setup['holes'] if
                         h.isSky() and not h.isAssigned()]
        unassigned_objs=[h for h in setup['holes'] if
                        h.isObject() and not h.isAssigned()]
                        
        
        #Grab the cassettes and cassette groups
        cassettes=self.plateHoleInfo.cassettes_for_setup(setup['setup'])
        cassette_groups=self.plateHoleInfo.cassette_groups_for_setup(setup['setup'])
        
        #Distribute sky fibers evenly over groups of cassettes with
        # same color & slit, don't bother factoring in preassigned skys for now
        for i, h in enumerate(unassigned_skys):
            group=cassette_groups[i % len(cassette_groups)]
            h.assign_possible_cassette(group)

        #While there are holes w/o an assigned cassette (groups don't count)
        while len(unassigned_skys) > 0:
            #Update cassette availability for each hole (a cassette may have filled)
            for h in unassigned_skys:
                #Get cassettes with correct slit and free fibers
                # n.b these are just cassette name strings
                possible_cassettes=self.plateHoleInfo.available_cassettes(h,
                                                    setup['setup'])
                if len(possible_cassettes)<1:
                    import pdb;pdb.set_trace()
                #Set the cassetes that are usable for the hole
                #  no_add is true so we keep the distribution of sky fibers
                h.assign_possible_cassette(possible_cassettes,
                                           update_with_intersection=True)

            #Sort holes by their distance from cassettes
            unassigned_skys.sort(key=lambda h: h.plug_priority())

            #Get hole furthest from its cassettes
            h=unassigned_skys.pop()

            #Assign to nearest available cassette
            cassettes[h.nearest_usable_cassette()].assign_hole(h)

        #List of holes needing assignments
        holes_to_assign=unassigned_objs

        #While there are holes w/o an assigned cassette (groups don't count)
        while len(holes_to_assign) > 0:
            #Update cassette availability for each hole (a cassette may have filled)
            for h in holes_to_assign:
                #Get cassettes with correct slit and free fibers
                # n.b these are just cassette name strings
                possible_cassettes=self.plateHoleInfo.available_cassettes(h,
                                                    setup['setup'])
                if len(possible_cassettes)<1:
                    import pdb;pdb.set_trace()
                #Set the cassetes that are usable for the hole
                #  no_add is true so we keep the distribution of sky fibers
                h.assign_possible_cassette(possible_cassettes,
                                           update_with_intersection=True)

            #Sort holes by their distance from cassettes
            holes_to_assign.sort(key=lambda h: h.plug_priority())

            #Get hole furthest from its cassettes
            h=holes_to_assign.pop()

            #Assign to nearest available cassette
            cassettes[h.nearest_usable_cassette()].assign_hole(h)


        ####All holes have now been assigned to a cassette####

        #For each cassette assign fiber numbers with x coordinate of holes
        for c in cassettes.itervalues():
            c.map_fibers()
        
        #Compact the assignments (get rid of underutillized cassettes)
        condense_cassette_assignemnts(Cassette.left_only(cassettes))
        condense_cassette_assignemnts(Cassette.right_only(cassettes))
        
        #Rejigger the fibers
        rejigger_cassette_assignemnts(Cassette.left_only(cassettes))
        rejigger_cassette_assignemnts(Cassette.right_only(cassettes))
        
        #Remap fibers in c
        for c in cassettes.itervalues():
            c.map_fibers(remap=True)

        setup['cassetteConfig']=cassettes
        
    def drawHole(self, hole, canvas, color=None, fcolor='White', radmult=1.0, drawimage=0):
       
        
        pos=self.plateCoordShift(hole.position())
            
        hashtag=".%i"%hole.hash
        if drawimage:
                canvas.drawCircle( pos, hole.radius*radmult, outline=color, fill=fcolor)
        else:
            if canvas.find_withtag(hashtag):
                tmp=list(pos)
                tmp.append(hole.hash)
                print tmp
                for k,v in hole.items():
                    print k,v
                import pdb;pdb.set_trace()
                print "drawing dupe in Dark Green @ (%f,%f) ID:%i"%tuple(tmp)
                fcolor='DarkGreen'
            canvas.drawCircle( pos, hole.radius*radmult, 
                               outline=color, fill=fcolor, tags=('hole',hashtag),
                               activefill='Green',activeoutline='Green',
                               disabledfill='Orange',disabledoutline='Orange')


    def plateCoordShift(self, (xin, yin), force=False):
        """ Shifts x and y to their new positions in scaled space,
            if self.doCoordShift is True or force is set to True.
            out=in otherwise"""
        if (not self.doCoordShift and
            not force or (xin==0.0 and yin==0.0)):
            return (xin,yin)
        else:
            D=self.coordShift_D
            a=self.coordShift_a
            R=self.coordShift_R
            rm=self.coordShift_rm
            
            x=xin*Plate.SCALE
            y=yin*Plate.SCALE
            r=math.hypot(x, y)
            #psi = angle clockwise from vertical
            #psi=90.0 - math.atan2(y,x)
            cpsi=y/r
            spsi=x/r
            d=math.sqrt(R**2 - r**2) - math.sqrt(R**2 - rm**2)
            dr=d*r/(D+d)
            
            rp=(r-dr)*(1.0+a*cpsi)
            xp=rp*spsi
            yp=rp*cpsi
            return (xp/Plate.SCALE, yp/Plate.SCALE)

    def draw(self, canvas, active_setup=None, channel='all'):
        
        #Make a circle of appropriate size in the window
        canvas.drawCircle( (0,0) , Plate.RADIUS)
        
        if active_setup and active_setup in self.setups:
            #the active setup
            setup=self.setups[active_setup]
            
            inactiveHoles=self.holeSet.difference(setup['unused_holes'])
            inactiveHoles.difference_update(setup['holes'])
            
            #Draw the holes that aren't in the current setup
            for h in inactiveHoles:
                self.drawHole(h, canvas)
            
            #If holes in setup have been grouped then draw the groups
            # otherwise draw them according to their channel
            if 'cassetteConfig' in setup:
                self._draw_with_assignements(setup, channel, canvas)
            else:
                self._draw_without_assignements(setup, channel, canvas)
            
            #Draw the guide and acquisition holes in color
            for h in setup['unused_holes']:
                self.drawHole(h, canvas, color='Green')
        else:
            for h in self.holeSet:
                self.drawHole(h, canvas)

    def _draw_with_assignements(self, setup, channel, canvas,
                                lblcolor='black', drawimage=False):
        """Does not draw holes for color if not selected"""
        if channel in ['armB', 'BLUE', 'blue']:
            drawred=False
            drawblue=True
        elif channel in ['armR', 'RED', 'red']:
            drawblue=False
            drawred=True
        else:
            drawred=True
            drawblue=True
        
        #List of cassette labels and first hole positions
        labeldata=[]
        
        #Draw all the cassettes
        for cassette in setup['cassetteConfig'].itervalues():
            #canvas.drawCircle(cassette.pos, .02, outline='pink', fill='pink')
            if cassette.used==0:
                continue
            if drawred and cassette.color()=='red':
                #Draw the cassette
                self.drawCassette(cassette, canvas, drawimage=drawimage)
                #Grab the first hole position
                start_pos=cassette.first_hole().position()
                #Grab the label text
                label=cassette.label()
                #Add the label, color, and start pos to the pot
                labeldata.append(('red', start_pos, label, cassette.onRight()))
            if drawblue and cassette.color()=='blue':
                #Draw the cassette
                self.drawCassette(cassette, canvas, drawimage=drawimage)
                #Grab the first hole position
                start_pos=cassette.first_hole().position()
                #Grab the label text
                label=cassette.label()
                #Add the label, color, and start pos to the pot
                labeldata.append(('blue', start_pos, label, cassette.onRight()))
        
        labeldata.sort(key=lambda x:x[1][1])
        
        #Figure out where all the text labels should go
        labelpos=range(len(labeldata))
        
        #Left side positions
        lefts=filter(lambda i:labeldata[i][3]==False, range(len(labeldata)))
        y=distribute([labeldata[i][1][1] for i in lefts],
                     -LABEL_MAX_Y, LABEL_MAX_Y, MIN_LABEL_Y_SEP)
        x=(Plate.LABEL_RADIUS**2 - y**2)
        for i in range(len(lefts)):
            labelpos[lefts[i]]=[x[i], y[i]]

        #Right side positions
        rights=filter(lambda i:labeldata[i][3]==True, range(len(labeldata)))
        y=distribute([labeldata[i][1][1] for i in rights],
                     -LABEL_MAX_Y, LABEL_MAX_Y, MIN_LABEL_Y_SEP)
        x=-(Plate.LABEL_RADIUS**2 - y**2)
        for i in range(len(rights)):
            labelpos[rights[i]]=[x[i], y[i]]
        
        #Kludge for image cavas
        if isinstance(canvas, ImageCanvas.ImageCanvas):
            for i in range(len(labeldata)):
                label=labeldata[2]
                side=labeldata
                if not side: #on right
                    labelpos[i][0]-=canvas.getTextSize(label)
                else:
                    labelpos[i][0]-=2*canvas.getTextSize(label)
        
        #Draw the labels
        for i in xrange(len(labeldata)):
            color,hpos,label,side=labeldata[i]
            tpos=labelpos[i]

            #Draw the label
            canvas.drawText(tpos, label, color=lblcolor)

            #Connect label to cassette path
            canvas.drawLine(tpos, self.plateCoordShift(hpos),
                            fill=color, dashing=1)
    
    def _draw_without_assignements(self, setup, channel, canvas,
                                   drawimage=False, radmult=1.0):
        if channel == 'all':
            bluecolor='blue'
            redcolor='red'
            nonecolor='purple'
        elif channel in ['armB', 'BLUE', 'blue']:
            bluecolor='blue'
            redcolor=None
            nonecolor=None
        else:
            bluecolor=None
            redcolor='red'
            nonecolor=None

        for h in setup['holes']:
            hcolor=h.assigned_color()
            if hcolor == 'blue':
                if drawimage:
                    self.drawHole(h, canvas, color=bluecolor,
                                  drawimage=drawimage,
                                  fcolor=bluecolor,
                                  radmult=radmult)
                else:
                    self.drawHole(h, canvas, color=bluecolor,
                                  radmult=radmult)
            elif hcolor =='red':
                if drawimage:
                    self.drawHole(h, canvas, color=redcolor,
                                  drawimage=drawimage,
                                  fcolor=redcolor,
                                  radmult=radmult)
                else:
                    self.drawHole(h, canvas, color=redcolor,
                                  radmult=radmult)
            else:
                if drawimage:
                    self.drawHole(h, canvas, color=nonecolor,
                                  drawimage=drawimage,
                                  fcolor=nonecolor,
                                  radmult=radmult)
                else:
                    self.drawHole(h, canvas, color=nonecolor,
                                  radmult=radmult)

    def drawImage(self, canvas, active_setup=None, channel='all',radmult=1.25):
        if active_setup and active_setup in self.setups:
            #the active setup
            setup=self.setups[active_setup]

            #Draw the plate name and active setup
            canvas.drawText((0,PROJ_PLATE_LABEL_Y), self.plate_name,
                            color='White',center=0)
            canvas.drawText((0,PROJ_PLATE_LABEL_Y-.05), active_setup,
                            color='White',center=0)

            if 'cassetteConfig' in setup:
                self._draw_with_assignements(setup, channel, canvas,
                                             drawimage=True,
                                             lblcolor='white')
            else:
                self._draw_without_assignements(setup, channel, canvas,
                                                drawimage=True, radmult=radmult)

            for h in setup['unused_holes']:
                self.drawHole(h, canvas,color='Yellow',fcolor='Yellow',
                              radmult=radmult,drawimage=True)

            sh_and_std=[h for h in self.holeSet if
                        h.idstr=='Shack-Hartman' or h['MATTFIB']=='R-01-17']
            for h in sh_and_std:
                self.drawHole(h, canvas,color='Magenta',fcolor='Magenta',
                              radmult=radmult,drawimage=True)


            #Draw little white dots where all the other holes are
            inactiveHoles=self.holeSet.difference(setup['unused_holes'])
            
            if channel=='all':
                inactiveHoles.difference_update(setup['holes'])
            elif channel=='armR':
                redholes=[h for h in setup['holes'] if 'R' in h['FIBER']]
                inactiveHoles.difference_update(redholes)
            elif channel=='armB':
                blueholes=[h for h in setup['holes'] if 'B' in h['FIBER']]
                inactiveHoles.difference_update(blueholes)
            else:
                raise Exception('Channel has invalid value:'+channel)

            for h in inactiveHoles:
                pos=self.plateCoordShift(h.position())    
                canvas.drawSquare(pos,h.radius/3,fill='White',outline='White')
    
    def drawCassette(self, cassette, canvas, radmult=1.0, drawimage=False):
        color=cassette.color()
        
        if cassette.used==0:
            return
        
        pluscrosscolor='Lime'
        #Draw an x across the first hole
        x,y=self.plateCoordShift(cassette.first_hole().position())
        radius=2*0.08675*radmult/Plate.SCALE
        canvas.drawLine((x-radius,y+radius),(x+radius,y-radius),
                        fill=pluscrosscolor)
        canvas.drawLine((x-radius,y-radius),(x+radius,y+radius),
                        fill=pluscrosscolor)
        
        #Draw a + over the last hole
        x,y=self.plateCoordShift(cassette.first_hole().position())
        radius=1.41*2*0.08675*radmult/Plate.SCALE
        canvas.drawLine((x-radius,y),(x+radius,y), fill=pluscrosscolor)
        canvas.drawLine((x,y-radius),(x,y+radius), fill=pluscrosscolor)
        
        holes=cassette.ordered_holes()

        #Draw the holes in the cassette
        for h in holes:
            self.drawHole(h, canvas, color=color, fcolor=color,radmult=radmult,drawimage=drawimage)

        if cassette.used==1:
            return

        #Draw the paths between each of the holes
        for i in range(len(holes)-1):
            p0=holes[i].position()
            p1=holes[i+1].position()
            canvas.drawLine(self.plateCoordShift(p0), self.plateCoordShift(p1),
                            fill=color)
        
    def setCoordShiftD(self, D):
        if self.isValidCoordParam_D(D):
            self.coordShift_D=float(D)
        else:
            raise ValueError()
    
    def setCoordShiftR(self, R):
        if self.isValidCoordParam_D(R):
            self.coordShift_R=float(R)
        else:
            raise ValueError()
    
    def setCoordShiftrm(self, rm):
        if self.isValidCoordParam_rm(rm):
            self.coordShift_rm=float(rm)
        else:
            raise ValueError()
    
    def setCoordShifta(self, a):
        if self.isValidCoordParam_D(a):
            self.coordShift_a=float(a)
        else:
            raise ValueError()
    
    def isValidCoordParam_D(self, x):
        if type(x) in [int,long,float]:
            return float(x) > 0.0
        elif type(x) is str:
            try: 
                float(x)
                return float(x) > 0.0
            except ValueError:
                return False
        else:
            return False
        
    def isValidCoordParam_R(self, x):
        if type(x) in [int,long,float]:
            return float(x)**2-self.coordShift_rm**2 >= 0.0 and float(x) > 0.0
        elif type(x) is str:
            try: 
                return float(x)**2-self.coordShift_rm**2 >= 0.0 and float(x) > 0.0
            except ValueError:
                return False
        else:
            return False
        
    def isValidCoordParam_rm(self, x):
        if type(x) in [int,long,float]:
            return self.coordShift_R**2-float(x)**2 >= 0.0 and float(x) > 0.0
        elif type(x) is str:
            try: 
                return self.coordShift_R**2-float(x)**2 >= 0.0 and float(x) > 0.0
            except ValueError:
                return False
        else:
            return False
        
    def isValidCoordParam_a(self, x):
        if type(x) in [int,long,float]:
            return True
        elif type(x) is str:
            try: 
                float(x)
                return True
            except ValueError:
                return False
        else:
            return False

    def isValidSetup(self,s):
        ret=True
        if self.setups:
            ret=s in self.setups
        return ret
