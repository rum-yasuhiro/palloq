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


if __name__ == "__main__":
    unittest.main()
