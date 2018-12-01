SH_RADIUS=0.1875

PLATE_RADIUS=14.25

PLATE_TARGET_RADIUS_LIMIT=12.23 #14.25'

GUIDE_EXCLUSION_D=0.7

#- overlap implies holes must have a slight gab between them
#of %*r_other e.g if other hole is 1" and pct is -.05 then must be
# clearance of .05" between their edges. 
SIMULTANEOUS_PLUG_PCT_R_OVERLAP_OK=-0.05

DRILLABLE_PCT_R_OVERLAP_OK=.9

#must be <= SIMULTANEOUS_PLUG_PCT_R_OVERLAP_OK
GUIDEACQ_PCT_R_OVERLAP_OK=-0.05

assert GUIDEACQ_PCT_R_OVERLAP_OK<=SIMULTANEOUS_PLUG_PCT_R_OVERLAP_OK