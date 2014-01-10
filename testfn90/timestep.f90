    subroutine timestep(u,n,m,dx,dy,error)
    real*8 u(n,m)
    real*8 dx,dy,dx2,dy2,dnr_inv,tmp,diff, error
    integer n,m,i,j
!f2py intent(in) :: dx,dy
!f2py intent(in,out) :: u
!f2py intent(out) :: error
!f2py intent(hide) :: n,m
    dx2 = dx*dx
    dy2 = dy*dy
    dnr_inv = 0.5d0 / (dx2+dy2)
    error = 0d0
    do 200,j=2,m-1
        do 100,i=2,n-1
            tmp = u(i,j)
            u(i,j) = ((u(i-1,j) + u(i+1,j))*dy2+(u(i,j-1) + u(i,j+1))*dx2)*dnr_inv
            diff = u(i,j) - tmp
            error = error + diff*diff
100     continue
200  continue
    error = sqrt(error)
end