# 2021 / 8 / 11
# qiskit version 0.27.0


import unittest
from datetime import datetime

from qiskit.circuit.quantumcircuit import QuantumCircuit
from qiskit.converters.dag_to_circuit import dag_to_circuit
from qiskit.compiler import transpile
from qiskit.providers.models import BackendProperties
from qiskit.providers.models.backendproperties import Nduv, Gate
from palloq.transpiler.passes.layout.buffered_layout import BufferedMultiLayout
from qiskit.converters import circuit_to_dag
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, circuit
from qiskit.test.mock import FakeManhattan
from qiskit.transpiler.layout import Layout


def make_qubit_with_error(readout_error):
    """Create a qubit for BackendProperties"""
    calib_time = datetime(year=2021, month=8, day=11, hour=0, minute=0, second=0)
    return [
        Nduv(name="T1", date=calib_time, unit="µs", value=100.0),
        Nduv(name="T2", date=calib_time, unit="µs", value=100.0),
        Nduv(name="frequency", date=calib_time, unit="GHz", value=5.0),
        Nduv(name="readout_error", date=calib_time, unit="", value=readout_error),
    ]


class TestBufferedLayout(unittest.TestCase):
    def test_run_singledag(self):

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

        dml = BufferedMultiLayout(
            backend_prop=bprop,
        )

        mapped_dag = dml.run(next_dag=dag)

        self.assertEqual(dag, mapped_dag)

    def test_run_twodag(self):

        # prepare mock backend info
        backend = FakeManhattan()
        basis_gates = backend.configuration().basis_gates
        bprop = backend.properties()

        # prepare test dag1
        qr1 = QuantumRegister(3, "q1")
        cr1 = ClassicalRegister(3)
        qc1 = QuantumCircuit(qr1, cr1)
        qc1.toffoli(qr1[0], qr1[1], qr1[2])
        qc1.measure(qr1, cr1)
        qc1 = transpile(
            circuits=qc1,
            basis_gates=basis_gates,
        )
        dag1 = circuit_to_dag(qc1)

        # prepare test dag2
        qr2 = QuantumRegister(3, "q2")
        cr2 = ClassicalRegister(3)
        qc2 = QuantumCircuit(qr2, cr2)
        qc2.toffoli(qr2[2], qr2[1], qr2[0])
        qc2.measure(qr2, cr2)
        qc2 = transpile(
            circuits=qc2,
            basis_gates=basis_gates,
        )
        dag2 = circuit_to_dag(qc2)

        # initialize dml
        dml = BufferedMultiLayout(
            backend_prop=bprop,
        )

        init_dag = dml.run(next_dag=dag1)
        mapped_dag = dml.run(next_dag=dag2, init_dag=init_dag)

        self.assertEqual(dag1, init_dag)
        self.assertNotEqual(dag1, mapped_dag)
        self.assertNotEqual(dag2, mapped_dag)
        self.assertEqual(dag1.qubits, init_dag.qubits)
        self.assertEqual(dag1.qubits[0], mapped_dag.qubits[0:3][0])
        self.assertEqual(dag2.qubits[0], mapped_dag.qubits[3:6][0])

    def test_noisy_backend1(self):

        # prepare mock backend info
        calib_time = datetime(year=2021, month=8, day=11, hour=0, minute=0, second=0)

        num_qubits = 6
        qubit_list = [make_qubit_with_error(0.01) for _ in range(num_qubits)]

        p01 = [Nduv(date=calib_time, name="gate_error", unit="", value=0.7)]
        g01 = Gate(name="CX0_1", gate="cx", parameters=p01, qubits=[0, 1])
        p12 = [Nduv(date=calib_time, name="gate_error", unit="", value=0.1)]
        g12 = Gate(name="CX1_2", gate="cx", parameters=p12, qubits=[1, 2])
        p23 = [Nduv(date=calib_time, name="gate_error", unit="", value=0.9)]
        g23 = Gate(name="CX2_3", gate="cx", parameters=p23, qubits=[2, 3])
        p34 = [Nduv(date=calib_time, name="gate_error", unit="", value=0.1)]
        g34 = Gate(name="CX3_4", gate="cx", parameters=p34, qubits=[3, 4])
        p45 = [Nduv(date=calib_time, name="gate_error", unit="", value=0.6)]
        g45 = Gate(name="CX4_5", gate="cx", parameters=p45, qubits=[4, 5])

        gate_list = [g01, g12, g23, g34, g45]
        bprop = BackendProperties(
            last_update_date=calib_time,
            backend_name="test_backend",
            qubits=qubit_list,
            backend_version="1.0.0",
            gates=gate_list,
            general=[],
        )

        # prepare test dag1
        qr1 = QuantumRegister(3, "q1")
        cr1 = ClassicalRegister(3)
        qc1 = QuantumCircuit(qr1, cr1)
        # weight 2 on (0, 1) and weight 1 on (1, 2)
        qc1.cx(qr1[0], qr1[1])
        qc1.cx(qr1[1], qr1[0])
        qc1.cx(qr1[1], qr1[2])
        qc1.measure(qr1, cr1)
        dag1 = circuit_to_dag(qc1)

        # prepare test dag2
        qr2 = QuantumRegister(3, "q2")
        cr2 = ClassicalRegister(3)
        qc2 = QuantumCircuit(qr2, cr2)
        # weight 1 on (0, 1) and weight 2 on (1, 2)
        qc2.cx(qr2[0], qr2[1])
        qc2.cx(qr2[1], qr2[2])
        qc2.cx(qr2[2], qr2[1])
        qc2.measure(qr2, cr2)
        dag2 = circuit_to_dag(qc2)

        # initialize and run bm_layout
        bm_layout = BufferedMultiLayout(
            backend_prop=bprop,
        )
        init_dag = bm_layout.run(next_dag=dag1)
        mapped_dag = bm_layout.run(next_dag=dag2, init_dag=init_dag)
        initial_layout = bm_layout.property_set["layout"]
        self.assertEqual(initial_layout[0], qr1[2])
        self.assertEqual(initial_layout[5], qr2[0])

        # initialize and run bm_layout
        bm_layout = BufferedMultiLayout(
            backend_prop=bprop,
            n_hop=1,
        )
        init_dag = bm_layout.run(next_dag=dag1)
        mapped_dag = bm_layout.run(next_dag=dag2, init_dag=init_dag)
        initial_layout = bm_layout.property_set["layout"]
        self.assertEqual(initial_layout[0], qr1[2])
        self.assertEqual(init_dag, mapped_dag)

    def test_noisy_backend2(self):

        # prepare mock backend info
        calib_time = datetime(year=2021, month=8, day=11, hour=0, minute=0, second=0)

        num_qubits = 6
        qubit_list = [make_qubit_with_error(0.01) for _ in range(num_qubits)]

        p01 = [Nduv(date=calib_time, name="gate_error", unit="", value=0.7)]
        g01 = Gate(name="CX0_1", gate="cx", parameters=p01, qubits=[0, 1])
        p12 = [Nduv(date=calib_time, name="gate_error", unit="", value=0.1)]
        g12 = Gate(name="CX1_2", gate="cx", parameters=p12, qubits=[1, 2])
        p23 = [Nduv(date=calib_time, name="gate_error", unit="", value=0.1)]
        g23 = Gate(name="CX2_3", gate="cx", parameters=p23, qubits=[2, 3])
        p34 = [Nduv(date=calib_time, name="gate_error", unit="", value=0.1)]
        g34 = Gate(name="CX3_4", gate="cx", parameters=p34, qubits=[3, 4])
        p45 = [Nduv(date=calib_time, name="gate_error", unit="", value=0.6)]
        g45 = Gate(name="CX4_5", gate="cx", parameters=p45, qubits=[4, 5])

        gate_list = [g01, g12, g23, g34, g45]
        bprop = BackendProperties(
            last_update_date=calib_time,
            backend_name="test_backend",
            qubits=qubit_list,
            backend_version="1.0.0",
            gates=gate_list,
            general=[],
        )

        # prepare test dag1
        qr1 = QuantumRegister(3, "q1")
        cr1 = ClassicalRegister(3)
        qc1 = QuantumCircuit(qr1, cr1)
        # weight 2 on (0, 1) and weight 1 on (1, 2)
        qc1.cx(qr1[0], qr1[1])
        qc1.cx(qr1[1], qr1[0])
        qc1.cx(qr1[1], qr1[2])
        qc1.measure(qr1, cr1)
        dag1 = circuit_to_dag(qc1)

        # prepare test dag2
        qr2 = QuantumRegister(3, "q2")
        cr2 = ClassicalRegister(3)
        qc2 = QuantumCircuit(qr2, cr2)
        # weight 1 on (0, 1) and weight 2 on (1, 2)
        qc2.cx(qr2[0], qr2[1])
        qc2.cx(qr2[1], qr2[2])
        qc2.cx(qr2[2], qr2[1])
        qc2.measure(qr2, cr2)
        dag2 = circuit_to_dag(qc2)

        # initialize bm_layout
        bm_layout = BufferedMultiLayout(
            backend_prop=bprop,
        )

        init_dag = bm_layout.run(next_dag=dag1)
        mapped_dag = bm_layout.run(next_dag=dag2, init_dag=init_dag)

        self.assertEqual(init_dag, mapped_dag)


if __name__ == "__main__":
    unittest.main()
