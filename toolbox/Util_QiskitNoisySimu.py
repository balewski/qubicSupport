# those function are needed for simulator with NoiseModel() and user definded bit-flip and thermal noise

from pprint import pprint
from qiskit.providers.aer.noise import errors, NoiseModel
 
#...!...!....................
def config_noise_model(cf,nq):
    print('CNM: conf'); pprint(cf)

    #... make only pointers, so you can save it  after modiffications   
    T1, T2 = cf['T1_us'] * 1e-6, cf['T2_us'] * 1e-6,
    # qiskit_aer.noise.noiseerror.NoiseError: 'Invalid T_2 relaxation time parameter: T_2 greater than 2 * T_1.'
    assert T2<=2*T1
    
    #... configure noise model ...
    noise_model = NoiseModel()
    
    for qubit in range(nq):
        set_1q_gate_error(cf['gate_1q'],T1,T2, noise_model, qubit)
        set_read_error(cf['read_err'], noise_model,qubit)
    set_2q_gate_error(cf['gate_2q'],T1,T2, noise_model, [0, 1])  # Assuming gate qubits 0 and 1
    return noise_model


#...!...!....................
def set_1q_gate_error(cf,T1,T2, noise_model, qubit):
    """Set single-qubit gate error."""
    gateN=sorted(cf.keys())
    #print('kk1',gateN)
    for gate in cf:
        gcf=cf[gate]
        duration=gcf['duration_us'] * 1e-6
        fidelity = gcf['fidelity']
        gate_error = 1 - fidelity
    
        pauli_err = errors.pauli_error([('X', gate_error / 2), ('I', 1 - gate_error / 2)])
        thermal_err = errors.thermal_relaxation_error(T1, T2, duration, excited_state_population=0)
        combined_error = pauli_err.compose(thermal_err)
        # Apply the combined error to each specified gate on the given qubit
        noise_model.add_quantum_error(combined_error, gate, [qubit])
        print('  added noise q%d:%s'%(qubit,gate),gcf)

        
#...!...!....................
def set_2q_gate_error(cf,T1,T2, noise_model, qubits):
    """Set two-qubit gate error."""
    gateN=sorted(cf.keys())
    #print('kk2',gateN,cf)
    for gate in cf:
        gcf=cf[gate]
        duration=gcf['duration_us'] * 1e-6
        fidelity = gcf['fidelity']
        gate_error = 1 - fidelity
   
        pauli_err = errors.pauli_error(
            [('XX', gate_error / 4), ('YY', gate_error / 4),
             ('ZZ', gate_error / 4), ('II', 1 - 3 * gate_error / 4)])
        thermal_err_q1 = errors.thermal_relaxation_error(
            T1, T2, duration, excited_state_population=0)
        thermal_err_q2 = errors.thermal_relaxation_error(
            T1, T2, duration, excited_state_population=0)
        combined_error = pauli_err.compose(thermal_err_q1).compose(thermal_err_q2)
        
        # Apply the combined error to each specified gate on the given qubit pairs
        noise_model.add_quantum_error(combined_error, gate, qubits)
        print('  added noise q%s:%s'%(qubits,gate),gcf)

        
#...!...!....................
def set_read_error(probs, noise_model,qubit):
    """Configure the noise model based on readout error probabilities."""
   
    prob_matrix = [[probs['set0meas0'], 1 - probs['set0meas0']],
                   [1 - probs['set1meas1'], probs['set1meas1']]]
    readout_error = errors.ReadoutError(prob_matrix)
    noise_model.add_readout_error(readout_error, [qubit])
    print('  read noise q%d'%(qubit),probs)
