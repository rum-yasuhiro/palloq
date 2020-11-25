import pytest

from palloq import MultiCircuitConverter, MultiCircuit
from qiskit import QuantumCircuit


class TestMultiCircuitConverter:

    @pytest.fixture
    def dummy_device(self):
        pass

    def test_init(self, small_circuits):
        multi_conv = MultiCircuitConverter(small_circuits, 10)
        assert multi_conv.qcircuits == small_circuits

    def test_optimize(self, small_circuits):
        multi_conv = MultiCircuitConverter(small_circuits, 10)
        multi_conv.optimize()
        print(multi_conv.optimized_circuits)

    def test_has_qc(self):
        pass

    def test_pop(self):
        pass

    def test_push(self):
        pass