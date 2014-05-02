import numpy as np
from jbastro.astroLib import sexconvert
from m2fsholesxy import m2fsholesxy as m2hxy
from m2fsholesxy import m2fsholesxyplate as m2hxyplate

CLAY_LONGITUDE=sexconvert(70,42,06.00,dtype=float) #70 42 06.00 in decimal degrees
CLAY_LATITUDE=sexconvert(-29,00,12.00,dtype=float) #-29 00 12.00 in decimal degrees
CLAY_ELEVATION=2282.0 #meters

def compute_hole_positions(field_ra,field_dec,field_epoch, date,
                           ras,decs,epochs,targ_types,
                           longitude=CLAY_LONGITUDE,
                           latitude=CLAY_LATITUDE,
                           elevation=CLAY_ELEVATION):
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

    fieldrot=180.0 if field_dec <= latitude else 0.0

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

    #All coordinates are now in decimal degrees

    #Call the fortran code
#    TODO: Remove hack fix in m2fsholes xy.f90
# change         if(type.ne.'F'.and.type.ne.'T') then
# to         if(type.ne.'F'.and.type.ne.'B') and recompile
    typestars[typestars=='T']='O'
    x,y,z,d,type_out, st,ha,az,el,airmass,nout = m2hxy(ut, utdate, latitude,
          longitude, elevation, rafield, decfield, epochfield, fieldrot,
          rastars, decstars, epochstars, typestars)
    typestars[typestars=='O']='T'
    type_out[type_out=='O']='T'


    class retobj(object):
        pass

    pos=retobj()
    pos.x=[v for v in x[:nstar]]
    pos.y=[v for v in y[:nstar]]
    pos.z=[v for v in z[:nstar]]
    pos.d=[v for v in d[:nstar]]

    nguide=(typestars=='G').sum()
    if nguide:
        guideref=retobj()
        guideref.x=[v for v in x[nstar:nstar+3*nguide]]
        guideref.y=[v for v in y[nstar:nstar+3*nguide]]
        guideref.z=[v for v in z[nstar:nstar+3*nguide]]
        guideref.d=[v for v in d[nstar:nstar+3*nguide]]
        guideref.type=[v for v in type_out[nstar:nstar+3*nguide]]
    
        if (np.array(guideref.d)==0.0).any():
            import ipdb;ipdb.set_trace()
    else:
        guideref=None
    
    ret=retobj()
    ret.airmass=airmass
    ret.ha=ha
    ret.el=el
    ret.st=st
    ret.az=az
    

    return (pos, guideref, ret)



def get_plate_holes(fieldrot=180.0):
    """
    Compute x,y,z,r for the standard holes on a plate
    """
    
    class retobj(object):
        pass
    mech=retobj()
    
    std_offset=2.44268264430000003884
    std_offset_z=-0.0585076611999999982
    science_d=0.166
    fid_d=0.26
    x=[ -std_offset,   std_offset,  0., 0.,
       -13.75, 13.75,  -13.75, 13.75,
       -12.125, -2.91000008580000013581,  12.78999996189999954765]

    y=[ 0., 0., -std_offset, std_offset,
       2.5, 2.5, -2.5, -2.5,
       7., -13.69499969479999990085, 5.6939997673000002365]
    
    z=[std_offset_z, std_offset_z,std_offset_z,std_offset_z,
       -1.5, -1.5, -1.5, -1.5,
       -1.5, -1.5, -1.5]

    d=[science_d, science_d, science_d, science_d,
       fid_d, fid_d, fid_d, fid_d,
       fid_d, fid_d, fid_d]
       
    type_out=['Z', 'Z', 'Z', 'Z', 'F', 'F', 'F', 'F', 'B', 'B', 'B']

    mech.x=x
    mech.y=y
    mech.z=z
    mech.d=d
    mech.type=type_out

#    rafield=0.0
#    decfield=0.0
#    epochfield=2000.0
#    
#    deltara=lambda dec: np.rad2deg(np.arccos(
#                np.cos(np.deg2rad(180./3600.0)) *
#                1.0/np.cos(np.deg2rad(dec))**2 -
#                np.tan(np.deg2rad(dec))**2))
#    
#    rastars= np.array([              0.0,                0.0,
#                       deltara(decfield), -deltara(decfield)]) + rafield
#                       
#    decstars=np.array([       180/3600.0,        -180/3600.0,
#                                     0.0,                0.0]) + decfield
#                                     
#    epochstars=np.array([2000.0]*4)
#
#    nstar=len(rastars)
#
#    #Call the fortran code
#    x,y,z,d,type_out = m2hxyplate(rafield, decfield, epochfield, fieldrot,
#                                  rastars, decstars, epochstars)


#    mech.x=x.tolist()
#    mech.y=y.tolist()
#    mech.z=z.tolist()
#    mech.d=d.tolist()
#    mech.type=[t for t in type_out]
#    import ipdb;ipdb.set_trace()

    
    return mech


#def plater(fieldrot=180.0):
#    """
#    Compute x,y,z,r for the standard holes on a plate
#    """
#    
#    rafield=0.0
#    decfield=0.0
#    epochfield=2000.0
#    
#    deltara=lambda dec,delt_as: np.rad2deg(np.arccos(
#                np.cos(np.deg2rad(delt_as/3600.0)) *
#                1.0/np.cos(np.deg2rad(dec))**2 -
#                np.tan(np.deg2rad(dec))**2))
#    
#    rastars= np.array([              0.0,                0.0]) + rafield
#                       
#    decstars=np.array([       29.5/60/2,        29.5/60/2]) + decfield
#                                     
#    epochstars=np.array([2000.0]*2)
#
#    nstar=len(rastars)
#
#    #Call the fortran code
#    x,y,z,r,type_out = m2hxyplate(rafield, decfield, epochfield, fieldrot,
#                                  rastars, decstars, epochstars)
#
#
#    print x
#    print y
#    
#    raise Exception
#
##    import ipdb;ipdb.set_trace()
#
#    
#    return mech
#
#plater()

