
DEFAULT_FOCUS=280.0

FILTER_NAMES=['BK7']
SLIT_NAMES=['180 um','125 um','98 um','75 um','58 um','45 um']
MODE_NAMES=['HiRes','LoRes']
HIRES_MODE='hires'



REQUIRED_PLUGGED_SECTION_KEYS=['fiber', 'id', 'ra', 'dec', 'epoch', 'type',
                               'priority','pm_ra','pm_dec']



class SetupConfig(object):
    def __init__(self, side=None, mode=None, slit=None, loel=None,
                 hiaz=None, hiel=None, focus=None,
                 binning=None, filter=None, n_amps=None, speed=None):
        
        self.side=side
    
        self.mode=mode
        assert self.mode in MODE_NAMES
        
        self.slit=slit
        assert slit in SLIT_NAMES

        self.loel=loel

        self.hiaz=hiaz
        self.hiel=hiel

        self.focus=focus

        self.binning=binning
        self.speed=speed
        self.n_amps=n_amps

        self.filter=filter
        assert filter in FILTER_NAMES
    

    @property
    def info(self):
        c=self
        r={'binning_{}'.format(self.side):'{} ({})'.format(c.binning, c.n_amps),
           'filter_{}'.format(self.side):c.filter,
           'focus_{}'.format(self.side):str(c.focus),
           'hiaz_{}'.format(self.side):str(c.hiaz),
           'hiel_{}'.format(self.side):str(c.hiel),
           'loel_{}'.format(self.side):str(c.loel),
           'slide_{}'.format(self.side):c.mode, #LoRes or HiRes
           'slit_{}'.format(self.side):c.slit,
           'speed_{}'.format(self.side):c.speed}
        return r

class Setup(object):
    def __init__(self, setupfile, fieldname, configR, configB, assignwith=[]):
        
        ok_fibers_r=configR.pop('tetris_config') #boolean 16 tuple,fibers to use
        ok_fibers_b=configB.pop('tetris_config') #boolean 16 tuple,fibers to use
        self.b=configB
        selb.r=configR
        self.name=os.path.basename(setupfile)
        self.plate=databasegetter.get_plate_for_field(fieldname)
        self.field=self.plate.fields[fieldname]

        self.assign_with=map(databasegetter.get_setup, assignwith) #setups
        
        self.cassette_config=CassetteConfig(usableR=ok_fibers_r,
                                            usableB=ok_fibers_b)

    @property
    def uses_r_side(self):
        """ Returns true iff the setup need to use the r side """
        return True

    @property
    def uses_b_side(self):
        """ Returns true iff the setup need to use the B side """
        return True

    @property
    def info(self):
        ret=self.field.info.copy()
    
        addit={'assign_with':', '.join(name for name in self.assigned_with),
               'plate':self.plate.name}
        
        addit.update(self.r.info)
        addit.update(self.b.info)
    
        for k in addit:
            assert k not in ret

        ret.update(addit)
        
        return ret
    
    @property
    def uses_b_side(self):
        """ returns true iff targets have been assigned to b side"""
        for t in self.field.skys+self.field.targets:
            if t.fiber and t.fiber.color=='b':
                return True
        return False

    @property
    def uses_r_side(self):
        """ returns true iff targets have been assigned to r side"""
        for t in self.field.skys+self.field.targets:
            if t.fiber and t.fiber.color=='r':
                return True
        return False

    def writeplist(self, dir='./'):
        filename='{}_{}.m2fs'.format(self.plate.name,self.name)
        import plistlib
        #TODO: Finish
        c={}
        if self.uses_b_side:
            c.update(self.configB.info)
        if self.uses_r_side:
            c.update(self.configR.info)

        for k in config.keys():
            if config[k]==None or config[k]=='None':
                config.pop(k)
        plistlib.writeplist(config, os.path.join(dir,filename))
        
    def writemap(self, dir='./'):
        """
        [setup]
        field info + setup config info
        [setup:plugged]
        header
        records
        [setup:unplugged]
        header
        records
        """
        filename='{}_{}.fibermap'.format(self.plate.name,self.name)
    
        with open(os.path.join(dir, filename),'w') as fp:
    
            fp.write("[setup]\n")

            recs=_format_dict_nicely(self.info)
            for r in recs:
                fp.write(r+'\n')
    
            fp.write("[assignemnts]\n")
            #Create dictlist for all fibers
            #Grab fibers
            def dicter(fiber):
                if not f.target:
                    return {'fiber':fiber.name,'id':'unplugged'}
                elif f.target not in setup.targets:
                    return {'fiber':fiber.name,'id':'unassigned'}
                else:
                    return fiber.target.dictlist
            
            dl=[dicter(f) for f in setup.cassette_config.fibers]
            recs=_dictlist_to_records(dl, col_first=REQUIRED_PLUGGED_SECTION_KEYS)
            
            fp.write("[guides]\n")
            
#            target record for each guide/acquisition

            fp.write("[unused]\n")
#            target record for any targets not on plate on unassigned


    def write(self,dir='./'):
        """ Call to write the outputs after calling assign"""
        self.writemap(dir=dir)
        self.writeplist(dir=dir)
        for s in self.assign_with:
            s.writemap(dir=dir)
            s.writeplist(dir=dir)

    def assign(self):
        
        #Field targets and skys do not overlab with any guides
        #or acquisitions in any setups, because such cases were culled when
        #creating the plate
        
        try:
            func=get_custom_usable_cassette_func(self.name)
        except NameError:
            func=usable_cassette
        
        to_assign=func(self, self.assign_with)
        _assign_fibers(self.cassette_config, to_assign)


def usable_cassette(setup, assign_with=[]):
    to_assign=setup.field.skys+setup.field.targets
    
    to_assign_with=[t for s in assign_with
                      for t in s.field.skys+s.field.targets]
    
    if not to_assign_with:
        if len(to_assign) <= self.cassette_config.n_r_usable:
            #put all on one side by setting
            for t in to_assign:
                t._preset_usable_cassette_names=set(RED_CASSETTE_NAMES)
        elif len(to_assign) <= self.cassette_config.n_b_usable:
            for t in to_assign:
                t._preset_usable_cassette_names=set(BLUE_CASSETTE_NAMES)
        else:
            for t in self.field.targets:
                t._preset_usable_cassette_names=set(CASSETTE_NAMES)
            for i, t in enumerate(self.field.skys):
                if i % 2:
                    t._preset_usable_cassette_names=set(RED_CASSETTE_NAMES)
                else:
                    t._preset_usable_cassette_names=set(BLUE_CASSETTE_NAMES)
    else:
        #Assume we are distributing everything evenly
        to_assign+=to_assign_with
        for t in (t for t in to_assign if t.type==TARGET_TYPE):
            t._preset_usable_cassette_names=set(CASSETTE_NAMES)
        for i, t in enumerate(t for t in to_assign if t.type==SKY_TYPE):
            if i % 2:
                t._preset_usable_cassette_names=set(RED_CASSETTE_NAMES)
            else:
                t._preset_usable_cassette_names=set(BLUE_CASSETTE_NAMES)

    return to_assign

def _assign_fibers(cassettes, targets):
    """
    
    cassettes should be a cassettesconfig 
    
        assign_with may be list of setups to perform assignment with
    if none, assignwith from the setup will be used
    
    
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
    

    #Reset all the assignments
    cassettes.reset()
    for t in to_assign:
        t.reset_assignment()
    
    #Grab all skys and objects that don't have assignments
    unassigned_skys=[t for t in to_assign
                     if t.is_sky and not t.is_assigned]
    unassigned_objs=[t for t in to_assign
                     if t.is_target and not t.is_assigned]
                    
    #Grab targets with assignments and configure the cassettes
    assigned=[t for t in to_assign if t.is_assigned]
    for t in assigned:
        print "some were assigned"
        cassettes.assign(t, t.fiber.cassette)

    #All targets must have possible_cassettes_names set

    #TODO: What about targets with preset usable cassette restrictions


    #While there are holes w/o an assigned cassette (groups don't count)
    while unassigned_skys:
        #Update cassette availability for each hole (a cassette may have filled)
        for t in unassigned_skys:
            #Get cassettes with correct slit and free fibers
            # n.b these are just cassette name strings
            possible_cassettes=[c.name for c in cassettes
                                if t.is_assignable(cassette=c) and
                                c.n_avail >0]
            if not possible_cassettes:
                print 'Could not find a suitable cassette for {}'.format(t)
                import ipdb;ipdb.set_trace()
            #Set the cassettes that are usable for the hole
            #  no_add is true so we keep the distribution of sky fibers
            t.set_possible_cassettes_by_name(possible_cassettes,
                                       update_with_intersection=True)

        #Get hole furthest from its cassettes and assign to nearest available
        unassigned_skys.sort(key=lambda t: t.plug_priority)
        t=unassigned_skys.pop()
        cassettes.assign(t, t.nearest_usable_cassette)


    #While there are holes w/o an assigned cassette (groups don't count)
    while unassigned_objs:
        #Update cassette availability for each hole (a cassette may have filled)
        for h in unassigned_objs:
            #Get cassettes with correct slit and free fibers
            # n.b these are just cassette name strings
            possible_cassettes=[c.name for c in cassettes
                                if t.is_assignable(cassette=c) and
                                c.n_avail >0]
            if not possible_cassettes:
                print 'Could not find a suitable cassette for {}'.format(t)
                import ipdb;ipdb.set_trace()
            #Set the cassetes that are usable for the hole
            #  no_add is true so we keep the distribution of sky fibers
            t.set_possible_cassettes_by_name(possible_cassettes,
                                       update_with_intersection=True)

        #Get hole furthest from its cassettes and assign to nearest available
        unassigned_objs.sort(key=lambda t: t.plug_priority)
        t=unassigned_objs.pop()
        cassettes.assign_cassette(t.nearest_usable_cassette, t)


    ####All targets have now been assigned to a cassette####

    #For each cassette assign fiber numbers with x coordinate of holes
    cassettes.map()
    
    #Compact the assignments (get rid of underutillized cassettes)
    cassettes.condense()
    
    #Rejigger the fibers
    cassettes.rejigger()
    
    #Remap fibers
    cassettes.map(remap=True)



