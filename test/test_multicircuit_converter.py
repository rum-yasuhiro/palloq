import pytest

from qiskit import QuantumCircuit


class TestMultiCircuitConverter:

    @pytest.fixturea(scope="class")
    def circuits(self):
        """
        quantum circuits for test
        """
        pass

    @pytest.fixture
    def dummy_device(self):
        pass

    def test_init(self):
        pass

    def test_optimize(self, circuits):
        pass

    def test_has_qc(self):
        pass
    
    def test_pop(self):
        pass

    def test_push(self):
        pass