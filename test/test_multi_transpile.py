from qiskit import Aer
from qiskit.transpiler import Layout
from qiskit.converters import circuit_to_dag
from qiskit.circuit import QuantumCircuit
from qiskit.test.mock import *

from palloq.compiler.multi_transpile import multi_transpile

def test_multi_transpile(small_circuits):
    circuit_list = small_circuits[:2]
    xtalk_prop = {(0, 1): {(2, 3): 2}}

    qc_multi = multi_transpile(circuit_list)
    qc_3pm = multi_transpile(circuit_list, optimization_level=3)
    qc_xtalk = multi_transpile(circuit_list, layout_method='xtalk_adaptive', xtalk_prop=xtalk_prop)

    assert isinstance(qc_multi, QuantumCircuit)
    assert isinstance(qc_3pm, QuantumCircuit)
    assert isinstance(qc_xtalk, QuantumCircuit)

def test_transpile_with_ibmq_qasm_simulator(small_circuits):
    circuit_list = small_circuits[:2]
    simulator = Aer.get_backend('qasm_simulator')
    qc_multi = multi_transpile(circuit_list, backend=simulator)
    
    print("layout: ", qc_multi._layout)
    assert isinstance(qc_multi, QuantumCircuit)

def test_transpile_with_ibmqs(small_circuits):
    circuit_list = small_circuits[:2]
    paris = FakeParis()
    qc_multi = multi_transpile(circuit_list, backend=paris)
    
    print("layout: ", qc_multi._layout)
    assert isinstance(qc_multi, QuantumCircuit)

def test_layout():
    qc0 = QuantumCircuit(3)
    qc1 = QuantumCircuit(3)

    qc0.h(0)
    qc0.cx(0, 1)
    qc0.cx(1, 2)

    qc1.h(0)
    qc1.cx(0, 1)
    qc1.cx(1, 2)

    circuit_list = [qc0, qc1]
    paris = FakeParis()
    qc_multi = multi_transpile(circuit_list, backend=paris)
    print("layout: ", qc_multi._layout)
    assert isinstance(qc_multi, QuantumCircuit)