import numpy as np
from jbastro.astrolib import sexconvert

CLAY_LONGITUDE=sexconvert(70,42,06.00,dtype=float) #70 42 06.00 in decimal degrees
CLAY_LATITUDE=sexconvert(-29,00,12.00,dtype=float) #-29 00 12.00 in decimal degrees
CLAY_ELEVATION=2282.0 #2282.0 meters

def compute_hole_positions(field_ra,field_dec,field_epoch, date,
                           ras,decs,epochs,targ_types,
                           fieldrot=180.0, longitude=CLAY_LONGITUDE,
                           latitude=CLAY_LATITUDE, elevation=CLAY_ELEVATION)
    """
    Compute x,y,z,r for the holes on a plate
    
    ra,dec,epoch of field center
    datetime object with UT time of desired intended observation
    arrays of ra,dec,epoch & type ('G', 'A', 'T', 'S') for the targets
    optionally the field rotation
    
    returns tuple,
        first element (x,y,z,r) of targets
        second (x,y,z,r) of mechanical holes
        third dict of field info
            ha
            st
            az
            el
            airmass
            
    
    """
    from m2fsholesxy import m2fsholesxy as m2hxy

    if not len(rastars):
        raise ValueError('Must specify stars')

    ut=sexconvert(date.timetuple()[3:6],dtype=float)
    utdate=np.array([date.day,date.month,date.year])

    rafield=sexconvert(field_ra,dtype=float,ra=True)
    decfield=sexconvert(field_dec,dtype=float,ra=True)
    epochfield=float(field_epoch)

    rastars=np.array([sexconvert(ra, dtype=float, ra=True) for ra in ras])
    decstars=np.array([sexconvert(de, dtype=float) for de in decs])
    epochstars=np.array([float(ep) for ep in epochs])
    typestars=np.array([c for c in targ_types])

    #All coordinates are now in decimal degrees

    #Call the fortran code
    x,y,z,r,type_out,st,ha,az,el,airmass,nout = m2hxy(ut, utdate, latitude,
          longitude, elevation, rafield, decfield, epochfield, fieldrot,
          rastars, decstars, epochstars, typestars)

    pos=(x[:nstar],y[:nstar],z[:nstar],r[:nstar])
    mech_pos=(x[nstar:nout],y[nstar:nout],z[nstar:nout],r[nstar:nout],
              type_out[nstar:nout])

    class retobj(object):
        pass
    ret=retobj()
    ret.airmass=airmass
    ret.ha=ha
    ret.el=el
    ret.st=st
    ret.az=az

    return (pos, mech_pos, ret)

