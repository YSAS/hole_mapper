!
!   FRUIT IS A GENERAL PURPOSE SUBROUTINE USED TO CALCULATE CELESTIAL OBJECT
!   COORDINATES, HOUR ANGLES, ELEVATIONS, AIRMASSES, VELOCITY CORRECTIONS,
!   HELIOCENTRIC TIME DELAYS AND JULIAN DATES. THE PERTINENT PARAMETERS ARE
!   INPUT VIA AN ARGUMENT LIST. THE DESIRED QUANTITIES CALCULATED BY FRUIT
!   ARE RETURNED IN COMMON BLOCKS. ALL ARITHMETIC IS IN REAL*8.
!   VALID TIME RANGE ARE YEARS 1800 TO 2200.
!
!   'FRUIT' IS ADAPTED FROM THE IBM 370 PROGRAM 'LOG' WRITTEN BY STEVE KENT.
!   THIS VERSION:   16 AUG 1979  BY  PETER YOUNG.
!               :   15 OCT 1980 PLACED ON ASTRONOMY VAX BY JEFF PIER.
!
!
!   GCLONG   =  LONGITUDE OF OBSERVING SITE IN DECIMAL DEGREES (REAL*8).
!   GDLAT    =  GEODETIC LATITUDE OF OBSERVING SITE IN DECIMAL DEGREES.
!               (REAL*8).
!   H        =  HEIGHT OF OBSERVING SITE IN METRES (REAL*8).
!   EPOCH    =  EPOCH (BESSELIAN DATE IN YEARS) OF COORDINATES TO BE INPUT.
!               (REAL*8).
!   RAINP    =  RIGHT ASCENSION OF OBJECT IN DECIMAL HOURS (REAL*8).
!   DECINP   =  DECLINATION OF OBJECT IN DECIMAL DEGRESS (REAL*8).
!               NOTE THAT POSITION MUST BE MEAN COORDINATES.
!   IYEAR    =  YEAR OF OBSERVATION (INTEGER*4).
!   IMONTH   =  MONTH OF OBSERVATION (INTEGER*4).
!   IDAY     =  DAY OF OBSERVATION (INTEGER*4).
!   UTC      =  COORDINATED UNIVERSAL TIME OF OBSERVATION IN DECIMAL HOURS.
!               (REAL*8).
!
      subroutine fruit(gclong,gdlat,h,epoch,rainp,decinp,iyear,imonth, &
          iday,utc)
      implicit real*8 (o-z, a-h)
      integer*2 printr
      real*8 xinp(3),xref(3),xmean(3),xtrue(3),prec(3, 3),nut(3,3), &
          vel(3),sun(3)
!
!   RA0,DEC0 =  EPOCH 1950.0 POSITION OF OBJECT (DECIMAL HOURS, DEGREES).
!               THESE ARE MEAN COORDINATES (REAL*8).
!
!   RA,DEC   =  MEAN COORDINATES FOR EPOCH OF TIME OF OBSERVATION.
!   FPOCH    =  BESSELIAN DATE IN YEARS FOR THESE COORDINATES.
!
!   RAT,DECT =  TRUE COORDINATES AT TIME OF OBSERVATION, CORRECTED FOR
!               NUTATION.
!
!   RAA,DECA =  ABERRATION CORRECTED COORDINATES AT TIME OF OBSERVATION.
!
!   RAR,DECR =  REFRACTION CORRECTED COORDINATES FOR POSITION AND TIME OF
!               OBSERVATION. VALUES RETURNED ONLY IF ELEVATION ABOVE -35 
!               ARCMIN.  ALSO INCLUDES CORRECTION FOR ABERRATION.
!
!   GLONG    =  GALACTIC LONGITUDE (SYSTEM II) OF OBJECT.
!   GLAT     =  GALACTIC LATITUDE (SYSTEM II) OF OBJECT.
!
!   RJD      =  JULIAN DATE AT TIME OF OBSERVATION (DECIMAL DAYS). (REAL*8)
!   HJD      =  HELIOCENTRIC JULIAN DATE (DECIMAL DAYS).
!   TDELAY   =  TIME DELAY (RJD - HJD). (REAL*8). UNITS ARE DAYS.
!   VHELC    =  HELIOCENTRIC VELOCITY CORRECTION (SUBTRACT FROM OBSERVED
!               VELOCITY TO GET TRUE VELOCITY). (REAL*8). KM/SEC.
!
!   SIDTIM   =  LOCAL SIDERIAL TIME OF OBSERVATION (DECIMAL HOURS). (REAL*8)
!   HA       =  HOUR ANGLE OF OBJECT (DECIMAL HOURS). (REAL*8)
!
!   EL       =  ELEVATION OF OBJECT (TRUE, NOT REFRACTED). DECIMAL DEGREES.
!   AZ       =  AZIMUTH OF OBJECT (DECIMAL DEGREES). BOTH ARE REAL*8.
!   ELR      =  REFRACTION CORRECTED ELEVATION (REAL*8). VALUE IS RETURNED
!               ONLY IF TRUE ELEVATION ABOVE -35 ARCMIN.
!   AIRMSS   =  AIRMASS OF OBSERVATION. VALUE RETURNED ONLY IF TRUE ELEVATION
!               OF OBJECT ABOVE -35 ARCMIN.
!
      common /fruit1/ ra0, dec0
      common /fruit2/ ra, dec, fpoch
      common /fruit3/ rat, dect
      common /fruit4/ raa, deca
      common /fruit5/ rar, decr
      common /fruit6/ glong, glat
      common /fruit7/ rjd, hjd, tdelay, vhelc
      common /fruit8/ sidtim, ha
      common /fruit9/ el, az, elr, airmss
      data printr / 2 /
!
!   GET JULIAN DATE AT TIME OF OBSERVATION.
!
      call julian(iyear, imonth, iday, utc, rjd)
      if ((rjd .lt. 2378494.d0) .or. (rjd .gt. 2524959.d0)) then
        write(unit=printr, fmt=200) rjd
  200   format(21h FRUIT: JULIAN DATE: ,f15.6,22h OUTSIDE ALLOWED RANGE)
        write(unit=*, fmt=200) rjd
        return 
      end if
!
!   BESSELIAN DATE (YEARS) OF TIME OF OBSERVATION.
!
      fpoch = ((rjd - 2433282.423378d0) / 365.2421988d0) + 1950.d0
!
!   GET COORDINATE VECTOR OF INPUT RIGHT ASCENSION, DECLINATION.
!
      call vector(xinp, rainp, decinp, 1)
!
!   GET JULIAN DATE OF COORDINATE EPOCH (IN 'RJDEP').
!
      rjdep = ((epoch - 1950.d0) * 365.2421988d0) + 2433282.423378d0
      if ((rjdep .lt. 2378494.d0) .or. (rjdep .gt. 2524959.d0)) then
        write(unit=printr, fmt=201) rjdep
  201   format(20h FRUIT: EPOCH J.D.: ,f15.6,22h OUTSIDE ALLOWED RANGE)
        write(unit=*, fmt=201) rjdep
        return 
      end if
!
!   GET 1950.0 MEAN COORDINATES FROM INPUT COORDINATES.
!
      call preces(rjdep, prec, nut, gclong, gdlat, h, vel, sun)
      call rotat(xinp, xref, prec, -1)
      call vector(xref, ra0, dec0, -1)
!
!   GET GALACTIC COORDINATES.
!
      call galaxy(ra0, dec0, glat, glong, 1)
!
!   PRECESS 1950.0 COORDINATES TO GET MEAN COORDINATES AT TIME OF OBSERVATION.
!
      call preces(rjd, prec, nut, gclong, gdlat, h, vel, sun)
      call rotat(xmean, xref, prec, 1)
      call vector(xmean, ra, dec, -1)
! 
!   NUTATE MEAN COORDINATES TO GET TRUE COORDINATES.
!
      call rotat(xtrue, xmean, nut, 1)
      call vector(xtrue, rat, dect, -1)
!
!   CORRECT TRUE COORDINATES FOR ABERRATION.
!
      call aberr(rat, dect, vel, raa, deca)
!
!   GET SIDERIAL TIME, HOUR ANGLE, ALTITUDE, AZIMUTH OF OBJECT.
!
      call azel(rjd, gclong, gdlat, raa, deca, sidtim, ha, el, az, rar,  &
          decr, elr, airmss)
!
!   HELIOCENTRIC VELOCITY CORRECTION (SUBTRACT FROM OBSERVED VELOCITY TO
!   GET TRUE VELOCITY). KM/SEC.
!
      vhelc = -(((vel(1)*xmean(1)) + (vel(2)*xmean(2))) +  &
          (vel(3)*xmean(3)))
!
!   CALCULATE HELIOCENTRIC TIME DELAY (SUBTRACT FROM JULIAN DATE TO GET
!   HELIOCENTRIC JULIAN DATE). UNITS ARE DAYS.
!
      tdelay = ((sun(1)*xmean(1)) + (sun(2)*xmean(2))) +  &
          (sun(3)*xmean(3))
      hjd = rjd - tdelay
!
      return 
      end
!
!   PRECES COMPUTES A PRECESSION MATRIX FOR A PARTICULAR TIME. THIS MATRIX
!   MAY BE APPLIED TO OBJECT COORDINATE VECTORS TO CONVERT THOSE COORDINATES
!   EITHER FROM OR TO 1950.0 COORDINATES. NOTE THAT PRECESS OPERATES ON   
!   MEAN COORDINATES.
!   NUTATION MATRIX IS ALSO COMPUTED, TO BE APPLIED TO COORDINATE VECTORS
!   WHICH HAVE ALREADY BEEN PRECESSED. ONLY THE LARGEST TERMS ARE CALCULATED.
!   APPROXIMATE ERRORS ARE 0.1 ARCSEC IN 'DPSI' AND 0.05 ARCSEC IN 'DEPS'.
!   IN ADDITION THE VELOCITY VECTOR OF THE OBSERVING SITE IS COMPUTED
!   RELATIVE TO THE SUN IN KM/SEC REFERRED TO THE MEAN ECLIPTIC AND EQUUATOR
!   OF DATE (GEOCENTRIC COORDINATES). VALUE ACCURATE TO 0.04 KM/SEC (RESIDUAL
!   DUE TO PLANETARY PERTURBATIONS OF BOTH EARTH AND SUN).
!   ALSO THE RECTANGULAR COORDINATES OF THE SUN RELATIVE TO THE EARTH ARE
!   COMPUTED (IN DAYS OF LIGHT TRAVEL TIME) REFERRED TO MEAN EQUATOR AND
!   ECLIPTIC OF DATE. ACCURACY IS ABOUT 3 SECONDS (RESIDUAL DUE TO PLANETARY
!   PERTURBATIONS OF BOTH SUN AND EARTH).
!
!   RJD    =  JULIAN DATE (DECIMAL DAYS) OF DESIRED EPOCH (REAL*8).
!   PREC   =  3 BY 3 PRECESSION MATRIX FOR EPOCH RJD. IF YOU INPUT THE 
!             RJD
!             FOR EPOCH 1950.0 THEN 'PREC' IS THE IDENTITY MATRIX.
!   NUT    =  3 BY 3 NUTATION MATRIX. (REAL*8).
!   GCLONG =  LONGITUDE OF OBSERVING SITE (REAL*8) IN DECIMAL DEGREES.
!   GDLAT  =  GEODETIC LATITUDE OF SITE (REAL*8) IN DECIMAL DEGREES.
!   H      =  HEIGHT OF SITE IN METRES (REAL*8).
!   VEL    =  3-COORDINATE VECTOR (REAL*8) CONTAINING EARTH'S VELOCITY
!             VECTOR IN KM/SEC.
!   SUN    =  RECTANGULAR COORDINATES OF SUN FROM EARTH (3-D VECTOR)
!             MEASURED IN DAYS (LIGHT TRAVEL TIME). (REAL*8).
!
!   IF AN OBJECT HAS MEAN COORDINATE VECTOR  X(I) THEN:
!   TO PRECESS FROM 1950.0 TO 'RJD': XNEW(I)=PREC(I,J)*X(J) SUM ON J.
!   TO PRECESS FROM 'RJD' TO 1950.0: X(J)=XNEW(I)*PREC(I,J) SUM ON I.
!   TO NUTATE MEAN VECTOR: XTRUE(I)=XMEAN(I)*NUT(I,J)*XMEAN(J)
!
!
      subroutine preces(rjd, prec, nut, gclong, gdlat, h, vel, sun)
      implicit real*8 (o-z, a-h)
      real*8 nut(3, 3), v1(3), sun(3), vel(3), prec(3, 3)
!
!   STATEMENT FUNCTIONS FOR ANGLES AND ORBITAL ELEMENTS.
!
!   PRECESSION CONSTANTS: X IN TROPICAL CENTURIES FROM 1950.0.
!
!   MEAN OBLIQUITY OF EARTH RELATIVE TO MEAN ECLIPTIC OF DATE, X IN JULIAN
!   CENTURIES FROM 1900 JAN0.5
!
!   ORBITAL ELEMENTS OF EARTH-MOON BARYCENTER RELATIVE TO SUN REFERRED TO 
!   MEAN QUINOX AND ECLIPTIC OF DATE.  X IN JULIAN DAYS SINCE 1900 JAN0.5. 
!   INCLINATION AND LONGITUDE OF ASCENDING NODE ARE ZERO BY DEFINITION.
!   ECCENTRICITY:
!   ARGUMENT OF PERIHELION (ADD 180 DEG TO THIS ONLY TO GET SUN RELATIVE
! 
!   TO EARTH).
!   MEAN ANOMALY:
!
!   ELEMENTS OF MOON RELATIVE TO EARTH, SAME REFERENCE AND EPOCH:
!   LONGITUDE OF ASCENDING NODE:
!   ARGUMENT OF PERIGEE:
!   MEAN ANOMALY:
!
!   CONVERSION FROM MEAN TO TRUE ANOMALY (APPROX.):
!
!   CONSTANTS OF THE ORBITS
!   ECCENTRICITY OF MOON
!   INCLINATION OF MOON
!
      data etut / 46.d0 /
      data pi / 3.1415926535897932d0 /
      data twopi / 6.2831853071795865d0 /
      data convd / 1.7453292519943296d-2 /
      data convds / 4.8481368110953599d-6 /
      data convhs / 7.2722052166430399d-5 /
!
      zeta(x) = (x * (2.304948d3 + (x * (0.3020d0 + (x * 0.179d-1))))) &
         * convds
!
      z(x) = (x * (2.304948d3 + (x * (1.093d0 + (x * 0.192d-1))))) *  &
        convds
!
      theta(x) = (x * (2.004255d3 + (x * ((-0.426d0) - (x * 0.416d-1)))) &
        ) * convds
!
      oblqm(x) = (23.452294d0 + (x * ((-0.0130125d0) + (x * ((-1.64d-6) &
         + (x * 5.03d-7)))))) * convd
!
      es(x) = 0.01675104d0 + (x * ((-1.1444d-9) - (x * 9.4d-17)))
!
      ws(x) = (101.220833d0 + (x * (4.70684d-5 + (x * (3.39d-13 + (x *  &
        7.d-20)))))) * convd
      anoms(x) = (358.475845d0 + (x * (0.985600267d0 + (x * ((-1.12d-13) &
         - (x * 7.d-20)))))) * convd
!
      omegam(x) = (259.183275d0 + (x * ((-0.0529539222d0) + (x * ( &
        1.557d-12 + (x * 5.d-20)))))) * convd
!
      wm(x) = (75.146281d0 + (x * (0.1643580025d0 + (x * ((-9.296d-12) &
         - (x * 3.1d-19)))))) * convd
!
      anomm(x) = ((-63.895392d0) + (x * (13.0649924465d0 + (x * ( &
        6.889d-12 + (x * 2.99d-19)))))) * convd
!
      atrue(x,e) = ((x + (((2.d0 * e) - (0.25d0 * (e ** 3))) * dsin(x))) &
         + ((1.25d0 * (e ** 2)) * dsin(2.d0 * x))) + (((13.d0 / 12.d0) * ( &
        e ** 3)) * dsin(3.d0 * x))
!
!
!   VALUES FOR SEMI-MAJOR AXES FROM MIKE ASH
!   SUN-EARTH-MOON BARYCENTER (KM)
!   DITTO (IN DAYS OF LIGHT TRAVEL TIME).
!   EARTH-MOON
!   MASSES IN KM**3/SEC**2
!   EARTH
!
      e2 = 0.054900489d0
      aim = 5.14539122 * convd
      as = (499.00478d0 * 2.99792456d5) * 1.00000023d0
      sundis = (499.00478d0 * 1.00000023d0) / 86400.d0
      am = 60.2665d0 * 6378.16d0
      emass = 398601.2d0
      smass = ((emass * 328900.d0) * 82.3d0) / 81.3d0
      ammass = emass / 81.3d0
!
!   TEST FOR VALID TIME RANGE.
!
      if ((rjd .lt. 2378494.d0) .or. (rjd .gt. 2524959.d0)) return 
!
!   T IS EPHEMERIS TIME IN DAYS SINCE 1900 JAN0.5 ET. (RJD=2415020.0).
!   ET=UT+46 SEC (APPROX. 1975) MORE ACCURATE VALUE CAN BE FOUND IN AENA.
!
      t = (rjd - 2415020.d0) + (etut / (24.0 * 3600.d0))
!
!   TY=T IN JULIAN YEARS
!
      ty = t / 365.25
!
!   TC=T IN CENTURIES.
!
      tc = ty / 100.d0
!
!   TTP=T IN TROPICAL CENTURIES SINCE 1950.0
!
      ttp = (t - 18262.423378) / 36524.21988d0
!
!   COMPUTE PRECESSION MATRIX.
!
      z1 = zeta(ttp)
      z2 = z(ttp)
      z3 = theta(ttp)
      czt = dcos(z1)
      szt = dsin(z1)
      cz = dcos(z2)
      sz = dsin(z2)
      ct = dcos(z3)
      st = dsin(z3)
      q1 = cz * ct
      q2 = sz * ct
      prec(1,1) = (czt * q1) - (szt * sz)
      prec(1,2) = (- (szt * q1)) - (czt * sz)
      prec(1,3) = - (cz * st)
      prec(2,1) = (czt * q2) + (szt * cz)
      prec(2,2) = (czt * cz) - (szt * q2)
      prec(2,3) = - (st * sz)
      prec(3,1) = czt * st
      prec(3,2) = - (szt * st)
!
!   LONGITUDE OF ASCENDING NODE OF MOON.
!
      prec(3,3) = ct
!
!   MEAN LONGITUDE OF MOON:
!
      o2 = omegam(t)
!
!   MEAN LONGITUDE OF SUN:
!
      smoon = (o2 + wm(t)) + anomm(t)
!
!   NUTATION CONSTANTS FROM ESE:
!
      ssun = ws(t) + anoms(t)
!
      dpsi = (((- ((17.233d0 + (0.017d0 * tc)) * dsin(o2))) + (0.209d0 &
         * dsin(2.d0 * o2))) - (1.273d0 * dsin(2.d0 * ssun))) - (0.204d0 &
         * dsin(2.d0 * smoon))
!
      deps = ((((9.210d0 + (0.0009d0 * tc)) * dcos(o2)) - (0.090d0 *  &
         dcos(2.d0 * o2))) + (0.552d0 * dcos(2.d0 * ssun))) + (0.088d0 *  &
         dcos(2.d0 * smoon))
!
      dpsi = dpsi * convds
!
!   TRUE OBLIQUITY
!
      deps = deps * convds
!
      oblq = oblqm(tc) + deps
      co = dcos(oblq)
!
!   ROTATION MATRIX TO FIRST ORDER (SECOND ORDER CORRECTIONS ARE OF 
!   MAGNITUDE 1.D-8 RADIANS).
!
!
      so = dsin(oblq)
!
      nut(1,1) = 1.d0
      nut(1,2) = - (dpsi * co)
      nut(1,3) = - (dpsi * so)
      nut(2,1) = - nut(1,2)
      nut(2,2) = 1.d0
      nut(2,3) = - deps
      nut(3,1) = - nut(1,3)
      nut(3,2) = deps
!
!   CALCULATE GEOCENTRIC LATITUDE AND RADIUS ARM OF SITE.
!
!
      nut(3,3) = 1.d0
!
      f = 1.d0 / 298.25d0
      a = 6378.16d0
      hh = h * 1.d-3
      rlat = gdlat * convd
      cphi = dcos(rlat)
      sphi = dsin(rlat)
      c = 1.d0 / dsqrt((cphi ** 2) + (((1.d0 - f) * sphi) ** 2))
      s = ((1.d0 - f) ** 2) * c
!
!   GEOCENTRIC LATITUDE.
!
      rad = dsqrt(((((a * s) + hh) * sphi) ** 2) + ((((a * c) + hh) *  &
        cphi) ** 2))
!
!   SIDEREAL TIME AT 0H UT (IN RADIANS).
!
      gclat = datan2(((a * s) + hh) * dtan(rlat),(a * c) + hh) / convd
!
      s = idnint(rrjd) - 2415020.5d0
      ut = (rrjd - idnint(rrjd)) + .5d0
!
!   SFRACT=RATIO OF SIDEREAL TIME TO UTC IN RAD/SEC
!
      sidtmo = 1.73993589472d0 + (s * (1.7202791266d-2 + (s *  &
        5.06409d-15)))
!
!   LOCAL SIDEREAL TIME. THIS EXPRESSION WOULD BE EXACT IF UT WERE UT1 
!   AND DPSI WAS CALCULATED MORE EXACTLY.
!
      sfract = 7.2921158546827d-5 + (s * 1.1727115d-19)
!
      oblq = oblqm(tc) + deps
      sidtim = (sidtmo + ((sfract*ut)*3600.d0)) + (dcos(oblq)*dpsi)
!
      sidtim = sidtim - (gclong * convd)
!
!   ROTATION RATE OF SITE IN KM/SEC
!
      sidtim = dmod(sidtim,twopi)
!
!   VECTOR VELOCITY REFERENCED TO TRUE EQUATOR AND ECLIPTIC.
!
      vrot = (rad * dcos(gclat * convd)) * sfract
!
      v1(1) = - (vrot * dsin(sidtim))
      v1(2) = vrot * dcos(sidtim)
!
!   ROTATE TO MEAN EQUATOR AND ECLIPTIC
!
      v1(3) = 0.d0
      do 20 j = 1, 3
        vel(j) = 0.d0
        do 20 i = 1, 3
!
!   VELOCITY OF E-M BARYCENTER RELATIVE TO SUN.
!   TO BE MORE ACCURATE VELOCITY OF SUN RELATIVE TO SS BARYCENTER SHOULD
! BE
!   COMPUTED.
!
   20   vel(j) = vel(j) + (nut(i,j) * v1(i))
      e1 = es(t)
      w1 = ws(t)
!
!   TRUE ANOMALY.
!
      a1 = anoms(t)
      av1 = atrue(a1,e1)
!
!   VECTOR VELOCITY REFERENCED TO ECLIPTIC.
!
      vrev = dsqrt(((emass+smass)+ammass)/(as*(1.d0-(e1*e1))))
      v1(1) = - (vrev * (dsin(av1 + w1) + (e1 * dsin(w1))))
!
!   ELEMENTS FOR MOON
!
      v1(2) = vrev * (dcos(av1 + w1) + (e1 * dcos(w1)))
      o2 = omegam(t)
      w2 = wm(t)
      a2 = anomm(t)
      av2 = atrue(a2,e2)
      vrev = dsqrt((emass + ammass) / (am * (1.d0 - (e2 * e2)))) /  &
        82.3d0
!
      co = dcos(o2)
      so = dsin(o2)
      ci = dcos(aim)
      si = dsin(aim)
      cl = dcos(av2 + w2)
      sl = dsin(av2 + w2)
      cw = dcos(w2)
!
!   ADD VELOCITY OF EARTH TO V1, MAKING SURE SIGN IS CORRECT.
!
      sw = dsin(w2)
      v1(1) = v1(1) + (vrev * ((co * (sl + (e2 * sw))) + ((ci * so) * &
             (cl + (e2 * cw)))))
      v1(2) = v1(2) + (vrev * ((so * (sl + (e2 * sw))) - ((ci * co) * &
             (cl + (e2 * cw)))))
!
!   ROTATE TO MEAN EQUATOR AND ECLIPTIC
!
      v1(3) = - ((vrev * si) * (cl + (e2 * cw)))
      oblq = oblqm(tc)
      cm = dcos(oblq)
      sm = dsin(oblq)
      vel(1) = vel(1) + v1(1)
      vel(2) = (vel(2) + (v1(2) * cm)) - (v1(3) * sm)
!
!   CURRENT ELEMENTS OF EARTH'S ORBIT.
!
      vel(3) = (vel(3) + (v1(2) * sm)) + (v1(3) * cm)
      e1 = es(t)
      ob1 = oblqm(tc)
      w1 = ws(t)
!
!   TRUE ANOMALY.
!
      a1 = anoms(t)
!
!   TRUE ECLIPTIC LONGITUDE OF SUN.
!
      av1 = atrue(a1,e1)
!
!   DISTANCE TO SUN.
!
      slong = (av1 + w1) + (180.d0 * convd)
!
!   RECTANGULAR COORDINATES OF SUN (RELATIVE TO EARTH).
!
      sund = (sundis * (1.d0 - (e1 * e1))) / (1.d0 + (e1 * dcos(av1)))
!
      sun(1) = sund * dcos(slong)
      sun(2) = (sund * dsin(slong)) * dcos(ob1)
      sun(3) = (sund * dsin(slong)) * dsin(ob1)
      return 
      end
!
!   'JULIAN' COMPUTES THE DECIMAL JULIAN DATE FROM A GREGORIAN CALENDAR
!   DATE AND TIME IN UTC. WORKS FOR ANY INPUT TIME.
!
!   IYEAR   =  YEAR NUMBER (INTEGER*4). IYEAR = 0 FOR 1 B.C. ETC.
!   IMONTH  =  MONTH NUMBER (INTEGER*4).
!   IDAY    =  DAY NUMBER (INTEGER*4).
!   UTC     =  COORDINATED UNIVERSAL TIME IN DECIMAL HOURS (REAL*8).
!   RJD     =  RETURNED JULIAN DATE (DECIMAL DAYS). REAL*8.
!
!   JULIAN DATE   RJD = 2305447.0  ON 1600 JAN 0.5 UTC (GREGORIAN
!   CALENDAR) IS THE FIDUCIAL POINT USED BY 'JULIAN'. FIDUCIAL POINT 
!   MUST BE A YEAR DIVISIBLE BY 400.
!
      subroutine julian(iyear, imonth, iday, utc, rjd)
      real*8 rjd, utc
      integer*2 mon(12)
!
!   ADD EXTRA DAY FOR LEAP YEAR.
!
      data mon / 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334 /
      data ifid / 1600 /
      data jdfid / 2305447 /
!
      lyr = 0
      if (((iyear / 4) * 4) .eq. iyear) lyr = 1
      if (((iyear / 100) * 100) .eq. iyear) lyr = 0
      if (((iyear / 400) * 400) .eq. iyear) lyr = 1
!
!   NDAY IS THE DAY NUMBER OF THE YEAR.
!
      if (imonth .le. 2) lyr = 0
!
!   GET J.D. FOR JAN 0.5 UTC IN REQUIRED YEAR.
!
      nday = (mon(imonth) + iday) + lyr
!
      if (iyear .gt. ifid) then
      iy = iyear - ifid
      rjd = ((((jdfid + (iy * 365.d0)) + ((iy - 1) / 4)) + 1) - ((iy - 1 &
        ) / 100)) + ((iy - 1) / 400)
!
      else if (iyear .eq. ifid) then
      rjd = jdfid
      else if (iyear .lt. ifid) then
      iy = ifid - iyear
      rjd = (((jdfid - (iy * 365.d0)) - (iy / 4)) + (iy / 100)) - (iy /  &
        400)
!
!   ADD ON THE DAYS AND HOURS COMPONENT.
!
      end if
!
      rjd = ((rjd + nday) + (utc / 24.d0)) - .5d0
      return 
      end
!
!   PERFORMS ROTATION X(I)=ROT(I,J)*Y(J) SUM ON J; IDIR=1.
!   PERFORMS ROTATION Y(J)=ROT(I,J)*X(I) SUM ON I; IDIR=-1.
!
      subroutine rotat(x, y, rot, idir)
      real*8 ra, dec, convd
      real*8 rdec, rra, cdec
      real*8 x(3), y(3), rot(3, 3), xx(3)
      data convd / 1.7453292519943296d-2 /
      if (idir .lt. 0) goto 10
      do 2 i = 1, 3
      x(i) = 0.d0
      do 2 j = 1, 3
    2 x(i) = x(i) + (rot(i,j) * y(j))
      return 
   10 continue
      do 12 j = 1, 3
      y(j) = 0.d0
      do 12 i = 1, 3
   12 y(j) = y(j) + (rot(i,j) * x(i))
      return 
!
!   CONVERTS R.A. AND DEC. TO COORDINATE VECTOR XX(I): MODE=1
!   CONVERTS COORDINATE VECTOR XX(I) TO R.A. AND DEC.: MODE=-1
!
!
      entry vector(xx, ra, dec, mode)
!
      if (mode .lt. 0) goto 17
      rra = (ra * convd) * 15.d0
      rdec = dec * convd
      cdec = dcos(rdec)
      xx(1) = cdec * dcos(rra)
      xx(2) = cdec * dsin(rra)
      xx(3) = dsin(rdec)
      return 
   17 continue
  100 format(1x,3d15.8)
      ra = datan2(xx(2),xx(1)) / (convd * 15.d0)
      if (ra .lt. 0.d0) ra = ra + 24.d0
      dec = dasin(xx(3)) / convd
      return 
      end
!
!   'AZEL' COMPUTES THE SIDERIAL TIME, HOUR ANGLE, TRUE (NOT REFRACTED)
!   ELEVATION AND AZIMUTH OF AN OBSERVED OBJECT. IF TRUE ELEVATION ABOVE
!   -35 ARCMIN IT ALSO COMPUTES REFRACTED COORDINATES, ELEVATION AND 
!   AIRMASS.
!
!   RJD     =  JULIAN DATE (DECIMAL DAYS) OF OBSERVATION. (REAL*8).
!   GCLONG  =  LONGITUDE (DECIMAL DEGREES) OF OBSERVING SITE (REAL*8).
!   GDLAT   =  GEODETIC LATITUDE OF SITE (DECIMAL DEGREES). (REAL*8).
!   RA      =  RIGHT ASCENSION (DECIMAL HOURS) OF OBJECT. (REAL*8).
!   DEC     =  DECLINATION (DECIMAL HOURS) OF OBJECT. (REAL*8).
!              NOTE THAT THESE SHOULD BE TRUE COORDINATES FOR THE EPOCH,
!              CORRECTED FOR ABERRATION.
!   SIDTIM  =  LOCAL SIDERIAL TIME AT SITE AT TIME 'RJD'. (REAL*8).
!   HA      =  HOUR ANGLE OF OBJECT (REAL*8). HA, SIDTIM IN DECIMAL 
!              HOURS.
!   EL      =  TRUE (UNREFRACTED) ELEVATION OF OBJECT IN DECIMAL DEGREES
!.
!              (REAL*8).
!   AZ      =  AZIMUTH OF OBJECT IN DECIMAL DEGREES (REAL*8).
!   RAR     =  REFRACTION CORRECTED R.A. (DECIMAL HOURS). REAL*8.
!   DECR    =  REFRACTION CORRECTED DEC. (DECIMAL DEGREES). REAL*8.
!   ELR     =  REFRACTED ELEVATION OF OBJECT.
!   AIRMSS  =  VALUE OF THE AIRMASS (REAL*8) RETURNED.
!
      subroutine azel(rjd, gclong, gdlat, ra, dec, sidtim, ha, el, az,  &
        rar, decr, elr, airmss)
      implicit real*8 (o-z, a-h)
!
      data pi / 3.1415926535897932d0 /
      data twopi / 6.2831853071795865d0 /
      data convd / 1.7453292519943296d-2 /
      data convds / 4.8481368110953599d-6 /
      data convhs / 7.2722052166430399d-5 /
!
!   TEST FOR VALID TIME RANGE.
!   CONVERT INPUT JULIAN DATE.
!
      if ((rjd .lt. 2378494.d0) .or. (rjd .gt. 2524959.d0)) return 
      t = idnint(rjd) - 2415020.5d0
!
!   CALCULATE LOCAL SIDERIAL TIME.
!
      utc = ((rjd - idnint(rjd)) + .5d0) * 24.d0
!
      sidtmo = 1.73993589472d0 + (t * (1.7202791266d-2 + (t *  &
             5.06409d-15)))
      sfract = 7.2921158546827d-5 + (t * 1.1727115d-19)
      sidtim = (((sidtmo + ((sfract * utc) * 3600.d0)) / convd)-gclong) &
             / 15.d0
      sidtim = dmod(sidtim,24.d0)
!
!   HOUR ANGLE
!
      if (sidtim .lt. 0.d0) sidtim = sidtim + 24.d0
      ha = sidtim - ra
      if (ha .le. (-12.d0)) ha = ha + 24.d0
      if (ha .gt. 12.d0) ha = ha - 24.d0
      rha = (ha * 15.d0) * convd
      cha = dcos(rha)
      sha = dsin(rha)
      rdec = dec * convd
      cdec = dcos(rdec)
      sdec = dsin(rdec)
      rlat = gdlat * convd
      clat = dcos(rlat)
!
!   COSINE OF ZENITH ANGLE.
!
      slat = dsin(rlat)
      cosz = (slat * sdec) + ((clat * cdec) * cha)
      el = dasin(cosz) / convd
      az = datan2(- (cdec * sha),(sdec * clat) - ((cdec * cha) * slat)) &
         / convd
      if (az .lt. 0.d0) az = az + 360.d0
!
!   COMPUTE REFRACTED ELEVATION AND AIRMASS.
!
      if (el .lt. (- (35.d0 / 60.d0))) return 
      if (el .gt. (4.d0 + (50.d0 / 60.d0))) then
        sinz = dsin((90.d0 - el) * convd)
        tanz = sinz / cosz
        elr = el + (((58.3 * tanz) - (0.067 * (tanz ** 3))) / 3600.d0)
        secz = 1.d0 / cosz
        chi = secz - 1.d0
        airmss = secz - (chi * (.0018167d0 + (chi * (.002875d0 + (chi *  &
             0.0008083d0)))))
      else
      zt = 90.d0 - el
      theta = ((-287.8165098d0) + (7.792832093d0 * zt)) - (( &
             0.0401680058d0 * zt) * zt)
!
      airmss = 1.0d0 / dcos(theta * convd)
      elr = el + ((55.2053 * airmss) / 3600.d0)
      end if
      caz = dcos(az * convd)
      saz = dsin(az * convd)
      celr = dcos(elr * convd)
!
!   COSINE OF ANGLE FROM NORTH POLE.
!
      selr = dsin(elr * convd)
!
      cpole = (slat * selr) + ((clat * celr) * caz)
!
!   NEW HOUR ANGLE.
!
      decr = dasin(cpole) / convd
!
!   NEW R.A.
!
      hanew = datan2(-(celr*saz),(selr*clat)-((celr*caz)*slat)) &
             / (convd * 15.d0)
      rar = dmod(sidtim - hanew,24.d0)
      if (rar .lt. 0.d0) rar = rar + 24.d0
      return 
      end
!
!   'GALAXY' CONVERTS EPOCH 1950.0 MEAN R.A. AND DEC. TO GALACTIC
!   COORDINATES, AND VICE VERSA.
!
!   RA     =  EPOCH 1950.0 R.A. (DECIMAL HOURS). (REAL*8).
!   DEC    =  EPOCH 1950.0 DEC. (DECIMAL DEGREES). (REAL*8).
!   GLAT   =  GALACTIC LATITUDE (SYSTEM II). (REAL*8).
!   GLONG  =  GALACTIC LONGITUDE (SYSTEM II). (REAL*8).
!   IDIR   =  MODE SELECTOR (INTEGER*4). IF IDIR = -1 THEN CONVERT 
!             GALACTIC
!             TO EQUATORIAL COORDINATES. OTHERWISE CONVERT EQUATORIAL TO
!             GALACTIC COORDINATES.
!
      subroutine galaxy(ra, dec, glat, glong, idir)
      implicit real*8 (o-z, a-h)
      dimension r(3, 3), g(3), e(3)
!
!   GALACTIC   COORDINATES PI,THETA,Z IN G(3),EQUATORIAL X,Y,Z IN E(3).
!   CONVERSION: G(I)=R(I,J)*E(J), SUM ON J.
!   INVERSE:    E(J)=R(I,J)*G(I), SUM ON I.
!
      data r / -.066988740d0, .492728466d0, -.867600811d0, -.872755766d0 &
        , -.450346958d0, -.188374601d0, -.483538915d0, .744584633d0,  &
        .460199785d0 /
      data raddeg / 57.29577951d0 /
      data radhr / 3.8197186335d0 /
!
      if (idir .eq. (-1)) goto 50
      rra = ra / radhr
      rdec = dec / raddeg
      cdec = dcos(rdec)
      e(1) = cdec * dcos(rra)
      e(2) = cdec * dsin(rra)
      e(3) = dsin(rdec)
      do 5 i = 1, 3
      g(i) = 0.
      do 5 j = 1, 3
    5 g(i) = g(i) + (e(j) * r(i,j))
      glat = dasin(g(3)) * raddeg
      glong = datan2(g(2),g(1)) * raddeg
      if (glong .lt. 0.d0) glong = glong + 360.d0
      return 
   50 continue
      rglat = glat / raddeg
      rglong = glong / raddeg
      clat = dcos(rglat)
      g(1) = clat * dcos(rglong)
      g(2) = clat * dsin(rglong)
      g(3) = dsin(rglat)
      do 55 j = 1, 3
      e(j) = 0.
      do 55 i = 1, 3
   55 e(j) = e(j) + (r(i,j) * g(i))
      dec = dasin(e(3)) * raddeg
      ra = datan2(e(2),e(1)) * radhr
      if (ra .lt. 0.) ra = ra + 24.d0
      return 
      end
!
!   'ABERR' CORRECTS THE COORDINATES OF AN OBJECT FOR THE SPECIAL 
!   RELATIVISTIC ABERRATION OF LIGHT.
!
!   RA     =  RIGHT ASCENSION OF OBJECT (DECIMAL HOURS). (REAL*8).
!   DEC    =  DECLINATION OF OBJECT (DECIMAL DEGREES). (REAL*8).
!   VEL    =  3-D VELOCITY VECTOR OF EARTH IN KM/SEC IN RECTANGULAR
!             GEOCENTRIC COORDINATES.
!   RAA    =  ABERRATION CORRECTED R.A. (DECIMAL HOURS). (REAL*8).
!   DECA   =  ABERRATION CORRECTED DEC. (DECIMAL DEGREES). (REAL*8).
!
      subroutine aberr(ra, dec, vel, raa, deca)
      implicit real*8 (o-z, a-h)
      real*8 r(3), rnew(3), vel(3)
      data c / 299792.456d0 /
      data convd / 1.7453292519943296d-2 /
      data convds / 4.8481368110953599d-6 /
!
!   CALCULATE OBJECT COORDINATE VECTOR FROM RA,DEC.
!
      r(1) = dcos(dec * convd) * dcos((ra * convd) * 15.d0)
      r(2) = dcos(dec * convd) * dsin((ra * convd) * 15.d0)
!
!   PHOTONS FROM OBJECT HAVE VELOCITY VECTOR = -C*R(I).
!   VELOCITY VECTOR OF EARTH = VEL(I).
!   USE SPECIAL RELATIVISTIC VELOCITY TRANSFORM TO GET VELOCITY VECTOR
!   OF PHOTONS AS SEEN FROM EARTH  = RNEW(I).
!
!
      r(3) = dsin(dec * convd)
!
      ve2 = ((vel(1) ** 2) + (vel(2) ** 2)) + (vel(3) ** 2)
      gamma2 = 1.d0 / dsqrt(1.d0 - (ve2 / (c * c)))
      delta2 = 1.d0 / ((c * c) * (1.d0 + (1.d0 / gamma2)))
      v12 = - ((((r(1) * vel(1)) + (r(2) * vel(2))) + (r(3) * vel(3))) &
         * c)
!
      gam12 = 1.d0 - (v12 / (c * c))
      rnew(1) = (((((v12 * delta2) * vel(1)) + (((ve2 * delta2) * c) * r &
        (1))) - (c * r(1))) - vel(1)) / gam12
!
      rnew(2) = (((((v12 * delta2) * vel(2)) + (((ve2 * delta2) * c) * r &
        (2))) - (c * r(2))) - vel(2)) / gam12
!
!   NEW COORDINATE VECTOR = -RNEW(I)/C.
!
      rnew(3) = (((((v12 * delta2) * vel(3)) + (((ve2 * delta2) * c) * r &
        (3))) - (c * r(3))) - vel(3)) / gam12
!
      rnew(1) = - (rnew(1) / c)
      rnew(2) = - (rnew(2) / c)
!
!   TRANSFORM NEW COORDINATE VECTOR INTO R.A. AND DEC. VALUES.
!
      rnew(3) = - (rnew(3) / c)
!
      raa = datan2(rnew(2),rnew(1)) / (convd * 15.d0)
      if (raa .lt. 0.d0) raa = raa + 24.d0
      deca = dasin(rnew(3)) / convd
      return 
      end
