#!/usr/bin/env python
import numpy as np
import matplotlib.pyplot as plt
from m2fsholesxy import m2fsholesxy as m2hxy

day,month,year=25,11,2013
def sex2dec(d,m,s,ra=False):
    mul=15.0 if ra else 1.0
    if d<0:
        return d - m/60.0 - s/3600.0
    else:
        return mul*(d + m/60.0 + s/3600.0)

dat=[(7,22,11.22, -75,01,32.0,2000.0,'O'),
(7,21,44.92,-74,58,20.5,2000.0,'O'),
(7,21,14.88,-74,59,41.5,2000.0,'O'),
(7,22,30.98,-75,07,52.8,2000.0,'O'),
(7,20,52.64,-75,02,36.8,2000.0,'O'),
(7,20,7.09,-74,59,23.2,2000.0,'O'),
(7,21,0.83,-75,05,51.0,2000.0,'O'),
(7,22,1.43,-74,58,53.4,2000.0,'S'),
(7,22,11.14,-75,8,26.1,2000.0,'S'),
(7,20,25.38,-74,58,0.0,2000.0,'S'),
(7,25,38.01,-74,50,12.9,2000.0,'A'),
(7,25,51.51,-74,57,50.6,2000.0,'A'),
(7,24,46.80,-75,04,34.9,2000.0,'A'),
(7,22,14.36,-74,59,56.4,2000.0,'A'),
(7,21,7.52,-74,54,25.4,2000.0,'A'),
(7,25,42.31,-74,49,13.7,2000.0,'G'),
(7,25,56.72,-75,00,42.9,2000.0,'G'),
(7,22,41.94,-75,02,30.1,2000.0,'G')]
ras=[sex2dec(*d[0:3],ra=True) for d in dat]
decs=[sex2dec(*d[3:6]) for d in dat]
typ=[d[-1] for d in dat]
ep=[d[-2] for d in dat]

ut=sex2dec(7,30,00) #Intended UT time of observation in decimal hours
utdate=np.array([day,month,year]) # Intended UT day of observation

long_bn=sex2dec(70,42,06.00)  #70 42 06.00 in decimal degrees
lat=sex2dec(-29,00,12.00) #-29 00 12.00 in decimal degrees
height=2282.0 #2282.0 meters
rafield=sex2dec(7,23,45.07,ra=True) #field ra in decimal degrees
decfield=sex2dec(-74,56,56.0) #field dec in decimal degrees
epochfield=2000.0 #field coord epoch
fieldrot=180.0 #always?
rastars=np.array(ras) # Array of RAs in decimal hours
decstars=np.array(decs) # Array of DECs in decimal degrees
epochstars=np.array(ep) # Array of epochs (e.g. 2000.0)
type_bn=np.array(typ) #Array of types ('G', 'A', 'T'
tconfig=3 # 1 Baade 2 Baade ADC 3 Clay
#returns
#xm,
#ym,
#zm,
#sizem,
#sidtime,
#hangle,
#azimuth,
#elevation, #???
#airmass

type_out2,xm2,ym2,zm2,sizem2,sidtime2,hangle2,azimuth2,elevation2,airmass2 = m2hxy(
    ut,utdate,lat,long_bn,height,rafield,decfield,epochfield,fieldrot,
    rastars,decstars,epochstars,type_bn)


print  hangle2, sidtime2, elevation2, azimuth2, airmass2

report2=['{:7.4} {:7.4} {:7.4} {:7.4}'.format(*r) for r in zip(xm2,ym2,zm2,sizem2)]