def condense_cassette_assignemnts(cassettes):
    #Grab cassettes with available fibers
    non_full=[c for c in cassettes if c.n_avail > 0 and c.used > 0]
              
    to_check=list(non_full)
    to_check.sort(key= lambda x: x.n_avail)
    
    while to_check:
        
        trial=to_check.pop()
        
    
        #Try to reassign all holes to non full cassettes
        holes=list(trial.targets)
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
        first_higher_hole_ndx=len(sort_ndxs)
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


def get_setup_by_name(name):
    """return the setup object named name"""
    ...

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
    

    #Grab the cassettes
    #TODO: sort this out
    cassettes=setup.new_cassetts()
    
    #Grab all the setups & targets we should assign with
    assignwith_setups=map(get_setup_by_name, setup.assign_with)
    assignwith_targets=[t for s in assignwith_setups for t in s.targets]

    #TODO: Check that assignment requirements of other setup are compatible
    #TODO: make sure we've got enough fibers, etc
    #if setup.fibers_usable - setup.fibers_requested>0:

    #Reset all the assignments
    for t in setup.targets+assignwith_targets:
        t.reset_assignment()
    
    #Grab all skys and objects that don't have assignments
    unassigned_skys=[t for t in setup.targets+assignwith_targets
                       if t.is_sky and not t.is_assigned]
    unassigned_objs=[t for t in setup.targets+assignwith_targets
                       if t.is_target and not t.is_assigned]
                    
    #Grab targets with assignments and configure the cassettes
    assigned=[t for t in setup.targets+assign_with_targets if t.is_assigned]
    for t in assigned:
        print "some were assigned"
        cassettes.assign_fiber(t.fiber,t)

    #TODO: What about targets with preset usable cassette restrictions

    #Distribute sky fibers evenly over cassettes groups (e.g. color, slit)
    for setup_i in [setup_name]+assignwith_setups:
        #cassette_group is a list of disjoint lists of cassette names all
        # sharing the same color and slit
        skys=[t for t in setup_i.targets if t.is_sky and not t.is_assigned]
        for i, t in enumerate(skys):
            group=setup_i.cassette_groups[i % len(setup_i.cassette_groups)]
            t.assign_possible_cassettes_by_name(group)

    #While there are holes w/o an assigned cassette (groups don't count)
    while unassigned_skys:
        #Update cassette availability for each hole (a cassette may have filled)
        for t in unassigned_skys:
            #Get cassettes with correct slit and free fibers
            # n.b these are just cassette name strings
            possible_cassettes=[c.name for c in cassettes
                                if t.is_assignable(cassette=c) and c.n_avail >0]
            if not possible_cassettes:
                print 'Could not find a suitable cassette for {}'.format(t)
                import ipdb;ipdb.set_trace()
            #Set the cassettes that are usable for the hole
            #  no_add is true so we keep the distribution of sky fibers
            t.assign_possible_cassettes_by_name(possible_cassettes,
                                       update_with_intersection=True)

        #Get hole furthest from its cassettes and assign to nearest available
        unassigned_skys.sort(key=lambda t: t.plug_priority)
        t=unassigned_skys.pop()
        cassettes.assign_cassette(t.nearest_usable_cassette, t)


    #While there are holes w/o an assigned cassette (groups don't count)
    while unassigned_objs:
        #Update cassette availability for each hole (a cassette may have filled)
        for h in unassigned_objs:
            #Get cassettes with correct slit and free fibers
            # n.b these are just cassette name strings
            possible_cassettes=[c.name for c in cassettes
                                if t.is_assignable(cassette=c) and c.n_avail >0]
            if not possible_cassettes:
                print 'Could not find a suitable cassette for {}'.format(t)
                import ipdb;ipdb.set_trace()
            #Set the cassetes that are usable for the hole
            #  no_add is true so we keep the distribution of sky fibers
            t.assign_possible_cassettes_by_name(possible_cassettes,
                                       update_with_intersection=True)

        #Get hole furthest from its cassettes and assign to nearest available
        unassigned_objs.sort(key=lambda t: t.plug_priority)
        t=unassigned_objs.pop()
        cassettes.assign_cassette(t.nearest_usable_cassette, t)


    ####All targets have now been assigned to a cassette####

    #For each cassette assign fiber numbers with x coordinate of holes
    for c in cassettes:
        cassettes.map_fibers()
    
    #Compact the assignments (get rid of underutillized cassettes)
    condense_cassette_assignemnts(Cassette.left_only(cassettes))
    condense_cassette_assignemnts(Cassette.right_only(cassettes))
    
    #Rejigger the fibers
    rejigger_cassette_assignemnts(Cassette.left_only(cassettes))
    rejigger_cassette_assignemnts(Cassette.right_only(cassettes))
    
    #Remap fibers in c
    for c in cassettes.itervalues():
        c.map_fibers(remap=True)

    setup.cassette_config=cassettes
    for setup_i in assignwith_setups:
        #TODO: Remove?
        self.setups[s]['INFO']['ASSIGNEDWITH']=setup['INFO']['ASSIGNEDWITH']
        setup_i.cassette_config=cassettes

