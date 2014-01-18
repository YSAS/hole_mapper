!
!  Program to calculate x,y coords in the focal plane of either
!  Magellan telescope (with and/or without a WFC/ADC).
!
!  This program must run after the stars to be observed are
!  selected and vetted for collisions, uniform distribution over
!  the field, and ordered for observing/assignment.
!
!     For reference, the sizes associated with each hole type are given
!     here (in inches):
!
!     0.260 = thumbscrews     = T  (1/4-20 screws)
!     0.260 = dowelpins       = F
!     0.166 = fibers          = O, S, X  (object and sky; Nominal
!                               ferrule size is 0.1654)
!                               A --> acquisitions (added Nov 06)
!     0.316 = guidefibers     = G  (Ferrule is 0.311)
!     0.129 = guidefiber pins = R  (Pins are 0.1255-0.1265)
!
!
!     For each star, the standard coords (xi and eta) are calculated.
!     The date and target time of observation is specified (from a file
!     or directly).  Correct for differential aberration relative to
!     field center and determine new xi,eta values.  Calculate
!     differential refraction over the field and correct to get apparent
!     xi,eta.  Apply focal plane transformation to determine x,y from
!     apparent xi,eta.  Flip coords to determine machine x,y coords.
!     Add positions of reference dowels and guide fibers.
!
!
      subroutine m2fsholesxy(ut, utdate, lat, long, height, &
        rafield,decfield,epochfield,fieldrot, nstar, rastars, decstars, &
        epochstars, type, xm, ym, zm, sizem, type_out, sidtime, hangle, azimuth, &
        elevation, airmass, nmax, nout)
!
      implicit real*8 (a-h,o-z)
      integer i
      integer tconfig
      integer nmax,nstar,nout
      integer utdate(3)
!
      parameter(tconfig=3)
      parameter(rmax = 12.750)    ! in inches.
      real*8 rafield,decfield,epochfield,fieldrot
      real*8 raplugfield,decplugfield,fpochfield
      real*8 ut,long,lat,height
      real*8 airmass,elevation,azimuth,hangle,sidtime
      real*8 rastars(nstar),decstars(nstar),epochstars(nstar)
      character*1 type(nstar)

      real*8 raplugstars(nmax),decplugstars(nmax),fpochstars(nmax)
      real*8 xi(nmax),eta(nmax)
      real*8 x(nmax),y(nmax)
      real*8 xm(nmax),ym(nmax),zm(nmax),sizem(nmax)
!
      character*1 type_out(nmax)

!f2py intent(hide) nstar
!f2py integer, optional,intent(hide),depend(rastars) :: nmax=len(rastars)+100
!f2py intent(in) ut
!f2py intent(in) utdate
!f2py intent(in) long
!f2py intent(in) lat
!f2py intent(in) height
!f2py intent(in) rafield
!f2py intent(in) decfield
!f2py intent(in) epochfield
!f2py intent(in) fieldrot
!f2py intent(in) rastars
!f2py intent(in) decstars
!f2py intent(in) epochstars
!f2py intent(in) tconfig
!f2py intent(in) type
!
!f2py intent(out) xm
!f2py intent(out) ym
!f2py intent(out) zm
!f2py intent(out) sizem
!f2py intent(out) sidtime
!f2py intent(out) type_out
!f2py intent(out) hangle
!f2py intent(out) azimuth
!f2py intent(out) elevation
!f2py intent(out) airmass
!f2py intent(out) nout
!

        do i=1,nstar
            type_out(i)=type(i)
        end do

        call fruitfield(long,lat,height,epochfield,rafield,decfield, &
           utdate,ut,fpochfield,raplugfield,decplugfield)

        call fruitstars(long,lat,height,epochstars,rastars,decstars, &
           utdate,ut,fpochstars,raplugstars,decplugstars,nstar)
        call calcstandard(raplugstars,decplugstars,fpochstars, &
           raplugfield,decplugfield,fpochfield,xi,eta,nstar)
        call transformxy(xi,eta,nstar,x,y,tconfig)
        call machinexyz(x,y,type,nstar,fieldrot,xm,ym,zm,sizem)
!
!  Add holes for specific types (guidestar reference holes (type=R),
!  thumbscrews (T), and outer fiducial pins (F).
!
!adds 3 + 4 + 1 (not yet) + 3*nG

        call guiderefholes(xm,ym,zm,sizem,type_out,nstar,nmax,fieldrot,rmax)
        call getfieldinfo(utdate,ut,raplugfield,decplugfield,lat,long, &
          sidtime,hangle,azimuth,elevation,airmass)
          
        nout=nstar
!
      end
!
!
!!!!!!!!!!!!
!
      subroutine m2fsholesxyplate(rafield,decfield,epochfield,fieldrot, nstar, &
          rastars, decstars, epochstars, xm, ym, zm, sizem, type_out, nmax)
      !
      implicit real*8 (a-h,o-z)
      integer i
      integer tconfig
      integer nmax,nstar
      !
      parameter(tconfig=3)

      real*8 rafield,decfield,epochfield,fieldrot
      real*8 rastars(nstar),decstars(nstar),epochstars(nstar)

      real*8 x(nstar),y(nstar)
      real*8 xi(nstar),eta(nstar)

      real*8 xm(nmax),ym(nmax),zm(nmax),sizem(nmax)
      character*1 type_out(nmax)

      !f2py intent(hide) nstar
      !f2py integer, optional,intent(hide),depend(rastars) :: nmax=len(rastars)+7
      !f2py intent(in) rafield
      !f2py intent(in) decfield
      !f2py intent(in) epochfield
      !f2py intent(in) fieldrot
      !f2py intent(in) rastars
      !f2py intent(in) decstars
      !f2py intent(in) epochstars
      !f2py intent(in) tconfig

      !
      !f2py intent(out) xm
      !f2py intent(out) ym
      !f2py intent(out) zm
      !f2py intent(out) sizem

      !f2py intent(out) type_out

      do i=1,nstar
        type_out(i)='Z'
      end do

      call calcstandard(rastars,decstars,epochstars, &
            rafield,decfield,epochfield,xi,eta,nstar)
      call transformxy(xi,eta,nstar,x,y,tconfig)
      call machinexyz(x,y,type_out,nstar,fieldrot,xm,ym,zm,sizem)
      call fiducialholes(xm,ym,zm,sizem,type_out,nstar,nmax)
      call thumbscrewholes(xm,ym,zm,sizem,type_out,nstar,nmax)

      end
!
!
!!!!!!!!!!!!
!
      subroutine fruitfield(long,lat,height,epochfield,rafield,decfield, &
           utdate,ut,fpochfield,raplugfield,decplugfield)
!
      implicit real*8 (a-h,o-z)
      parameter(radian=57.295779513d0,epsilon=1.0d-8)
      real*8 rafield,decfield,epochfield
      real*8 raplugfield,decplugfield
      real*8 long,lat,ut,height
      real*8 latrad,longrad,date
      real*8 ramap,raob,decmap,decob
      integer utdate(3)
!
      call getmjd(utdate,ut,date)
!      print *,'In fruitfield info:  date = ',date
      latrad = lat/radian
      longrad = -long/radian
      rm = rafield/radian
      dm = decfield/radian
      call getrefparams(tempk,pressure,relhum,alambda,tlr,pr,pd,px,rv, &
          dut,xp,yp)
      call sla_MAP(rm,dm,pr,pd,px,rv,epochfield,date,ramap,decmap)
      call sla_AOP(ramap,decmap,date,dut,longrad,latrad,height, &
          xp,yp,tempk,pressure,relhum,alambda,tlr,aob,zob,hob, &
          decob,raob)
      raplugfield = raob*radian
      decplugfield = decob*radian
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine fruitstars(long,lat,height,epoch,ra,dec, &
           utdate,ut,fpoch,raplug,decplug,nstars)
!
      implicit real*8 (a-h,o-z)
      parameter(radian=57.295779513d0,epsilon=1.0d-8)
      real*8 ra(nstars),dec(nstars),epoch(nstars)
      real*8 raplug(nstars),decplug(nstars),fpoch(nstars)
      real*8 ramap,raob,decmap,decob
      real*8 long,lat,ut,height
      real*8 longrad,latrad,date
      integer utdate(3),i
!
      call getmjd(utdate,ut,date)
!      print *,'In fruitstars info:  date = ',date
      latrad = lat/radian
      longrad = -long/radian
      do i=1,nstars
        rm = ra(i)/radian
        dm = dec(i)/radian
        call getrefparams(tempk,pressure,relhum,alambda,tlr,pr,pd,px,rv, &
          dut,xp,yp)
        call sla_MAP(rm,dm,pr,pd,px,rv,epoch(i),date,ramap,decmap)
        call sla_AOP(ramap,decmap,date,dut,longrad,latrad,height, &
          xp,yp,tempk,pressure,relhum,alambda,tlr,aob,zob,hob, &
          decob,raob)
        raplug(i) = raob*radian
        decplug(i) = decob*radian
        fpoch(i) = epoch(i)
      end do
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine calcstandard(raplugstars,decplugstars,fpochstars, &
           raplugfield,decplugfield,fpochfield,xi,eta,nstar)
!
      implicit real*8 (a-h,o-z)
      parameter(radian=57.295779513d0)
      real*8 raplugstars(nstar),decplugstars(nstar),fpochstars(nstar)
      real*8 raplugfield,decplugfield,fpochfield
      real*8 xi(nstar),eta(nstar)
      real*8 ra,dec,raf,decf
      real*8 xisla,etasla,ra1,dec1,raf1,decf1
!      real*8 xifield,etafield
      integer i
!
      raf = raplugfield
      decf = decplugfield
!      call calcxi(raf,decf,raf,decf,xifield)
!      call calceta(raf,decf,raf,decf,etafield)
      do i=1,nstar
        ra = raplugstars(i)
        dec = decplugstars(i)
!        call calcxi(ra,dec,raf,decf,xi1)
!        call calceta(ra,dec,raf,decf,eta1)
!        xi(i) = xi1
!        eta(i) = eta1
        ra1 = ra/radian
        dec1 = dec/radian
        raf1 = raf/radian
        decf1 = decf/radian
        call sla_DS2TP(ra1,dec1,raf1,decf1,xisla,etasla,j)
        xi(i) = xisla*radian
        eta(i) = etasla*radian
      end do
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine transformxy(xi,eta,nstar,x,y,tconfig)
      implicit real*8 (a-h,o-z)
      integer tconfig,npts,mpts,ncoefs,mcoefs,i
      parameter(mpts=100,mcoefs=20)
      real*8 xi(nstar),eta(nstar)
      real*8 x(nstar),y(nstar)
      real*8 theta(mpts),r(mpts),sigma(mpts)
      real*8 coefs(mcoefs)
!
!  This routine operates in mm and degrees.
!
      call getcoefs(tconfig,coefs,ncoefs,mcoefs)
      do i=1,nstar
        call applyfit(xi(i),eta(i),coefs,ncoefs,x(i),y(i))
      end do
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine getcoefs(tconfig,coefs,ncoefs,mcoefs)
      implicit real*8 (a-h,o-z)
      integer tconfig,ncoefs,mcoefs,i
      real*8 coefs(mcoefs)
!
      if(tconfig.eq.3) then
        ncoefs = 8
        coefs(1) =  0.00D00
        coefs(2) =  1.239854010854D03
        coefs(3) = -2.329206669614D00
        coefs(4) =  4.652254793249D02
        coefs(5) = -2.132144915069D02
        coefs(6) =  1.314666842188D03
        coefs(7) =  8.430220481713D02
        coefs(8) =  4.212939454947D02
      else
        stop
      end if
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine applyfit(xi,eta,coefs,ncoefs,x,y)
!
!  Coefs for the fit for the M2FS scale are based on field angles in DEGREES.
!
      implicit real*8 (a-h,o-z)
      real*8 xi,eta,x,y,coefs(ncoefs),basis(ncoefs)
      real*8 theta,r,alpha
      integer i
      external polynomial
!
      if(xi.eq.0.0.and.eta.eq.0.0) then
        x = 0.0
        y = 0.0
        return
      end if
!
      alpha = datan2(eta,xi)
      theta = dsqrt(xi**2 + eta**2)
      call polynomial(theta,basis,ncoefs)
      r = 0.0
      do i=1,ncoefs
        r = r + basis(i)*coefs(i)
      end do
      x = r*dcos(alpha)
      y = r*dsin(alpha)
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine polynomial(x,p,np)
      implicit real*8 (a-h,o-z)
      real*8 x,p(np)
      integer np,i
!
      p(1) = 1.0
      do i=2,np
        p(i) = p(i-1)*x
      end do
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine machinexyz(x,y,type,nstar,fieldrot,xm,ym,zm,sizem)
      implicit real*8 (a-h,o-z)
      real*8 x(nstar),y(nstar)
      real*8 xm(nstar),ym(nstar),zm(nstar)
      real*8 sizem(nstar)
      real*8 dz,size,fieldrot
      integer nstar,i
      character*1 type(nstar)
      parameter(convert=25.4)
!
!  Parity is such that from the convex side of the plate, positive
!  x (east) maps to positive ym, and positive y (north) maps to
!  positive xm.  The zm assumes a distance from a tangent plane that
!  passes 1/16 + 1/32 = 3/32 inch above the center of the plugplate
!  and perpendicular to the optical axis.
!
!  Note the need to convert x,y,dz in mm to xm,ym,zm in inches.
!
      do i=1,nstar
        xm(i) = y(i)/convert
        ym(i) = x(i)/convert
        call zoffset(x(i),y(i),dz)
        zm(i) = dz/convert
        call getsize(type(i),size)
        sizem(i) = size
        call rotfield(xm(i),ym(i),fieldrot,type(i))
      end do
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine zoffset(x,y,dz)
      implicit real*8 (a-h,o-z)
      real*8 x,y,dz
      real*8 rp,rp2,r2,dzmin
!
!  This plate radius is for the convex surface plus 3/32 inch.
!  Note the messy units; the x,y are in mm; so is dz. dzmin is
!  in inches times 25.4 to compare with dz in mm.
!
      parameter(rp=51.02*25.4,dzmin=-1.500*25.4)
!
      rp2 = rp**2
      r2 = x**2 + y**2
      dz = rp - dsqrt(rp**2 - r2)
      dz = dmax1(-dz,dzmin)
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine getsize(type,size)
      implicit real*8 (a-h,o-z)
      real*8 size,starsize,guidesize
      character*1 type
      parameter(starsize=0.1660,guidesize=0.316)
!
!  All this is mercifully in inches.
!
      if(type.eq.'O'.or.type.eq.'o') then
         size = starsize
         return
      else if(type.eq.'T'.or.type.eq.'t') then
         size = starsize
         return
      else if(type.eq.'S'.or.type.eq.'s') then
         size = starsize
         return
      else if(type.eq.'A'.or.type.eq.'a') then
         size = starsize
         return
      else if(type.eq.'X'.or.type.eq.'x') then
         size = starsize
         return
      else if(type.eq.'Z'.or.type.eq.'z') then
         size = starsize
         return
      else if(type.eq.'G'.or.type.eq.'g') then
         size = guidesize
         return
      else
         size = 0.00
      end if
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine guiderefholes(xm,ym,zm,sizem,type,nstar,nmax,fieldrot,rmax)
      implicit real*8 (a-h,o-z)
      real*8 xm(nmax),ym(nmax),zm(nmax),sizem(nmax)
      real*8 fieldrot,rr,rmax
      integer nstar,nmax,i
      character*1 type(nmax)
!
      ng = 0
      do i=1,nstar
        rr = dsqrt(xm(i)**2 + ym(i)**2)
        if(rr.le.rmax.and.(type(i).eq.'G'.or.type(i).eq.'g')) then
          ng = ng + 1
          call guiderefoffsets(xm,ym,zm,sizem,type,nmax,nstar,i,ng,1,fieldrot)
          call guiderefoffsets(xm,ym,zm,sizem,type,nmax,nstar,i,ng,2,fieldrot)
          call guiderefoffsets(xm,ym,zm,sizem,type,nmax,nstar,i,ng,3,fieldrot)
        end if
      end do
      nstar = nstar + ng*3
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine guiderefoffsets(xm,ym,zm,sm,ty,nmax,nstar,is,ng,nref, &
          fieldrot)
      implicit real*8 (a-h,o-z)
      real*8 xm(nmax),ym(nmax),zm(nmax),sm(nmax)
      real*8 xoffsets(3),yoffsets(3)
      real*8 sizerefhole,fieldrot,sign
      data xoffsets / 0.000, -0.2165, 0.2165 /
      data yoffsets / 0.250, -0.125, -0.125 /
      parameter(sizerefhole=0.1285,convert=25.4)
      character*1 ty(nmax)
!
      sign = 1.0
      if(fieldrot.eq.180.0) sign = -1.0
      ii = nstar + (ng-1)*3 + nref
      xm(ii) = xm(is) + sign*xoffsets(nref)
      ym(ii) = ym(is) + sign*yoffsets(nref)
      call zoffset(xm(ii)*convert,ym(ii)*convert,dz)
      zm(ii) = dz/convert
      sm(ii) = sizerefhole
      ty(ii) = 'R'
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine fiducialholes(xm,ym,zm,sizem,type,nstar,nmax)
      implicit real*8 (a-h,o-z)
      real*8 xm(nmax),ym(nmax),zm(nmax),sizem(nmax)
      real*8 xoffsets(4),yoffsets(4)
      real*8 sizefidhole,zoffset
      integer i
      data xoffsets / -13.750, 13.750, -13.750, 13.750 /
      data yoffsets / 2.500, 2.500, -2.500, -2.500 /
      parameter(sizefidhole=0.260,zoffset=-1.500)
      character*1 type(nmax)
!
!  All dimensions in inches.
!
      nfid = 4
      do i=1,nfid
        ii = nstar + i
        xm(ii) = xoffsets(i)
        ym(ii) = yoffsets(i)
        zm(ii) = zoffset
        sizem(ii) = sizefidhole
        type(ii) = 'F'
      end do
      nstar = nstar + nfid
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine thumbscrewholes(xm,ym,zm,sizem,type,nstar,nmax)
      implicit real*8 (a-h,o-z)
      real*8 xm(nmax),ym(nmax),zm(nmax),sizem(nmax)
      real*8 xoffsets(3),yoffsets(3)
      real*8 sizethumbhole,zoffset
      integer i
      data xoffsets / -12.125, -2.910, 12.790 /
      data yoffsets / 7.000, -13.695, 5.694 /
      parameter(sizethumbhole=0.260,zoffset=-1.500)
      character*1 type(nmax)
      character*7 id(nmax)
!
!  All dimensions in inches.
!
      nthumb = 3
      do i=1,nthumb
        ii = nstar + i
        xm(ii) = xoffsets(i)
        ym(ii) = yoffsets(i)
        zm(ii) = zoffset
        sizem(ii) = sizethumbhole
        type(ii) = 'B'
      end do
      nstar = nstar + nthumb
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine rotfield(xm,ym,fieldrot,type)
      real*8 xm,ym,fieldrot
      character*1 type
!
!  For now, accept ONLY fieldrot = 180 deg.  Any other value results
!  in no field rotation.
!
      if(fieldrot.eq.180.0) then
        if(type.ne.'F'.and.type.ne.'T') then
          xm = -xm
          ym = -ym
        end if
      end if
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine getrefparams(temp,press,rh,alambda,tlr,pr,pd,px,rv,dut, &
          xp,yp)
!
      implicit real*8 (a-h,o-z)
      temp = 293.0d0
      press = 780.0d0
      rh = 0.5d0
      alambda = 0.5d0
      tlr = 0.0065d0
      pr = 0.0d0
      pd = 0.0d0
      px = 0.0d0
      rv = 0.0d0
      dut = 0.0d0
      xp = 0.0d0
      yp = 0.0d0
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine getfieldinfo(utdate,ut,racen,deccen,lat,long,lsidtime, &
          hangle,azimuth,elevation,airmass)
      implicit real*8 (a-h,o-z)
      parameter (radian=57.295779513d0,fifteen=15.0d0)
      real*8 ut,date,lsidtime,lat,long,latrad
      integer utdate(3)
!
      call getmjd(utdate,ut,date)
      sidtime = sla_gmst(date)*radian
      lsidtime = sla_gmst(date)*radian - long
      hanglerad = (lsidtime - racen)/radian
      deccenrad = deccen/radian
      latrad = lat/radian
      call sla_DE2H(hanglerad,deccenrad,latrad,azimuth,elevation)
      airmass = sla_AIRMAS((90.0d0/radian) - elevation)
      lsidtime = lsidtime/fifteen
      hangle = hanglerad*radian/fifteen
      azimuth = azimuth*radian
      elevation = elevation*radian
      return
      end
!
!
!!!!!!!!!!!!
!
      subroutine getmjd(utdate,ut,date)
      implicit real*8 (a-h,o-z)
      real*8 ut,date
      integer utdate(3)
!
      call sla_CLDJ(utdate(3),utdate(2),utdate(1),date,j)
      if(j.ne.0) then
        print *,'CLDJ barfed; j = ',j
        stop
      end if
      date = date + ut/24.0d0
      return
      end
