#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

import matplotlib.pyplot as plt
import numpy as np
import os
from pprint import pprint

from toolbox.Util_H5io4 import  write4_data_hdf5, read4_data_hdf5
#from toolbox.PlotterBackbone import roys_fontset


import argparse
def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--verbosity",type=int,choices=[0, 1, 2],  help="increase output verbosity", default=1, dest='verb')

    parser.add_argument("--basePath",default='/dataVault/dataQubiC_APS2024',help="head dir for set of experiments")
    parser.add_argument("-t","--tag",default='readA_czA',help="job group tag")
                        

    args = parser.parse_args()
    # make arguments  more flexible
    
    args.dataPath=os.path.join(args.basePath,args.tag,'post')
    args.outPath='out/'
    print( 'myArg-program:',parser.prog)
    for arg in vars(args):  print( 'myArg:',arg, getattr(args, arg))
    assert os.path.exists(args.dataPath)
    assert os.path.exists(args.outPath)
    return args

#...!...!....................
def plot2_sparse_3d_mesh(ax,md,set_T1T2, meas_tvd, z_plane=0.2, elev=30, azim=30):
    
    # Plotting the mesh
    ax.scatter(set_T1T2[:, 0], set_T1T2[:, 1], meas_tvd, color='g')
    ax.plot_trisurf(set_T1T2[:, 0], set_T1T2[:, 1], meas_tvd, color='g', alpha=0.5)

    if z_plane!=None:    # Plot a plane at Z=z_plane
        xlim = ax.get_xlim()
        ylim = ax.get_ylim(); ylim=[10,60]
        X, Y = np.meshgrid(np.linspace(xlim[0], xlim[1], 2), np.linspace(ylim[0], ylim[1], 2))
        Z = np.full(X.shape, z_plane)
        ax.plot_surface(X, Y, Z, color='b', alpha=0.4 , label='Intersection Plane')

        # Find and plot approximate intersection points
        close_to_plane = np.abs(meas_tvd - z_plane) < 0.015  # Threshold for "close" to the plane
        intPt = set_T1T2[close_to_plane]   # intersecting_points
        ax.plot(intPt[:,0],intPt[:,1],z_plane,color='r')
        
    # Set view angle
    ax.view_init(elev=elev, azim=azim)
    ax.set_zlim(0,0.5)
    
    ax.set_xlabel('T1 (us)')
    ax.set_ylabel('T2 (us)')
    ax.set_zlabel('TVD')
    ax.set_title(md['plot']['title'])

    #ax.text(-0.0, 1.05, 'b)', transform=ax.transAxes)
    # Add text 'abc' at specified location

    if 'comm' in md['plot']:
        ax.text(160, 10, 0.75, md['plot']['comm'], color='black', fontsize=10, ha='left')
        md['plot'].pop('comm') # one time use
        

#=================================
#  M A I N
#=================================
if __name__ == "__main__":
    args=get_parser()
    
    #roys_fontset(plt)
   

    inpF='%s.h5'%args.tag  
    expD,expMD=read4_data_hdf5(os.path.join(args.dataPath,inpF))
    circId=1
    nCyc=expMD['payload']['cycles'][circId]
    expMD['plot']={'num_cyc':nCyc}

    pprint(expMD)
    z_plane=None
    if args.tag=='readA_czA' : z_plane=0.20
    if args.tag=='readB_czB' : z_plane=0.37
    if args.tag=='readA_czB' : z_plane=0.34
    if args.tag=='readB_czA' : z_plane=0.28
    
    meas_tvd =expD['meas_tvd'][:,circId]
    set_T1T2 =expD['set_T1T2_us']

    fig, axs = plt.subplots(1, 2, figsize=(14, 6), subplot_kw={'projection': '3d'})
    
    expMD['plot']['title']='%s  numCycle:%d'%(expMD['short_name'],nCyc)
    ncf=expMD['noise_conf']
    expMD['plot']['comm']='s0m0: %.2f, s1m1: %.2f, czFid=%.2f'%(ncf['read_err']['set0meas0'],  ncf['read_err']['set0meas0'],  ncf['gate_2q']['cz']['fidelity'])  
    plot2_sparse_3d_mesh(axs[0],expMD,set_T1T2, meas_tvd, z_plane, elev=30, azim=50)
    plot2_sparse_3d_mesh(axs[1],expMD,set_T1T2, meas_tvd, z_plane, elev=1, azim=1)
    

    
    # Adjust figure spacing to add a 20% gap between the subplots
    #fig.subplots_adjust(wspace=0.15,bottom=0.2)
    
    plt.tight_layout()
    outF='bell_%s.png'%expMD['short_name']
    outF=os.path.join(args.outPath,outF)
    fig.savefig(outF)
    print('M: saved',outF)
