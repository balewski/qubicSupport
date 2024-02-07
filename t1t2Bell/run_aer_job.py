#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

'''
Use Qiskit simulator with NoiseModel() and 
user definded bit-flip and thermal noise
use all-to-all connectivity.
Run simulations w/o submit/retrieve of the job
Simulations run locally.
Records meta-data containing  job_id
HD5 arrays contain input images
Dependence: qiskit

'''

import time
import sys,os
import numpy as np
from pprint import pprint

from qiskit.tools.monitor import job_monitor
from qiskit import Aer, QuantumCircuit
#from qiskit.tools.visualization import circuit_drawer
#from submit_ibmq_backRun import get_parser, canned_qcrank_inp, harvest_ibmq_backRun_submitMeta
from toolbox.Util_H5io4 import  write4_data_hdf5, read4_data_hdf5
#from retrieve_ibmq_backRun import harvest_backRun_result

import argparse
#...!...!..................
def get_parser(backName="ibmq_qasm_simulator"):
    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--verb",type=int, help="increase debug verbosity", default=1)
    parser.add_argument("--basePath",default='env',help="head dir for set of experiments, or env--> $QCrank_dataVault")
    parser.add_argument("--expName",  default=None,help='(optional)replaces IBMQ jobID assigned during submission by users choice')
    # .... RC-setup
    parser.add_argument("--cycles",  default=[1,3,5],type=int,nargs='+', help=" RC cycles, list space separated")

    # .... job running
    parser.add_argument('-n','--numShots',type=int,default=4000, help="shots per circuit")
    parser.add_argument( "-E","--executeCircuit", action='store_true', default=False, help="may take long time, test before use ")

    args = parser.parse_args()
    if 'env'==args.basePath: args.basePath= os.environ['QubiC_dataVault']
    args.outPath=os.path.join(args.basePath,'meas')
    args.provider='local_sim'
    assert len(args.cycles)>1

    for arg in vars(args):
        print( 'myArgs:',arg, getattr(args, arg))

    assert os.path.exists(args.outPath)

    return args


#...!...!....................
def buildPayloadMeta(args):
    pd={}  # payload
    pd['num_circ']=len(args.cycles)
    pd['cycles']=args.cycles
    md={ 'payload':pd}
    md['short_name']=args.expName

    if args.verb>1:  print('\nBMD:');pprint(md)
    return md


#...!...!....................
def harvest_ibmq_backRun_submitMeta(job,md,args):
    sd={}
    sd['job_id']=job.job_id()
    sd['backend']=job.backend().name
    sd['num_shots']=args.numShots
    sd['provider']=args.provider
    md['submit']=sd

    if args.expName==None:
        # the  6 chars in job id , as handy job identiffier
        md['hash']=sd['job_id'].replace('-','')[3:9] # those are still visible on the IBMQ-web
        name='exp_'+md['hash']
        #if md['backend']['ideal_simu']: name='isim_'+md['hash']
        md['short_name']=name
    else:
        myHN=hashlib.md5(os.urandom(32)).hexdigest()[:6]
        md['hash']=myHN
        md['short_name']=args.expName


#...!...!....................
def harvest_backRun_result(job,md):
    jobRes = job.result()
    resL=jobRes.results
    nCirc=len(resL)  # number of circuit in the job
    jstat=str(job.status())
    # collect job performance info
    qa={}

    qa['status']=jstat
    qa['num_circ']=nCirc
    nclbit=md['payload']['num_clbit']
    MB=1<<nclbit
    
    countsL=jobRes.get_counts()
    raw_mshot = np.zeros((nCirc, MB), dtype=np.int32)    # Padded with 0
    if nCirc==1:
        countsL=[countsL]  # this is poor design
        
    for ic in range(nCirc):
        counts=countsL[ic]
        #print(ic,counts)
        for key in counts:
            ikey=int(key, 2)
            raw_mshot[ic,ikey]=counts[key]
    print('raw_mshot',raw_mshot)
    bigD={'raw_mshot':raw_mshot}
    return bigD

#...!...!....................
def make_circuit(nCyc):
    nq=2
    qc = QuantumCircuit(nq)
    qc.h(0); qc.h(1)
    for ib in range(nCyc):
        qc.cz(0,1)
        qc.h(0)
    
    qc.measure_all()
    return qc

#=================================
#=================================
if __name__ == "__main__":
    args=get_parser(backName='aer')
    expMD=buildPayloadMeta(args)
            
    pprint(expMD)
    qcL=[]
    for ic,nCyc in enumerate(args.cycles):
        qc=make_circuit(nCyc)
        print(qc)
        qcL.append(qc)
    
    expMD['payload'].update({'num_qubit':qc.num_qubits , 'num_clbit':qc.num_clbits})
    
    backend=Aer.get_backend("qasm_simulator")
    
    print('M: execution-ready %d circuits  on %s'%(len(qcL),backend.name))                        
    
    if not args.executeCircuit:
        print('NO execution of circuit, use -E to execute the job')
        exit(0)

    # ----- submission ----------
    T0=time.time()
    job =  backend.run(qcL,shots=args.numShots)
    jid=job.job_id()

    print('submitted JID=',jid,backend ,'\n do %.2fM shots , wait for execution ...'%(args.numShots/1e6))
    job_monitor(job)
    T1=time.time()
    print(' job done, elaT=%.1f min'%((T1-T0)/60.))

    harvest_ibmq_backRun_submitMeta(job,expMD,args)
    expMD['submit']['runtime']='sampler'  # tmp, test both runtimes?
         
    print('M: got results')
    expD=harvest_backRun_result(job,expMD)

    pprint(expMD)
    outF=os.path.join(args.outPath,expMD['short_name']+'.h5')
    write4_data_hdf5(expD,outF,expMD)

    print('   ./postproc_exp.py --expName   %s  -X  --showPlots a    \n'%(expMD['short_name']))
  
     
