"""
This file is part of the Avast project.
Copyright 2016 Megan Bedell (Chicago).
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter
from scipy.optimize import leastsq
c = 2.99792458e8

def unpack_pars(pars, n_ms, n_epoch):
    # unpack Parameters() object
    ams = pars[0:n_ms]
    scales = pars[n_ms:n_ms+n_epoch]
    vs = pars[n_ms+n_epoch:]
    return ams, scales, vs
    
def triangle(xs, xms, del_x):
    # returns values of triangle components centered on xms at location xs
    # xs & xms must be broadcastable
    return np.maximum(1. - np.abs(xs - xms)/del_x, 0.)
    
def model(xs, xms, del_x, ams):
    # returns values of triangle-based model at xs
    # xs : ln(wavelength) at point(s) of interest
    # xms : ln(wavelength) grid, shape (M)
    # del_x : ln(wavelength) spacing of xms
    # ams : function coefficients, shape (M)
    return np.sum(ams[None,:] * triangle(xs[:,None], xms[None,:], del_x), axis=1) 

def min_function(pars, xs, ys, xms, del_x):
    # function to minimize
    n_epoch = len(xs)
    n_ms = len(xms)
    ams, scales, vs = unpack_pars(pars, n_ms, n_epoch)
    resid = np.array([])
    for e in range(n_epoch):
        beta = vs[e] / c
        thisxs = xs[e] - 0.5 * np.log((1. + beta)/(1. - beta))
        calc = model(thisxs, xms, del_x, ams * scales[e])
        err = np.sqrt(ys[e])    # assumes Poisson noise 
        resid = np.append(resid,(ys[e] - calc) / err)
    return np.append(resid, np.append((scales - 1.) / 0.5, (vs - 0.) / 30.)) #MAGIC
    
def min_v(pars, i, xs, ys, xms, del_x):
    # do a simple minimzation of just one velocity parameter
    # i : epoch # to minimize, 0-2
    tmp_pars = np.copy(pars)    
    obj = []  # objective function
    v0 = []
    for v in np.linspace(vs[i]-50.,vs[i]+70.,100):
        tmp_pars[n_ms+n_epoch+i] = v
        resids = min_function(tmp_pars, xs, ys, xms, del_x)
        obj = np.append(obj, np.dot(resids,resids))
        v0 = np.append(v0,v)
    plt.clf()
    plt.plot(v0,obj)
    plt.axvline(vs[i])
    plt.xlabel('v')
    plt.ylabel('objective function')
    plt.savefig('objectivefn_v{0}.png'.format(i))
    v_min = v0[np.argmin(obj)]
    tmp_pars[n_ms+n_epoch+i] = v_min
    return tmp_pars
    
def save_plot(xs, obs, calc, x_plot, calc_plot, save_name):
    xs = np.e**xs
    x_plot = np.e**x_plot
    fig = plt.figure()

    ax1 = fig.add_subplot(2,1,1)
    ax1.step(xs,obs, color='black', label='Observed')
    ax1.plot(x_plot,calc_plot, color='red', label='Calculated')
    ax1.set_ylabel('Flux')
    #ax1.legend()
    ax1.set_xticklabels( () )
    ax2 = fig.add_subplot(2,1,2)
    ax2.step(xs,obs - calc, color='black')
    ax2.set_ylabel('(O-C)')
    ax2.ticklabel_format(useOffset=False)
    ax2.set_xlabel(r'Wavelength ($\AA$)')
    majorLocator = MultipleLocator(1)
    minorLocator = MultipleLocator(0.1)
    ax1.xaxis.set_minor_locator(minorLocator)
    ax1.xaxis.set_major_locator(majorLocator)
    ax2.xaxis.set_minor_locator(minorLocator)
    ax2.xaxis.set_major_locator(majorLocator)
    majorLocator = MultipleLocator(5000)
    ax1.yaxis.set_major_locator(majorLocator)
    majorLocator = MultipleLocator(200)
    ax2.yaxis.set_major_locator(majorLocator)
    ax2.set_ylim([-500,500])
    fig.subplots_adjust(hspace=0.05)
    plt.savefig(save_name)

if __name__ == "__main__":
    wave, spec = np.loadtxt('../data/test_spec1.txt', unpack=True)
    wave2, spec2 = np.loadtxt('../data/test_spec2.txt', unpack=True)
    wave3, spec3 = np.loadtxt('../data/test_spec3.txt', unpack=True)
    lnwave = np.log(wave)
    lnwave2 = np.log(wave2)
    lnwave3 = np.log(wave3)
    xs = [lnwave, lnwave2, lnwave3]
    ys = [spec, spec2, spec3]
    del_x = 1.3e-5/2.0
    xms = np.arange(np.min(lnwave) - 0.5 * del_x, np.max(lnwave) + 0.99 * del_x, del_x)
    
    # initial fit to ams & scales:
    fa = (xs, ys, xms, del_x)
    n_epoch = len(xs)
    n_ms = len(xms)
    ams0 = np.random.normal(size=n_ms) + np.median(ys[0])
    scales0 = np.ones(n_epoch)
    vs0 = np.random.normal(size=n_epoch) * 5.0
    pars0 = np.append(ams0, np.append(scales0, vs0))
    ftol = 1.49012e-08  # default is 1.49012e-08
    soln = leastsq(min_function, pars0, args=fa, ftol=ftol)

    # look at the fit:
    pars = soln[0]
    ams, scales, vs = unpack_pars(pars, n_ms, n_epoch)
    resids = min_function(pars, xs, ys, xms, del_x)
    print "Initial optimization of all parameters:"
    print "Objective function value: {0}".format(np.dot(resids,resids))
    print "Velocities:", vs
    
    # optimize one epoch at a time:
    for i in [0,1,2]:
        pars = min_v(pars, i, xs, ys, xms, del_x)
        resids = min_function(pars, xs, ys, xms, del_x)
        ams, scales, vs = unpack_pars(pars, n_ms, n_epoch)
        print "Optimization of velocity at epoch {0}:".format(i)
        print "Objective function value: {0}".format(np.dot(resids,resids))
        print "Velocities:", vs
        
    # do it a few more times:
    pars2 = np.copy(pars)
    for j in [2,3,4]:
        soln = leastsq(min_function, pars2, args=fa, ftol=ftol)
        pars2 = soln[0]
        ams2, scales2, vs2 = unpack_pars(pars2, n_ms, n_epoch)
        resids2 = min_function(pars2, xs, ys, xms, del_x)
        print "All-parameter optimization #{0}:".format(j)
        print "Objective function value: {0}".format(np.dot(resids2,resids2))
        print "Velocities:", vs2
    
        # & loop through the epochs again:
        for i in [0,1,2]:
            pars2 = min_v(pars2, i, xs, ys, xms, del_x)
            resids = min_function(pars2, xs, ys, xms, del_x)
            ams, scales, vs = unpack_pars(pars2, n_ms, n_epoch)
            print "Optimization of velocity at epoch {0}:".format(i)
            print "Objective function value: {0}".format(np.dot(resids,resids))
            print "Velocities:", vs
    
    
    '''''
    # re-optimize with vs only:
    soln_v = leastsq(min_function_v, vs, args=(ams, scales, xs, ys, xms, del_x), ftol=ftol)
    print soln_v[0]
    
    
    for e in range(n_epoch):
        calc = model(xs[e], xms, del_x, ams * scales[e])
        x_plot = np.linspace(lnwave[0],lnwave[-1],num=5000)
        calc_plot = model(x_plot, xms, del_x, ams * scales[e])
        save_plot(xs[e], ys[e], calc, x_plot, calc_plot, 'epoch'+str(e)+'.pdf')

    
    # re-optimize:
    pars[n_ms+n_epoch] = 20.0
    pars[n_ms+n_epoch+1] = -10.0
    soln2 = leastsq(min_function, pars, args=fa, ftol=ftol)
    pars2 = soln2[0]
    ams, scales, vs = unpack_pars(pars2, n_ms, n_epoch)
    print vs
    '''
