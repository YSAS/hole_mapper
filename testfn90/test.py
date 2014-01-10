import numpy

def w1():

    sol,err,iter=w2(50)

    return (sol,err,iter)


def w2(num_points):

    j=numpy.complex(0,1)

    u=numpy.zeros((num_points,num_points),dtype=float)
    pi_c=float(numpy.pi)
    x=numpy.r_[0.0:pi_c:num_points*j]
    u[0,:]=numpy.sin(x)
    u[num_points-1,:]=numpy.sin(x)

    (sol,err,iter)=solve_laplace(u,pi_c/(num_points-1),pi_c/(num_points-1))


    return (sol,err,iter)

def solve_laplace(u,dx,dy):
    iter =0
    err = 2
    import timestep
    while(iter <10000 and err>1e-6):
        (u,err)=timestep.timestep(u,dx,dy)
        iter+=1
    return (u,err,iter)