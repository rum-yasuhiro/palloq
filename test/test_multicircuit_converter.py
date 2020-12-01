import pytest

from palloq import MultiCircuitConverter, MultiCircuit
from qiskit import QuantumCircuit


class TestMultiCircuitConverter:

    @pytest.fixture
    def dummy_device(self):
        pass

    def test_init(self, small_circuits):
        multi_conv = MultiCircuitConverter(small_circuits, 30, 30)
        assert multi_conv.qcircuits == small_circuits

    def test_optimize(self, small_circuits):
        multi_conv = MultiCircuitConverter(small_circuits, 30, 50)
        assert len(multi_conv.qcircuits) == 28
        multi_conv.optimize()
        assert len(multi_conv.qcircuits) == 27

    def test_has_qc(self):
        pass

    def test_pop(self):
        pass

    def test_push(self):
        pass