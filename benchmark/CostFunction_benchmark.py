# 1. get result
# 2. js, norm,  fidelity, evaluate

# Jensen-Shannonダイバージェンス
import numpy as np
from scipy.spatial.distance import jensenshannon
from qiskit import execute, Aer, IBMQ

from palloq.compiler import multi_transpile
from palloq.multicircuit.OptimizationFunction import DurationTimeCost
from palloq.multicircuit.mcircuit_composer import MCC_random, MCC
from palloq.utils import get_IBMQ_backend
from utils import PrepareQASMBench


def execute_circuits(circuit, backend, shots, opt_level=1):
    """
    Arguments:
       circuit: (QuantumCircuit)
       backend: IBMQ backends
       shots: (int)
    """
    # Execute
    job = execute(circuit,
                  backend=backend,
                  shots=shots,
                  optimization_level=opt_level)
    return job.result().get_counts(circuit)


def compose_circuits(circuits,
                     composer,
                     device_size,
                     threshold,
                     cost_function):
    """
    Arguments:
       circuits: (List[QuantumCircuit]) list of QuantumCircuit
       composer: 
    """
    # initialize composer
    _composer = composer(circuits, device_size, threshold, cost_function)
    # give circuits to the composoer
    mcircuit = _composer.compose()
    # get the composed circuit
    return mcircuit


def multicompile_circuits(mcircuit):
    """
    Arguments:
       mcircuit: (mcircuit) Composed circuits
    """

    qcircuits = mcircuit.circuits()
    return multi_transpile(qcircuits)


def jsd(results):
    """
    1. get computational result
    2. calculate jsd

    Argument:
        result: (list(dict)) [{'00':100, '11': 100},
                              {'00': 200, '11': 0}]
    """
    if len(results) != 2:
        raise Exception("The size of result must be two.")

    # 1. calculate probability distribution
    prob1, prob2 = results

    # 00, 01, 10, 11 
    base = len(next(iter(prob1)))
    base2 = len(next(iter(prob2)))

    if base != base2:
        raise Exception("The sizes of two binaries are different.")

    # binary = ['00', '01', '10', '11']
    binary = [format(i, '0%db' % base) for i in range(2**base)]

    prob_dist1 = np.array([])
    prob_dist2 = np.array([])
    # take results according to binary table
    shots1 = sum(prob1.values())  # ex. 200
    shots2 = sum(prob2.values())  # ex. 200

    for b in binary:
        np.append(prob_dist1, prob1.get(b, 0) / shots1)
        np.append(prob_dist2, prob2.get(b, 0) / shots2)

    jsd = jensenshannon(prob_dist1, prob_dist2)
    return jsd


def experiment():
    IBMQ.load_account()
    ibmq_sydney = get_IBMQ_backend("ibmq_sydney")
    qasm_simulator = Aer.get_backend('qasm_simulator')
    # 0. prepare circuits
    qasm_bench = ["adder_n4",
                  "basis_change_n3",
                  "basis_trotter_n4",
                  "bell_n4",
                  "cat_state_n4"]
    qcircuit = PrepareQASMBench(qasm_bench, "qasmbench.pickle").qc_list()
    # 1. compose_circuits
    mcircuit = compose_circuits(qcircuit, MCC, 27, 200000, DurationTimeCost)
    rcircuit = compose_circuits(qcircuit, MCC_random, 27, None, None)
    # 2. compile circuits
    qc = multicompile_circuits(mcircuit)
    qc2 = multicompile_circuits(rcircuit)
    # 3. execute circuits
    results1 = []
    results2 = []
    results1.append(execute_circuits(qc, ibmq_sydney, 1024))
    results1.append(execute_circuits(qc, qasm_simulator, 1024))

    results2.append(execute_circuits(qc2, ibmq_sydney, 1024))
    results2.append(execute_circuits(qc2, qasm_simulator, 1024))

    # 4. calculate jsd
    jsd1 = jsd(results1)
    jsd2 = jsd(results2)

    print(jsd1, jsd2)


if __name__ == "__main__":
    experiment()