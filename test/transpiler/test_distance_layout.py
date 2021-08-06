# 2021 / 8 /
# qiskit version 0.27.0


import unittest

from qiskit.circuit.quantumcircuit import QuantumCircuit
from qiskit.providers import backend

from palloq.transpiler.passes.layout.distance_layout import DistanceMultiLayout
from qiskit.converters import circuit_to_dag
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, circuit
from qiskit.test.mock import FakeManhattan


class TestDistanceLayout(unittest.TestCase):
    def test_run_sigledag(self):

        # prepare test dag
        qr = QuantumRegister(3)
        cr = ClassicalRegister(3)
        qc = QuantumCircuit(qr, cr)
        qc.toffoli(qr[0], qr[1], qr[2])
        qc.measure(qr, cr)
        dag = circuit_to_dag(qc)

        # prepare mock backend info
        backend = FakeManhattan()
        bprop = backend.properties()
        coupling_map = backend.configuration().coupling_map

        dml = DistanceMultiLayout(
            backend_prop=bprop,
            coupling_map=coupling_map,
        )

        mapped_dag = dml.run(next_dag=dag)

        self.assertEqual(dag, mapped_dag)

    def test_run_twodag(self):

        # prepare test dag1
        qr1 = QuantumRegister(3)
        cr1 = ClassicalRegister(3)
        qc1 = QuantumCircuit(qr1, cr1)
        qc1.toffoli(qr1[0], qr1[1], qr1[2])
        qc1.measure(qr1, cr1)
        dag1 = circuit_to_dag(qc1)

        # prepare test dag2
        qr2 = QuantumRegister(3)
        cr2 = ClassicalRegister(3)
        qc2 = QuantumCircuit(qr2, cr2)
        qc2.toffoli(qr2[0], qr2[1], qr2[2])
        qc2.measure(qr2, cr2)
        dag2 = circuit_to_dag(qc2)

        # prepare mock backend info
        backend = FakeManhattan()
        bprop = backend.properties()
        coupling_map = backend.configuration().coupling_map

        dml = DistanceMultiLayout(
            backend_prop=bprop,
            coupling_map=coupling_map,
        )

        init_dag = dml.run(next_dag=dag1)
        mapped_dag = dml.run(next_dag=dag2, init_dag=init_dag)

        self.assertEqual(dag1, init_dag)
        self.assertNotEqual(dag1, mapped_dag)
        self.assertNotEqual(dag2, mapped_dag)

        self.asertEqual(dag1.qubits, init_dag.qubits)
        self.asertEqual(dag1.qubits[0], mapped_dag.qubits[0:3][0])
        self.asertEqual(dag1.qubits[0], mapped_dag.qubits[3:6][0])


if __name__ == "__main__":
    unittest.main()
