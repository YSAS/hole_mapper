import numpy as np
from jbastro.astroLib import sexconvert
from m2fsholesxy import m2fsholesxy as m2hxy


#_raarray=np.array(1000,dtype=np.float)
#_decarray=np.array(1000,dtype=np.float)
#_eparray=np.array(1000,dtype=np.float)
#_typearray=np.array(1000,dtype='S1')

CLAY_LONGITUDE=sexconvert(70,42,06.00,dtype=float) #70 42 06.00 in decimal degrees
CLAY_LATITUDE=sexconvert(-29,00,12.00,dtype=float) #-29 00 12.00 in decimal degrees
CLAY_ELEVATION=2282.0 #2282.0 meters

def compute_hole_positions(field_ra,field_dec,field_epoch, date,
                           ras,decs,epochs,targ_types,
                           fieldrot=180.0, longitude=CLAY_LONGITUDE,
                           latitude=CLAY_LATITUDE, elevation=CLAY_ELEVATION):
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


    if not len(ras):
        raise ValueError('Must specify stars')

    nstar=len(ras)

    ut=sexconvert(date.timetuple()[3:6],dtype=float)
    utdate=np.array([date.day,date.month,date.year])

    rafield=sexconvert(field_ra,dtype=float,ra=True)
    decfield=sexconvert(field_dec,dtype=float)
    epochfield=float(field_epoch)

    rastars=np.array([sexconvert(ra, dtype=float, ra=True) for ra in ras])
    decstars=np.array([sexconvert(de, dtype=float) for de in decs])
    epochstars=np.array([float(ep) for ep in epochs])
    typestars=np.array([c for c in targ_types])

#    _raarray[i]=rastars[i]
#    _decarra[i]=decstars[i]
#    _eparray[i]=epochstars[i]
#    _typearray[i]=typestars[i]

    #All coordinates are now in decimal degrees

    #Call the fortran code
    x,y,z,r,type_out, st,ha,az,el,airmass,nout = m2hxy(ut, utdate, latitude,
          longitude, elevation, rafield, decfield, epochfield, fieldrot,
          rastars, decstars, epochstars, typestars)

#    x=np.zeros(nstar+100,dtype=np.float)
#    y=np.zeros(nstar+100,dtype=np.float)
#    z=np.zeros(nstar+100,dtype=np.float)
#    r=np.zeros(nstar+100,dtype=np.float)
#    type_out=np.zeros(nstar+100,dtype='S1')
#    nout=nstar+30
#    st=0.0
#    ha=0.0
#    az=0.0
#    el=0.0
#    airmass=0.0

    class retobj(object):
        pass


    pos=retobj()
    mech=retobj()
    ret=retobj()
    pos.x=[v for v in x[:nstar]]
    pos.y=[v for v in y[:nstar]]
    pos.z=[v for v in z[:nstar]]
    pos.r=[v for v in r[:nstar]]


    mech.x=[v for v in x[nstar:nout]]
    mech.y=[v for v in y[nstar:nout]]
    mech.z=[v for v in z[nstar:nout]]
    mech.r=[v for v in r[nstar:nout]]
    mech.type=[v for v in type_out[nstar:nout]]

    ret.airmass=airmass
    ret.ha=ha
    ret.el=el
    ret.st=st
    ret.az=az
    

    return (pos, mech, ret)


