import operator
from cassettes import CASSETTE_NAMES, RED_CASSETTE_NAMES, BLUE_CASSETTE_NAMES
from graphcollide import build_overlap_graph_cartesian
from logger import getLogger
_log=getLogger('assign')

def assign(setups):
    """
    setups to assign together 
    and
    constraints such as
    which spectrograph to assign to
    """
    print "Assigning {}".format([s.name for s in setups])
    #Field targets and skys do not overlab with any guides
    #or acquisitions in any setups, because such cases were culled when
    #creating the plate
    
    for s in setups: s.set_assign_with(setups)
    
    #define which targets in each setup are allowed to go into which cassette
    _configure_possible_cassettes_names(setups)

    #Do the assignment
    _assign_fibers(setups)

def _configure_possible_cassettes_names(setups):
    """
    if single setup with fewer targets than fibers on a side:
        set usable cassettes to that side only
    
    if single setup with more targets than fibers on a side:
        assign across both sides

    if two with incompatible usable fiber patterns:
        set one to b and the other to r
        
    if two where either requests to be alone (e.g. assign_to=R):
        set one to b and the other to r
        
    else if two:
        assign across both sides
    
    if more than two:
        raise exception if incompatible instrument configurations
        assign across both sides
    """
    
    if len(setups)==1:
        setup=setups[0]
        n_b_avail=setup.cassette_config.n_b_usable
        n_r_avail=setup.cassette_config.n_r_usable
        n_needed=len(setup.field.skys+setup.field.targets)
        if (n_needed<= max(n_b_avail, n_r_avail) or
            setup.assign_to=='single'):
            if n_needed<=n_r_avail:
                _log.info('Assigning all of single to R')
                setup.set_assigning_to(red=True)
                for t in setup.field.skys+setup.field.targets:
                    t.set_possible_cassettes(RED_CASSETTE_NAMES)
            else:
                _log.info('Assigning all of single to B')
                setup.set_assigning_to(blue=True)
                for t in setup.field.skys+setup.field.targets:
                    t.set_possible_cassettes(BLUE_CASSETTE_NAMES)
        else:
            _log.info('Assigning all of single to both')
            setup.set_assigning_to(both=True)
            for t in setup.field.skys+setup.field.targets:
                t.set_possible_cassettes(CASSETTE_NAMES)

    elif len(setups)==2: #two setups
        #Consider adding a constraing/warning/test for case where user
        # specifies a side
#        if (setups[0].assign_to in ['r','b'] and
#            setups[0].assign_to==setups[1].assign_to)

        incompatible=(setups[0].config.r.active_fibers !=
                      setups[1].config.r.active_fibers or
                      setups[0].config.b.active_fibers !=
                      setups[1].config.b.active_fibers)
        if (incompatible or
            setups[0].assign_to=='single' or
            setups[1].assign_to=='single'): #stick one on R and one on B
            _log.info('Assigning 2 to seperate spectrographs')
            for t in setups[0].field.skys+setups[0].field.targets:
                t.set_possible_cassettes(BLUE_CASSETTE_NAMES)
            setups[0].set_assigning_to(blue=True)
            setups[0].config.r.active_fibers=setups[1].config.r.active_fibers
            for t in setups[1].field.skys+setups[1].field.targets:
                t.set_possible_cassettes(RED_CASSETTE_NAMES)
            setups[1].config.b.active_fibers=setups[0].config.b.active_fibers
            setups[1].set_assigning_to(red=True)
        else:
            _log.info('Assigning 2 to both')
            for s in setups:
                s.set_assigning_to(both=True)
                for t in s.field.skys+s.field.targets:
                    t.set_possible_cassettes(CASSETTE_NAMES)

    else: # more than 2 setups
        #make sure all are fiber compatible (e.g. all to odds, all to evens, etc)
        _log.info('Assigning > 2')
        _log.warn('Assigning > 2 setups support is spotty if you want anything '
                  'more than plane jane setups together.')
        for s in setups[1:]:
            s.set_assigning_to(both=True)
            if (s.config.r.active_fibers != setups[0].config.r.active_fibers or
                s.config.b.active_fibers != setups[0].config.b.active_fibers):
                raise AssignmentConstraintError("Setups do not all use the "
                                                "same set of active fibers")
        
        #Set all to use any
        for s in setups:
            for t in s.field.skys+s.field.targets:
                t.set_possible_cassettes(CASSETTE_NAMES)
    


def _assign_fibers(setups):
    """
    
    cassettes should be a cassettesconfig, targets a list of target
    
    
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
    
    #Get all the targets we are to assign
    to_assign=[t for s in setups for t in s.to_assign]

    #Filter out targets which can't be plugged simultaneously
    to_assign=_filter_for_pluggability(to_assign)
    
    #Reset all the assignments
    for s in setups:
        s.reset()
    
    cassettes=setups[0].cassette_config
    
    #Grab all skys and objects that don't have assignments
    unassigned_skys=[t for t in to_assign if t.is_sky and not t.is_assigned]
    unassigned_objs=[t for t in to_assign if t.is_target and not t.is_assigned]


    #Grab targets with assignments and associate them with their cassettes
    assigned=[t for t in to_assign if t.is_assigned]
    print("{} targets had preset assignments".format(len(assigned)))
    for t in assigned:
        cassettes.assign(t, t.fiber.cassette_name)

    unassignable=[]

    #This is a bit of a hack, which works when not assigning with things
    #If more targets & skys drilled than have usable fibers, then sort by
    #priority and discard the lowest
    #This doesn't respect min sky settings in the pathological case of assigning
    # multiple setups with each other
#    import ipdb;ipdb.set_trace()

    #this doesn't work with pultible setups, esp. when there are excessive
    # numbers of targets in one/both
    #we need to compute n_skip seperately if the setups are being assigned to
    #disjoint sets of fibers and then skip within each setup.
    #if sharing a common set of fibers we need to apply n_skip evenly to the
    # setups

    #determine number to skip in each setup when assigning setups to R/B side
    # only
    n_skip_map={}
    if len([s for s in setups if s.assigning_to!='both'])==0:
        n_skip=(sum(len([x for x in to_assign if x in s.to_assign])
                   for s in setups) - cassettes.n_available)
        base_skip=n_skip / len(setups)
        extra_skip=n_skip % len(setups)
        for s in setups:
            n_skip_map[s]=base_skip
            if extra_skip>0:
                n_skip_map[s]+=1
                extra_skip-=1
    else:
        #R side
        r_setups=[s for s in setups if s.assigning_to=='r']
        if r_setups:
            n_skip_r=(sum(len([x for x in to_assign if x in s.to_assign])
                          for s in r_setups) - cassettes.n_r_available)
            base_skip=n_skip_r / len(r_setups)
            extra_skip=n_skip_r % len(r_setups)
            for s in r_setups:
                n_skip_map[s]=base_skip
                if extra_skip>0:
                    n_skip_map[s]+=1
                    extra_skip-=1
        #B Side
        b_setups=[s for s in setups if s.assigning_to=='b']
        if b_setups:
            n_skip_b=(sum(len([x for x in to_assign if x in s.to_assign])
                          for s in b_setups) - cassettes.n_b_available)
            base_skip=n_skip_b / len(b_setups)
            extra_skip=n_skip_b % len(b_setups)
            for s in b_setups:
                n_skip_map[s]=base_skip
                if extra_skip>0:
                    n_skip_map[s]+=1
                    extra_skip-=1

#    n_skip=len(unassigned_skys)+len(unassigned_objs)-cassettes.n_available
    #First drop skys
    for s in setups:
        n_skip=n_skip_map[s]
        if n_skip > 0:
            skys=[sk for sk in unassigned_skys if sk in s.field.skys]
            #Drop as many as we can while respecting minsky
            todrop=max(min(len(skys)-s.minsky, n_skip),0)
            #respect priorities
            skys.sort(key=lambda x:x.priority)
            
            unassignable+=skys[:todrop]
            for sk in skys[:todrop]:
                try:
                    unassigned_skys.remove(sk)
                except ValueError:
                    pass
            if todrop:
                _log.warn('Dropping {} of {} skys in {} '.format(todrop,
                                                                 len(skys),
                                                                 s.name)+
                          'because there are too many things to plug.')
            n_skip_map[s]-=todrop
#            n_skip-=todrop
##            if n_skip <1:
##                break

    #Then drop targets if still needed
    for s in setups:
        n_skip=n_skip_map[s]
        if n_skip > 0:
            objs=[t for t in unassigned_objs if t in s.field.targets]
            #Drop as many as we must
            todrop=n_skip
            #respect priorities
            objs.sort(key=lambda x:x.priority)
            
            unassignable+=objs[:todrop]
            for t in objs[:todrop]:
                try:
                    unassigned_objs.remove(t)
                except ValueError:
                    pass
            if todrop:
                _log.warn('Dropping {} of {} targets in {} '.format(todrop,
                                                                    len(objs),
                                                                    s.name)+
                          'because there are too many things to plug.')
            n_skip_map[s]-=todrop
#            n_skip-=todrop
#            if n_skip <1:
#                break

#    import ipdb;ipdb.set_trace()

    #assign targets first
    while unassigned_objs:
        #Update cassette availability for each hole (a cassette may have filled)
        for t in unassigned_objs:
            #Get cassettes with correct slit and free fibers
            # n.b these are just cassette name strings
            possible_cassettes=[c.name for c in cassettes
                                if t.is_assignable(cassette=c) and
                                c.n_avail >0]
            t.update_possible_cassettes_by_name(possible_cassettes)

        #Get hole furthest from its cassettes and assign to nearest available
        unassigned_objs.sort(key=lambda t: t.plug_priority)
        t=unassigned_objs.pop()
        if t.nearest_usable_cassette:
            cassettes.assign(t, t.nearest_usable_cassette)
        else:
            unassignable.append(t)
#            import ipdb;ipdb.set_trace()
            _log.warn('No suitable cassette for targ {}'.format(t))

    #Assign skys second
    while unassigned_skys:
        #Update cassette availability for each hole (a cassette may have filled)
        for t in unassigned_skys:
            #Get cassettes with correct slit and free fibers
            # n.b these are just cassette name strings
            possible_cassettes=[c.name for c in cassettes
                                if t.is_assignable(cassette=c) and
                                c.n_avail >0]
            t.update_possible_cassettes_by_name(possible_cassettes)

        #Get hole furthest from its cassettes and assign to nearest available
        unassigned_skys.sort(key=lambda t: t.plug_priority)
        t=unassigned_skys.pop()
        if t.nearest_usable_cassette:
            cassettes.assign(t, t.nearest_usable_cassette)
        else:
            unassignable.append(t)
            _log.warn('No suitable cassette for sky {}'.format(t))


    ####As many targets as possible have now been assigned to a cassette####
    assigned=[t for t in to_assign if t not in unassignable]

    for t in assigned:
        if t not in cassettes.get_cassette(t.assigned_cassette).targets:
            import ipdb;ipdb.set_trace()

    #For each cassette assign fiber numbers with x coordinate of holes
    cassettes.map()

    for t in assigned:
        if t not in cassettes.get_cassette(t.assigned_cassette).targets:
            import ipdb;ipdb.set_trace()

    #Compact the assignments (get rid of underutillized cassettes)
    _condense_cassette_assignments([c for c in cassettes if c.on_left])
    _condense_cassette_assignments([c for c in cassettes if c.on_right])

    for t in assigned:
        if t not in cassettes.get_cassette(t.assigned_cassette).targets:
            import ipdb;ipdb.set_trace()
    
    #Rejigger the fibers
    _rejigger_cassette_assignments([c for c in cassettes if c.on_left])
    _rejigger_cassette_assignments([c for c in cassettes if c.on_right])

    for t in assigned:
        if t not in cassettes.get_cassette(t.assigned_cassette).targets:
            import ipdb;ipdb.set_trace()

    #Remap fibers
    cassettes.map(remap=True)
    
    
    for s in setups:
        s.cassette_config=cassettes


def _condense_cassette_assignments(cassettes):
    #Grab cassettes with available fibers
    non_full=[c for c in cassettes if c.n_avail >0 and c.used>0]
    
    to_check=list(non_full)
    to_check.sort(key= lambda x: x.n_avail)
    
    while to_check:
        
        trial=to_check.pop()
        
        #Try to reassign all holes to non full cassettes
        targets=list(trial.targets)
        for t in targets:
            #If hole can't be assigned then screw it
            if not t.is_assignable:
                break
            #Try assigning the hole to another tetris
            recomp_non_full=False
            for c in non_full:
                if t.is_assignable(cassette=c):
                    trial.unassign(t)
                    c.assign(t)
                    recomp_non_full=True
                    break
            if recomp_non_full:
                #Redetermine what is full
                recomp_non_full=False
                non_full=[c for c in non_full if c.n_avail>0]
        
        #If we have emptied the cassette then don't add anything to it
        if trial.used == 0:
            try:
                non_full.remove(trial)
            except ValueError,e:
                #it is possible that trial filled up, was dropped from non_full
                # or something like that
                pass
        
        #Update sort of to check
        to_check.sort(key= lambda x: x.n_avail)


def _rejigger_cassette_assignments(cassettes):
    """Go through the cassettes swapping holes to eliminate
    verticle excursions
    """
    cassettes.sort(key=lambda c: c.pos[1])
#    import ipdb;ipdb.set_trace()
    for i in range(len(cassettes)-1):
        cassette=cassettes[i]
        higer_cassettes=cassettes[i:]

        swappable_cassette_targets=[t for t in cassette.targets
                                    if t.is_assignable]

#        if not swappable_cassette_targets:
#            import ipdb;ipdb.set_trace()

        swappable_higher_targets=[t for c in higer_cassettes
                                    for t in c.targets
                                    if t.is_assignable(cassette=cassette)]
        
        if not swappable_higher_targets:
#            import ipdb;ipdb.set_trace()
            continue
        
        targets=swappable_cassette_targets+swappable_higher_targets
        targets.sort(key=operator.attrgetter('hole.y'))
        
        #Find index of lowest target not in the cassette
        sort_ndxs=[targets.index(t) for t in swappable_cassette_targets]
        first_higher_ndx=len(sort_ndxs)
        for i in range(len(sort_ndxs)):
            if i not in sort_ndxs:
                first_higher_ndx=i
                break
        
        #For targets not at start of sorted list
        for i in sort_ndxs:
            if i > first_higher_ndx:
                low_target=targets[i]
                #attempt exchange with lower holes
                for j in range(first_higher_ndx, i):
                    #nb high cassette might be same
                    high_cassette=[c for c in cassettes
                                   if c.name==targets[j].assigned_cassette][0]
                    if high_cassette==cassette:
                        continue
#                    import ipdb;ipdb.set_trace()
                    if (targets[j].is_assignable(cassette=cassette) and
                        low_target.is_assignable(cassette=high_cassette)):
                        #Unassign
                        high_cassette.unassign(targets[j])
                        cassette.unassign(low_target)
                        #Assign
                        high_cassette.assign(low_target)
                        cassette.assign(targets[j])
                        break


def _filter_for_pluggability(targets):
    """
    return subset of targets that may be plugged simultaneously
    """

    x=[t.hole.x for t in targets]
    y=[t.hole.y for t in targets]
    d=[t.hole.conflict_d for t in targets]
    
    #Nothing can conflict
    coll_graph=build_overlap_graph_cartesian(x,y,d)

    keep=coll_graph.crappy_min_vertex_cover_cut()

    return [targets[i] for i in keep]


