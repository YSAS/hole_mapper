import operator
from cassettes import CASSETTE_NAMES, RED_CASSETTE_NAMES, BLUE_CASSETTE_NAMES
from graphcollide import build_overlap_graph_cartesian, GraphCutError
from logger import getLogger
from errors import ConstraintError
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
            setup.assign_to in ['single','r','b']):
            if ((n_needed<=n_r_avail and setup.assign_to!='b') or
                setup.assign_to=='r'):
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
            setups[0].assign_to in ['single','r','b'] or
            setups[1].assign_to in ['single','r','b']):
            if (incompatible and
                setups[0].assign_to==setups[1].assign_to and
                setups[0].assign_to!='single'):
                _log.critical('Setups can not be assigned together.')
                raise ConstraintError('Setups incompatible and required to '
                                      'be on same arm. Correct .setup.')
            if (setups[0].assign_to==setups[1].assign_to and
                setups[0].assign_to!='single'):
                raise ConstraintError('Setups should be on different arms. '
                                      'Correct .setup.')
            _log.info('Assigning 2 to seperate spectrographs')
            
            if setups[0].assign_to=='b' or setups[1].assign_to=='r':
                setup_to_b=setups[0]
                setup_to_r=setups[1]
            else:
                setup_to_b=setups[1]
                setup_to_r=setups[0]
            
            for t in setup_to_b.field.skys+setup_to_b.field.targets:
                t.set_possible_cassettes(BLUE_CASSETTE_NAMES)
            setup_to_b.set_assigning_to(blue=True)
            setup_to_b.config.r.active_fibers=setup_to_r.config.r.active_fibers
            
            for t in setup_to_r.field.skys+setup_to_r.field.targets:
                t.set_possible_cassettes(RED_CASSETTE_NAMES)
            setup_to_r.config.b.active_fibers=setup_to_b.config.b.active_fibers
            setup_to_r.set_assigning_to(red=True)
            
        else:
            _log.info('Assigning 2 to both')
            for s in setups:
                s.set_assigning_to(both=True)
                for t in s.field.skys+s.field.targets:
                    t.set_possible_cassettes(CASSETTE_NAMES)

    else: # more than 2 setups
        #make sure all are fiber compatible (e.g. all to odds, all to evens, etc)
        _log.info('Assigning > 2')
        _log.warn('Assigning > 2 setups support is spotty if you want '
                  'anything more than plane jane setups together.')
        try:
            for s in setups:
                assert s.assign_to=='any'
        except AssertionError:
            raise ConstraintError('Assigning > 2 only supports assign_to=any.')
        try:
            for s in setups[1:]:
                assert (s.config.r.active_fibers ==
                        setups[0].config.r.active_fibers)
                assert (s.config.b.active_fibers ==
                        setups[0].config.b.active_fibers)
        except AssertionError:
            raise ConstraintError('Assigning > 2 only supports setups which '
                                  'all use use the same set of active fibers.')
        
        #Set all to use any
        for s in setups:
            s.set_assigning_to(both=True)
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
    
    #Get all the targets we are to assign filtering out targets
    # which can't be plugged simultaneously
    to_assign=[]

    #Filter each setup by priority
    for s in setups:
        setup_targets=s.to_assign
        x=[t.hole.x for t in setup_targets]
        y=[t.hole.y for t in setup_targets]
        d=[t.hole.conflict_d for t in setup_targets]
        weights=[t.priority/(t.field.max_priority if t.field.max_priority else 1)
                 for t in setup_targets]
        
        coll_graph=build_overlap_graph_cartesian(x,y,d) #Nothing can conflict
        keep=coll_graph.crappy_min_vertex_cover_cut(weights=weights)
        
        to_assign.extend([setup_targets[i] for i in keep])

    #Filter the ensemble together respecting mustkeep and keepall
    #this filtering process will for example kill every sky in one setup
    #in favor of the skys in the other if they have a lower weight and they all
    #conflict
    #to_assign=[t for t in to_assign if t.setup==setups[0]]
    x=[t.hole.x for t in to_assign]
    y=[t.hole.y for t in to_assign]
    d=[t.hole.conflict_d for t in to_assign]

#    #determine the indexes of skys and give them deterministically random
#    # weights less than minweight
#    #this works bust pathological case randomly gives all skys in one setup
#    # higher pri than others, doesn't respect minsky
#    minw=min(weights)
#    import random
#    seedbackup=random.getstate()
#    skyi=[i for i,t in enumerate(to_assign) if t.is_sky]
#    random.seed(0)
#    for i in skyi: weights[i]=minw-random.random()-1
#    random.setstate(seedbackup)

    #setup mustkeep can override field settings
    uncuttable=[i for i,t in enumerate(to_assign) if t.setup.mustkeep and
                t.priority >= t.setup.mustkeep_priority and t.is_target]
    
    coll_graph=build_overlap_graph_cartesian(x, y, d) #Nothing can conflict


    #first cut anything that conflicts with something uncuttable
    # if an uncuttable conflicts with an uncuttable warn the user
    fatal_conflicts=[]
    for i in uncuttable:
        for k in coll_graph.collisions(i):
            if k in uncuttable:
                fatal_conflicts.append(i)
                break
    if fatal_conflicts:
        _log.warn('There are {} skys/targets '.format(len(fatal_conflicts))+
                 'that must be kept that interfere with others that also '
                 'must be kept.')
        raise ConstraintError('Collisions among targets affected by mustkeep '
                              'make assignment impossible.')

    #Drop things that collide with uncuttable things this may drop
    #uncuttable targets, but the user has been warned
    discard=[]
    for i in uncuttable: discard.extend(coll_graph.drop_conflicting_with(i))

    #Now go through the setups round-robin taking the highest priority
    #target and discarding the others
    #There are edge cases where min sky would not be met here
    # one what do deal with this would be to do conditional discards if
    #a collision involves skys, but this would need iterating and adding a
    #sky back might create a conflict (say if the sky that was dropped
    # conflited with two targets but they didn't conflict with each other
    s_i=0
    while len(setups)>1 and not coll_graph.is_disconnected:
        #get all collisions belonging to setup[s_i] and sort by priority
        in_s_i=[i for i in coll_graph.get_colliding_nodes()
                if to_assign[i] in setups[s_i].to_assign]
        pri=[to_assign[i].priority for i in in_s_i]
        in_s_i, _ = zip(*sorted(zip(in_s_i, pri)))
        discard.extend(coll_graph.drop_conflicting_with(in_s_i[0]))
        s_i=(s_i+1) % len(setups)

    to_assign=[t for i,t in enumerate(to_assign) if i not in discard]

    #check minsky
    for s in setups:
        skys_kept=[t for t in to_assign if t.is_sky and t in s.to_assign]
        if len(skys_kept) < s.minsky:
            _log.warn('There are only {} '.format(len(skys_kept))+
                     'skys after filtering for collisions for '
                     '{} but minsky={}'.format(s.name,s.minsky))
            raise ConstraintError('Collisions among setups '
                                  'means minksy not met.')


    #end of filter
    
    #Reset all the assignments
    for s in setups: s.reset()
    
    cassettes=setups[0].cassette_config

    #HMMM this might need combining
    
    #Grab all skys and objects that don't have assignments
    unassigned_skys=[t for t in to_assign if t.is_sky and not t.is_assigned]
    unassigned_objs=[t for t in to_assign if t.is_target and not t.is_assigned]


    #Grab targets with assignments and associate them with their cassettes
    assigned=[t for t in to_assign if t.is_assigned]
    print("{} targets had preset assignments".format(len(assigned)))
    try:
        for t in assigned: cassettes.assign(t, t.fiber.cassette_name)
    except ValueError:
        raise ConstraintError('Collisions among targets with preset fibers '
                              ' assignment impossible.')

    unassignable=[]




    #IS THIS COMMENT CURRENT?
    #this doesn't work with multible setups, esp. when there are excessive
    # numbers of targets in one/both
    #we need to compute n_skip seperately if the setups are being assigned to
    #disjoint sets of fibers and then skip within each setup.
    #if sharing a common set of fibers we need to apply n_skip evenly to the
    # setups

    #determine number to skip in each setup when assigning setups to R/B side
    # only
    
    #This penalizes each field with an equal number of losses, it probably
    # should penalize in proportion to each setup's contribution to the
    #total number of targets
    n_skip_map={}
    # if all going to both
    if len([s for s in setups if s.assigning_to!='both'])==0:
        #nskip is total_number_of_things_needing_fibers - number_of_available_fibers
        n_skip=(sum(len([x for x in to_assign if x in s.to_assign
                         and x not in assigned])
                   for s in setups) - cassettes.n_available)
        base_skip=n_skip / len(setups)
        extra_skip=n_skip % len(setups)
        for s in setups:
            n_skip_map[s]=base_skip
            if extra_skip>0:
                n_skip_map[s]+=1
                extra_skip-=1
    else:
#        Is this a bug? what about the setups with assigning_to==both

        #R side
        r_setups=[s for s in setups if s.assigning_to=='r']
        if r_setups:
            n_skip_r=(sum(len([x for x in to_assign if x in s.to_assign
                               and x not in assigned])
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
            n_skip_b=(sum(len([x for x in to_assign if x in s.to_assign
                               and x not in assigned])
                          for s in b_setups) - cassettes.n_b_available)
            base_skip=n_skip_b / len(b_setups)
            extra_skip=n_skip_b % len(b_setups)
            for s in b_setups:
                n_skip_map[s]=base_skip
                if extra_skip>0:
                    n_skip_map[s]+=1
                    extra_skip-=1

    #First drop skys, respecting minsky
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
            
            #verify that none of the targets to drop have highest priority and mustkeep set
            if s.mustkeep:
                not_droppable=[o for o in objs[:todrop]
                               if o.priority==s.field.max_priority]
            else:
               not_droppable=[]
            if not_droppable:
                err=('Need to drop {} highest priority targets '
                     'to make assignment work but mustkeep '
                     'is set')
                raise ConstraintError(err.format(len(not_droppable)))
            
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



    #Not sure why the skys and targets need to be done separately
    #we only have as many targets and skys as fibers now

    #note that the plug priority is not realated to the priority from users
    # it has to do with the how reachable the target is from other fibers
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


    #Verify I havn't screwed up
    for t in assigned:
        if t not in cassettes.get_cassette(t.assigned_cassette).targets:
            _log.critical("A cassette's list of targets doesn't include"
                          "a target that is assigned to it."
                          "This is a major bug. entering debugger. type help")
            import ipdb;ipdb.set_trace()

    #For each cassette assign fiber numbers with x coordinate of holes
    cassettes.map()

    #Compact the assignments (get rid of underutillized cassettes)
    
    #I don't think these inherently need to be left or right
    #esp since I've got to rejigger anyway, but that is the way it has
    # been tested
    _condense_cassette_assignments([c for c in cassettes if c.on_left])
    _condense_cassette_assignments([c for c in cassettes if c.on_right])
#    _condense_cassette_assignments([c for c in cassettes])

    #Rejigger the fibers

    _rejigger_cassette_assignments([c for c in cassettes if c.on_left])
    _rejigger_cassette_assignments([c for c in cassettes if c.on_right])
    unsided=True
    if len(setups)>1:
        for s in setups:
            if s.assign_to in ('r','b'):
                unsided=False
                break
    _rejigger_cassette_assignments_lr(cassettes, unsided=unsided)
#    _rejigger_cassette_assignments([c for c in cassettes if c.on_left])
#    _rejigger_cassette_assignments_lr(cassettes, unsided=unsided)
#    _rejigger_cassette_assignments_lr(cassettes)


    #finally to updown rejiggering to enforce ordering rules
    _rejigger_cassette_assignments([c for c in cassettes if c.on_left])
    _rejigger_cassette_assignments([c for c in cassettes if c.on_right])
#
    #Remap fibers
    cassettes.map(remap=True)
    
    #Make sure its all ok
    for t in assigned:
        if t not in cassettes.get_cassette(t.assigned_cassette).targets:
            import ipdb;ipdb.set_trace()

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
            if not t.is_assignable(): continue
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

def _rejigger_cassette_assignments_lr(cassettes, unsided=True):
    """
    Go through the cassettes swapping holes to eliminate
    horizontal excursions
    
    call after rejiggering left cassettes but before right cassettes
    """
    #work from top to bottom (or bottom to top, doesn't matter) cassette by
    # cassette
    #find all the assigned fibers in the y range of the cassette on the other
    #side of the plate
    # for any that are more on this side of the plate than fibers in this
    #cassette attempt a trade

    right_cassettes=[c for c in cassettes if c.on_right]
    left_cassettes=[c for c in cassettes if c.on_left]
    left_cassettes.sort(key=lambda c: c.pos[1])
    for cassette in left_cassettes:
#        if cassette.name[:-1] in ['R7', 'R8']:
#            import ipdb;ipdb.set_trace()
        swappable_targets=[t for t in cassette.targets if t.is_assignable()]
                                    
        if not swappable_targets: continue
        
        #get bounding y region for swappable targets
        i=left_cassettes.index(cassette)
        cbelow_i=i-1
        while (cbelow_i>0 and
               (not left_cassettes[cbelow_i].targets or
               (left_cassettes[cbelow_i].side!=cassette.side or unsided))):
            cbelow_i-=1
        if cbelow_i<=0:
            cassette_min_y=float('-inf')
        else:
            cassette_min_y=max([t.hole.y
                                for t in left_cassettes[cbelow_i].targets])

        cabove_i=i+1
        while (cabove_i<len(left_cassettes) and
               (not left_cassettes[cabove_i].targets or
               (left_cassettes[cabove_i].side!=cassette.side or unsided))):
            cabove_i+=1
        try:
            if cabove_i>=len(left_cassettes):
                cassette_max_y=float('inf')
            else:
               cassette_max_y=min([t.hole.y
                                   for t in left_cassettes[cabove_i].targets])
        except ValueError:
            import ipdb;ipdb.set_trace()
#        _log.debug('RLR:  {}({}) - {} - {}({})'.format(
#           left_cassettes[cbelow_i].name if cbelow_i>=0 else 'X',
#           cassette_min_y, cassette.name,
#           left_cassettes[cabove_i].name if cabove_i<len(left_cassettes) else 'X',
#           cassette_max_y))
        swappable_other_targets=[t for c in right_cassettes
                                 for t in c.targets if
                                 t.hole.y<=cassette_max_y and
                                 t.hole.y>=cassette_min_y and
                                 t.is_assignable(cassette=cassette)]
        
        if not swappable_other_targets: continue
        

        other_max_x=max([t.hole.x for t in swappable_other_targets])
        
        #Consider only targets with x values less that the max of other
        # because x increases to left
        swappable_targets=[t for t in swappable_targets if t.hole.x < other_max_x]
        if not swappable_targets: continue


        #work from right to left while swappable targets are more right than
        # the left most swappable_other_targets
        swappable_targets.sort(key=operator.attrgetter('hole.x'))
        swappable_other_targets.sort(key=operator.attrgetter('hole.x'),
                                     reverse=True)
        for t in swappable_targets:
            swapped=False
            for ot in swappable_other_targets:
                #try a trade with the furthest right if it
#                _log.debug('?Swap {} w/ {}'.format(t.hole.position,ot.hole.position))
                if ot.hole.x > t.hole.x:
                    if t.is_assignable(cassette=ot.assigned_cassette):
                        ocassette=cassettes.get_cassette(ot.assigned_cassette)
                        #Unassign
                        ocassette.unassign(ot)
                        cassette.unassign(t)
                        #Assign
                        ocassette.assign(t)
                        cassette.assign(ot)
#                        _log.debug('    Yes')
                        swapped=True
                        break
                    else:
                        pass
                        #maybe it can be traded with another (unlikely branch)
                else:
                    #we are done with both loops
                    break
            #remove other target from conisderation in further swaps
            if swapped: swappable_other_targets.remove(ot)


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
                                    if t.is_assignable()]

        swappable_higher_targets=[t for c in higer_cassettes
                                    for t in c.targets
                                    if t.is_assignable(cassette=cassette)]
        
        if not swappable_higher_targets:
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

    #target.must_be_drilled not necessarily the same thing as
    # t.priority==t.field.max_priority and t.setup.mustkeep
    uncuttable=[i for i,t in enumerate(targets)
                if t.priority==t.field.max_priority and t.setup.mustkeep]
    weights=[t.priority/(t.field.max_priority if t.field.max_priority else 1)
             for t in targets]
    import ipdb;ipdb.set_trace()
    try:
        keep=coll_graph.crappy_min_vertex_cover_cut(uncuttable=uncuttable,
                                                    weights=weights)
    except GraphCutError:
        raise ConstraintError('Collisions among targets affected by mustkeep '
                              'makes assignment impossible')
    return [targets[i] for i in keep]


