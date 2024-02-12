#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

'''
Use Qiskit simulator with NoiseModel() and 
user definded bit-flip and thermal noise for gates, T1,T2 for qubits
use all-to-all connectivity.
Simulations run locally.
Records meta-data 
HD5 arrays contain  all outputs
(optional) plot ev(ZZ) vs. cycles
Dependence: qiskit

'''

import time
import sys,os
import numpy as np
from pprint import pprint
import hashlib

from qiskit.tools.monitor import job_monitor
from qiskit import Aer, QuantumCircuit
from toolbox.Util_H5io4 import  write4_data_hdf5, read4_data_hdf5
from toolbox.Util_QiskitNoisySimu import config_noise_model
from toolbox.Util_miscIO import read_yaml


import argparse
#...!...!..................
def get_parser(backName="ibmq_qasm_simulator"):
    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--verb",type=int, help="increase debug verbosity", default=1)
    parser.add_argument("--basePath",default='env',help="head dir for set of experiments, or env--> $QCrank_dataVault")
    parser.add_argument("--expName",  default=None,help='(optional)replaces IBMQ jobID assigned during submission by users choice')
    parser.add_argument( "-p","--plot",action='store_true', default=False,help="plot result")  
    # .... RC-setup
    parser.add_argument('-c',"--cycles",  default=[1,5,9,15,21,31],type=int,nargs='+', help=" RC cycles, list space separated")
    # .... job running
    parser.add_argument('-n','--numShots',type=int,default=10000, help="shots per circuit")

    # ..... noise modeling
    parser.add_argument("-N", "--noiseConf",  default='qubicAps24',choices=['minor','qubicAps24'],help="select pre-canned magnitude of noise")
    parser.add_argument('--noise_T1T2',type=float,nargs='+',default=[], help="change T1/us and T2/us")
    parser.add_argument('--noise_czFidel',type=float,default=None, help="change CZ fidelity, range (0,1)")
    parser.add_argument('--noise_readFidel',type=float,default=[],nargs='+', help="readout fidelity:  set0meas0 set1meas1 ,space separated, range (0,1) each")

    
    args = parser.parse_args()
    if 'env'==args.basePath: args.basePath= os.environ['QubiC_dataVault']
    args.outPath=os.path.join(args.basePath,'meas')
    args.confPath='noise_conf'
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
    nshot=md['submit']['num_shots']
    true_prob=md['payload']['true_probs']
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
    #print('HBR:raw_mshot\n',raw_mshot)

    # expectation value for <ZZ>
    
    ev_zz= (raw_mshot[:,0] + raw_mshot[:,3] - raw_mshot[:,1] - raw_mshot[:,2])/nshot
    ev_zzErr= np.sqrt( ev_zz*(1-ev_zz)/nshot)
    #print('HBR: 1-ev_zz  1/sqrt(nshot)=%.3f\n'%(1/np.sqrt(nshot)),1-ev_zz)
    #print('ev_zz err:',ev_zzErr)

    #.... compute total variation distance (TVD)
    meas_prob=raw_mshot/nshot
    # Compute the absolute difference and sum it across the probability dimension
    abs_diff_sum = np.sum(np.abs(true_prob - meas_prob), axis=1)
    meas_tvd=0.5*abs_diff_sum
   
    print('cycles:',md['payload']['cycles'])
    print('meas TVD:',meas_tvd)
        
    bigD={'raw_mshot':raw_mshot, 'ev_zz':ev_zz, 'ev_zzErr':ev_zzErr,'meas_tvd':meas_tvd}
    return bigD

#...!...!....................
def make_circuit(nCyc):
    nq=2
    qc = QuantumCircuit(nq,name='bell_%dcyc'%nCyc)
    qc.h(0); qc.h(1)
    for ib in range(nCyc):
        qc.cz(0,1)
    qc.h(0)
    qc.measure_all()
    return qc

#...!...!....................
def patch_noise_conf(cf,args):
    TT=args.noise_T1T2
    assert len(TT) in [0,2]
    if len(TT)==2:
        assert TT[1]<=2*TT[0]
        assert TT[1]>0
        cf['T1_us']=TT[0]; cf['T2_us']=TT[1];
  
    if args.noise_czFidel!=None: cf['gate_2q']['cz']['fidelity']=args.noise_czFidel

    RR=args.noise_readFidel
    assert len(RR) in [0,2]
    if len(RR)==2:
        assert min(RR) >0
        assert max(RR) <1
        cf['read_err']['set0meas0']=RR[0]
        cf['read_err']['set1meas1']=RR[1]

#...!...!....................
def M_plot_ev_ZZ(md,bigD):
    X=md['payload']['cycles']
    Y=bigD['ev_zz']
    eY=bigD['ev_zzErr']
    fig, ax = plt.subplots()
    ax.errorbar(X, Y, yerr=eY, fmt='o', capsize=5, capthick=2, ecolor='red', markeredgecolor='black', markeredgewidth=1)
    ax.set_xlabel('RB cycles')
    ax.set_ylabel('EV <ZZ>')
    ax.set_title('RB for Bell-state,   noisy simu:%s'%md['short_name'])
    ax.set_ylim(-0.02,1.02)
    ax.grid()
    outF1=outF.replace('.h5','.ev_zz.png')
    plt.savefig(outF1); print('M:saved plot',outF1)

    
#...!...!....................
def M_plot_TVD(md,bigD):
    #.... plot total variation distance (TVD)
    X=md['payload']['cycles']
    Y=bigD['meas_tvd']
    circN=md['payload']['circ_name']
    fig, ax = plt.subplots()
    ax.plot(X, Y, '*')
    ax.set_xlabel('num cycles')
    ax.set_ylabel('TVD')
    ax.set_title('%s,   noisy simu:%s'%(circN,md['short_name']))
    ax.set_ylim(-0.02,0.52)

    ax.grid()
    outF1=outF.replace('.h5','.tvd.png')
    plt.savefig(outF1); print('M:saved plot',outF1)

        
#=================================
#        M A I N 
#=================================
if __name__ == "__main__":
    args=get_parser(backName='aer')
    expMD=buildPayloadMeta(args)            
    pprint(expMD)
    
    inpF=args.noiseConf+'.yaml'
    inpFF=os.path.join(args.confPath,inpF)
    noiseCf=read_yaml(inpFF)
    patch_noise_conf(noiseCf,args)
    
    expMD['noise_conf']=noiseCf
    noise_model =config_noise_model(noiseCf,nq=2)
    
    qcL=[]
    for ic,nCyc in enumerate(args.cycles):
        qc=make_circuit(nCyc)
        qcL.append(qc)
        if ic%2==0 or ic<3: print('circ=',qc.name); print(qc)
    
    expMD['payload'].update({'num_qubit':qc.num_qubits , 'num_clbit':qc.num_clbits})
    expMD['payload']['true_probs']=[0.5,0.,0.,0.5]
    expMD['payload']['circ_name']='Bell-state'
    
    backend=Aer.get_backend("qasm_simulator")       
    print('M: execution-ready %d circuits  on %s'%(len(qcL),backend.name))
        
    # ----- submission ----------
    T0=time.time()
    job =  backend.run(qcL,shots=args.numShots, noise_model=noise_model)
    jid=job.job_id()

    print('submitted JID=',jid,backend ,'\n do %.2fM shots , wait for execution ...'%(args.numShots/1e6))
    job_monitor(job)
    T1=time.time()
    print(' job done, elaT=%.1f min'%((T1-T0)/60.))

    harvest_ibmq_backRun_submitMeta(job,expMD,args)
         
    #
    expD=harvest_backRun_result(job,expMD)

    print('\nM: noise conf:'); pprint(expMD['noise_conf'])
    outF=os.path.join(args.outPath,expMD['short_name']+'.h5')
    write4_data_hdf5(expD,outF,expMD)

    print('M:done')

    # .... plotting ....
    if args.plot==False:
        print('M: plots NOT produced, add -p')
        exit(0)
    import matplotlib.pyplot as plt
    #M_plot_ev_ZZ(expMD,expD)
    M_plot_TVD(expMD,expD)
    plt.show()

