#!/usr/bin/env python3
__author__ = "Jan Balewski + ChatGPT"
__email__ = "janstar1122@gmail.com"

from qiskit import Aer, QuantumCircuit, transpile
import numpy as np
from pprint import pprint

#=================================
#  M A I N 
#=================================
#=================================
if __name__=="__main__":

    if 1:  # H-gate 
        nq=1
        # Define your two quantum circuits
        qc1 = QuantumCircuit(nq)
        qc1.h(0)
        print(qc1)

        qc2 = QuantumCircuit(nq)
        qc2.p(np.pi/2,0)
        qc2.rx(np.pi/2,0)
        qc2.p(np.pi/2,0)
        print(qc2)

    if 0:  # CZ vs. CNOT gates 
        nq=2
        # Define your two quantum circuits
        qc1 = QuantumCircuit(nq)
        qc1.cx(0,1)
        print(qc1)

        qc2 = QuantumCircuit(nq)
        qc2.x(0)
        qc2.cz(0,1)
        print(qc2)

    backend=Aer.get_backend("qasm_simulator")
    
    # Transpile the circuits
    simulator = Aer.get_backend('unitary_simulator')

    qc1_us = transpile(qc1, simulator)
    qc2_us= transpile(qc2, simulator)
   

    # Simulate the circuits to get their unitary representations
    result1 = simulator.run(qc1_us).result()
    U1 = result1.get_unitary()

    result2 = simulator.run(qc2_us).result()
    U2 = result2.get_unitary()


    # Compare the unitary matrices
    equal12 = np.allclose(U1,U2, atol=1e-10)
    

    print('M: equality:',equal12)
    # Format and print the unitary matrices
    def niceU(U):
        return np.array2string(np.where(np.round(U, 3) == 0.+0.j, None, np.round(U, 3)), separator=', ')

    # Format and print the unitary matrices
    fU1 = niceU(U1)
    fU2 = niceU(U2)
   
    print("Unitary for circuit 1:\n",fU1)

    if equal12:
        print("\nPASS_12:  the same unitary ")
    else:
        print("\nFAIL: different unitary 2")
        print("Unitary for circuit 2:\n",fU2)
        fD=niceU(U2-U1)
        print("diff U2-U1:\n",fD)

   
