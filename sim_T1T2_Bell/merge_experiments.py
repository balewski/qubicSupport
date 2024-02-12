#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

'''
merge yields from many jobs as one hd5

'''

import os
import fnmatch
from toolbox.Util_H5io4 import  write4_data_hdf5, read4_data_hdf5
import copy
from pprint import pprint
import numpy as np


import argparse
def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--verbosity",type=int,choices=[0, 1, 2],  help="increase output verbosity", default=1, dest='verb')

    parser.add_argument("--basePath",default='/dataVault/dataQubiC_APS2024',help="head dir for set of experiments")
    parser.add_argument("-t","--tag",default='readA_czA',help="job group tag")
                        
    parser.add_argument('-e',"--expName",  default=['exp_62a2'],  nargs='+',help='list of retrieved experiments, blank separated')

    args = parser.parse_args()
    # make arguments  more flexible
    
    args.dataPath=os.path.join(args.basePath,args.tag,'meas')
    args.outPath=os.path.join(args.basePath,args.tag,'post')
 
    print( 'myArg-program:',parser.prog)
    for arg in vars(args):  print( 'myArg:',arg, getattr(args, arg))
    assert os.path.exists(args.dataPath)
    assert os.path.exists(args.outPath)
    return args

#...!...!.................... 
def add_experiment(ie,inpL,outD,outMD):
     inpF=inpL[ie]
     print('A: %d %s'%(ie,inpF))
     expD,expMD=read4_data_hdf5(os.path.join(args.dataPath,inpF),verb=0)
     #nimg=expMD['payload']['num_images']
     
     # ... copy data
     for x in expD:
         outD[x][ie]=expD[x]

     #.... add merging input info
     ncf=expMD['noise_conf']
     T1=ncf['T1_us']
     T2=ncf['T2_us']
     outD['set_T1T2_us'][ie]=[T1,T2]

         
         
#...!...!.................... 
def setup_containers(expD,expMD,numJobs):
    #pprint(expMD)
    # for now all experiments must have the same dims
    nCirc=expMD['payload']['num_circ']
    #1 ... big data...
    bigD={}
    for x in expD:
        y=expD[x]
        shy=(numJobs,)+y.shape
        print('expand x%d'%numJobs,x,shy)
        bigD[x]=np.zeros(tuple(shy),dtype=y.dtype)
        

    bigD['set_T1T2_us']=np.zeros((numJobs,2))
    print('created bigD:',list(bigD))
    
    #2 ... meta data...                
    MD=copy.deepcopy(expMD)
    for xx in ['T1_us','T2_us']: MD['noise_conf'].pop(xx)
    MD['submit'].pop('job_id')
    
    # ... new merged job hash & name
    MD['hash']='%sx%d'%(expMD['hash'],numJobs)
    MD['short_name']=args.tag
    MD['num_merged_jobs']=numJobs
    
    return bigD, MD

#...!...!....................
def find_matching_files(directory, pattern):
    matching_files = []
    print('search dir:',directory,'pattern:')#,=)
    for item in os.listdir(directory):
        full_path = os.path.join(directory, item)
        if os.path.isfile(full_path) and fnmatch.fnmatch(item, pattern):
            matching_files.append(item)
    return matching_files

#=================================
#=================================
#  M A I N 
#=================================
#=================================
if __name__=="__main__":
    args=get_parser()
    
    jobL=find_matching_files(args.dataPath,'bell*.h5')
    nJob=len(jobL)
    print('M:found %d jobs:'%nJob,jobL[:3])
    assert nJob>0
    inpF=jobL[0]
    expD,expMD=read4_data_hdf5(os.path.join(args.dataPath,inpF))
    if args.verb>1: pprint(expMD)
    outD,outMD=setup_containers(expD,expMD,nJob)
    print('M:merges MD');pprint(outMD)

    
    # append other experiments
    for ie in range(0,nJob):
        add_experiment(ie,jobL,outD,outMD)
        
    print('M: found all %d inputs'%nJob)
    
    #...... WRITE  OUTPUT .........
    outF=os.path.join(args.outPath,outMD['short_name']+'.h5')
    write4_data_hdf5(outD,outF,outMD)
    
    print('  ./pl_T1T2_surf.py --tag   %s    \n'%(args.tag ))

