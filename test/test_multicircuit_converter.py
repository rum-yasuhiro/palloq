import pytest

from palloq import MCC, MCC_dp, MCC_random, MultiCircuit
from qiskit import QuantumCircuit


class TestMultiCircuitConverter:

    @pytest.fixture
    def dummy_device(self):
        pass

    def test_init(self, small_circuits):
        multi_conv = MCC(small_circuits, 30, 30)
        assert multi_conv.qcircuits == small_circuits

    def test_optimize(self, small_circuits):
        multi_conv = MCC(small_circuits, 30, 50)
        assert len(multi_conv.qcircuits) == 28
        circuit = multi_conv.compose()
        assert len(multi_conv.qcircuits) == 27

    def test_dp_optimize(self, small_circuits):
        multi_conv = MCC_dp(small_circuits, 10)
        circuit = multi_conv.compose()
    
    def test_mcc_random(self, small_circuits):
        multi_comv = MCC_random(small_circuits, 10, 0.5)
        circuits = multi_comv.compose()
        print(circuits)

    def test_has_qc(self):
        pass

    def test_pop(self):
        pass

    def test_push(self):
        pass