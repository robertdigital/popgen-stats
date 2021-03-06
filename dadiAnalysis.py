#!/usr/bin/env python

import sys
import argparse
from Bio.Phylo.PAML.chi2 import cdf_chi2
import numpy
from numpy import array
import dadi
from math import *
import cmath

def get_args():
    # parse command line arguments
    parser = argparse.ArgumentParser(description='Run dadi analysis')
    parser.add_argument("sfs", help="SFS in dadi format",
                    type=argparse.FileType('r'))
    parser.add_argument("-f", "--fold", help="Fold the SFS before analysis",
                        action="store_true")
    return parser.parse_args()

def likelihood_grid(function, data, ns, pts_l, func_name):
    outfile = open("likelihood_grid_{0}.txt".format(func_name), "w")
    outfile.write("nu\tT\tLL\n")
    for T in numpy.arange(0.001, 1, 0.01):
        for nu in numpy.arange(0.001, 50, 1):
            params = array([nu, T])
            model = function(params, ns, pts_l)
            ll = dadi.Inference.ll_multinom(model, data)
            outfile.write("%f\t%f\t%f\n" % (nu, T, ll))
    outfile.close()

def likelihood_grid_bottleneck(function, data, ns, pts_l, func_name):
    outfile = open("likelihood_grid_{0}.txt".format(func_name), "w")
    outfile.write("nuB\tnuF\tTB\tTF\tLL\n")
    for TF in numpy.arange(0.001, 1, 0.01):
        for TB in numpy.arange(0.001, 1, 0.01):
            for nuF in numpy.arange(0.001, 50, 1):
                for nuB in numpy.arange(0.001, 50, 1):
                    params = array([nuB,nuF,TB,TF])
                    model = function(params, ns, pts_l)
                    ll = dadi.Inference.ll_multinom(model, data)
                    outfile.write("%f\t%f\t%f\t%f\t%f\n" % (nuB, nuF, TB, TF, ll))
    outfile.close()

def likelihood_grid_bottlegrowth(function, data, ns, pts_l, func_name):
    outfile = open("likelihood_grid_{0}.txt".format(func_name), "w")
    outfile.write("nuB\tnuF\tTF\tLL\n")
    for TF in numpy.arange(0.001, 1, 0.01):
            for nuF in numpy.arange(0.001, 50, 1):
                for nuB in numpy.arange(0.001, 50, 1):
                    params = array([nuB,nuF,TF])
                    model = function(params, ns, pts_l)
                    ll = dadi.Inference.ll_multinom(model, data)
                    outfile.write("%f\t%f\t%f\t%f\n" % (nuB, nuF, TF, ll))
    outfile.close()

args = get_args()

data = dadi.Spectrum.from_file(args.sfs)
ns = data.sample_sizes
if args.fold:
    data = data.fold()
print "Number of samples: %s" % ns

thetaW = data.Watterson_theta()
print "Watterson's theta: %f" % thetaW

pi = data.pi()
print "Pi: %f" % pi

D = data.Tajima_D()
print "Tajima's D: %f" % D

pts_l = [110,120,130] # grid point settings

AIC_stats = []

# Neutral model

neutral_func = dadi.Demographics1D.snm
neutral_params = array([])
neutral_upper_bound = []
neutral_func_ex = dadi.Numerics.make_extrap_log_func(neutral_func)
neutral_model = neutral_func_ex(neutral_params, ns, pts_l)
neutral_ll = dadi.Inference.ll_multinom(neutral_model, data)

print "Neutral model log-likelihood: %f" % neutral_ll

# Instantaneous expansion model

expansion_func = dadi.Demographics1D.two_epoch
# params are nu: ratio of population size & T: time that change happened
expansion_params = array([2,0.05])
expansion_upper_bound = [100, 10]
expansion_lower_bound = [1e-2, 0]
expansion_func_ex = dadi.Numerics.make_extrap_log_func(expansion_func)
expansion_model = expansion_func_ex(expansion_params, ns, pts_l)
expansion_ll = dadi.Inference.ll_multinom(expansion_model, data)

print "Expansion model log-likelihood: %f" % expansion_ll


expansion_p0 = dadi.Misc.perturb_params(expansion_params, fold=1,
                                        upper_bound = expansion_upper_bound)

expansion_popt = dadi.Inference.optimize_log(expansion_p0, data,
                                            expansion_func_ex, pts_l,
                                            lower_bound = expansion_lower_bound,
                                            upper_bound = expansion_upper_bound,
                                            maxiter=100)
print "Optimized parameters", repr(expansion_popt)
expansion_model = expansion_func_ex(expansion_popt, ns, pts_l)
expansion_ll_opt = dadi.Inference.ll_multinom(expansion_model, data)
print "Optimized log-likelihood:", expansion_ll_opt

k = len(expansion_params)
expansion_AIC = 2 * k - 2 * expansion_ll_opt
print "AIC:", expansion_AIC
AIC_stats.append(expansion_AIC)

# Exponential growth model

growth_func = dadi.Demographics1D.growth
# params are nu: ratio of population size & T: time that change happened
growth_params = array([2,0.05])
growth_upper_bound = [100, 10]
growth_lower_bound = [1e-2, 0]
growth_func_ex = dadi.Numerics.make_extrap_log_func(growth_func)
growth_model = growth_func_ex(growth_params, ns, pts_l)
growth_ll = dadi.Inference.ll_multinom(growth_model, data)

print "Exponential growth model log-likelihood: %f" % growth_ll

growth_p0 = dadi.Misc.perturb_params(growth_params, fold=1,
                                        upper_bound = growth_upper_bound)

growth_popt = dadi.Inference.optimize_log(growth_p0, data,
                                            growth_func_ex, pts_l,
                                            lower_bound = growth_lower_bound,
                                            upper_bound = growth_upper_bound,
                                            maxiter=100)

print "Optimized parameters", repr(growth_popt)
growth_model = growth_func_ex(growth_popt, ns, pts_l)
growth_ll_opt = dadi.Inference.ll_multinom(growth_model, data)
print "Optimized log-likelihood:", growth_ll_opt
k = len(growth_params)
growth_AIC = (2 * k) - (2 * growth_ll_opt)
print "AIC:", growth_AIC
AIC_stats.append(growth_AIC)

# Bottleneck model

bottleneck_func = dadi.Demographics1D.three_epoch
# Params are nuB,nuF,TB,TF; nuB: Ratio of bottleneck population size to ancient pop size, nuF: Ratio of contemporary to ancient pop size,
# TB: Length of bottleneck and TF: Time since bottleneck recovery
bottleneck_params = array([2,2,0.05,0.05])
bottleneck_upper_bound = [100, 100, 10, 10]
bottleneck_lower_bound = [1e-2, 1e-2, 0, 0]
bottleneck_func_ex = dadi.Numerics.make_extrap_log_func(bottleneck_func)
bottleneck_model = bottleneck_func_ex(bottleneck_params, ns, pts_l)
bottleneck_ll = dadi.Inference.ll_multinom(bottleneck_model, data)

print "Bottleneck model log-likelihood: %f" % bottleneck_ll

bottleneck_p0 = dadi.Misc.perturb_params(bottleneck_params, fold=1,
                                        upper_bound = bottleneck_upper_bound)

bottleneck_popt = dadi.Inference.optimize_log(bottleneck_p0, data,
                                            bottleneck_func_ex, pts_l,
                                            lower_bound = bottleneck_lower_bound,
                                            upper_bound = bottleneck_upper_bound,
                                            maxiter=100)
print "Optimized parameters", repr(bottleneck_popt)
bottleneck_model = bottleneck_func_ex(bottleneck_popt, ns, pts_l)
bottleneck_ll_opt = dadi.Inference.ll_multinom(bottleneck_model, data)
print "Optimized log-likelihood:", bottleneck_ll_opt

k = len(bottleneck_params)
bottleneck_AIC = 2 * k - 2 * bottleneck_ll_opt
print "AIC:", bottleneck_AIC
AIC_stats.append(bottleneck_AIC)

# Bottlegrowth model

bottlegrowth_func = dadi.Demographics1D.bottlegrowth
# Params are nuB,nuF,T; nuB
bottlegrowth_params = array([2,2,0.05])
bottlegrowth_upper_bound = [100, 100, 10]
bottlegrowth_lower_bound = [1e-2, 1e-2, 0]
bottlegrowth_func_ex = dadi.Numerics.make_extrap_log_func(bottlegrowth_func)
bottlegrowth_model = bottlegrowth_func_ex(bottlegrowth_params, ns, pts_l)
bottlegrowth_ll = dadi.Inference.ll_multinom(bottlegrowth_model, data)

print "Bottlegrowth model log-likelihood: %f" % bottlegrowth_ll

bottlegrowth_p0 = dadi.Misc.perturb_params(bottlegrowth_params, fold=1,
                                        upper_bound = bottlegrowth_upper_bound)

bottlegrowth_popt = dadi.Inference.optimize_log(bottlegrowth_p0, data,
                                            bottlegrowth_func_ex, pts_l,
                                            lower_bound = bottlegrowth_lower_bound,
                                            upper_bound = bottlegrowth_upper_bound,
                                            maxiter=100)
print "Optimized parameters", repr(bottlegrowth_popt)
bottlegrowth_model = bottlegrowth_func_ex(bottlegrowth_popt, ns, pts_l)
bottlegrowth_ll_opt = dadi.Inference.ll_multinom(bottlegrowth_model, data)
print "Optimized log-likelihood:", bottlegrowth_ll_opt

k = len(bottlegrowth_params)
bottlegrowth_AIC = 2 * k - 2 * bottlegrowth_ll_opt
print "AIC:", bottlegrowth_AIC
AIC_stats.append(bottlegrowth_AIC)

# Output SFS for data
data_sfs_file = open("observedSFS.txt", "w")
for i in range(1,len(data)-1):
    data_sfs_file.write(str(data[i]) + '\n')
data_sfs_file.close()

# Output SFS for neutral model
neutral_sfs = dadi.Inference.optimally_scaled_sfs(neutral_model, data)
neutral_sfs_file = open("neutralModelSFS.txt", 'w')
for i in range(1,len(neutral_sfs)-1):
    neutral_sfs_file.write(str(neutral_sfs[i]) + '\n')
neutral_sfs_file.close()

# Output SFS for expansion model
expansion_sfs = dadi.Inference.optimally_scaled_sfs(expansion_model, data)
expansion_sfs_file = open("expansionModelSFS.txt", 'w')
for i in range(1,len(expansion_sfs)-1):
    expansion_sfs_file.write(str(expansion_sfs[i]) + '\n')
expansion_sfs_file.close()

# Output SFS for growth model
growth_sfs = dadi.Inference.optimally_scaled_sfs(growth_model, data)
growth_sfs_file = open("growthModelSFS.txt", 'w')
for i in range(1,len(growth_sfs)-1):
    growth_sfs_file.write(str(growth_sfs[i]) + '\n')
growth_sfs_file.close()

# Output SFS for bottleneck model
bottleneck_sfs = dadi.Inference.optimally_scaled_sfs(bottleneck_model, data)
bottleneck_sfs_file = open("bottleneckModelSFS.txt", 'w')
for i in range(1,len(bottleneck_sfs)-1):
    bottleneck_sfs_file.write(str(bottleneck_sfs[i]) + '\n')
bottleneck_sfs_file.close()

# Output SFS for bottlegrowth model
bottlegrowth_sfs = dadi.Inference.optimally_scaled_sfs(bottlegrowth_model, data)
bottlegrowth_sfs_file = open("bottlegrowthModelSFS.txt", 'w')
for i in range(1,len(bottlegrowth_sfs)-1):
    bottlegrowth_sfs_file.write(str(bottlegrowth_sfs[i]) + '\n')
bottlegrowth_sfs_file.close()


min_AIC = min(AIC_stats)

if min_AIC == expansion_AIC:
    print "Best fitting model: Expansion. Working on likelihood surface..."
    likelihood_grid(expansion_func_ex, data, ns, pts_l, "expansion")
if min_AIC == growth_AIC:
    print "Best fitting model: Growth. Working on likelihood surface..."
    likelihood_grid(growth_func_ex, data, ns, pts_l, "growth")
if min_AIC == bottleneck_AIC:
    print "Best fitting model: Bottleneck. Working on likelihood surface..."
    likelihood_grid_bottleneck(bottleneck_func_ex, data, ns, pts_l, "bottlneck")
if min_AIC == bottlegrowth_AIC:
    print "Best fitting model: Bottlegrowth. Working on likelihood surface..."
    likelihood_grid_bottlegrowth(bottlegrowth_func_ex, data, ns, pts_l, "bottlegrowth")
