from typing import Union, List
from qiskit import QuantumCircuit
from .OptimizationFunction import CostFunctions


class MultiCircuitConverter:
    '''
    MultiCircuitConverter combine multiple circuit to a list based on ESP.

    Arguments:

    '''

    def __init__(self,
                 qcircuits: List[QuantumCircuit] = None,
                 max_size=10) -> None:
        self.max_size = max_size
        if qcircuits is not None:
            # Other data type is also availale
            if not isinstance(qcircuits, list):
                raise TypeError(f"qcircuits must be a list of QuantumCircuit, not {type(qcircuits)}")
            if not all([isinstance(qc, QuantumCircuit) for qc in qcircuits]):
                raise ValueError("All elements in qcircuits must be Quantum Circuit")
            self.qcircuits = qcircuits
        else:
            self.qcircuits = []
        self.opt_combo = []
        # cost function no atumari
        self.cost_function = CostFunctions()

    def optimize(self) -> None:
        """
        This is the core function that optimize the combination of circuit
        """
        costs = []
        for i, v in enumerate(self.qcs):
            cost = self.cost_function.cocori_function(v)
            costs.append(cost)

    def has_qc(self) -> bool:
        return len(self.qcircuits) > 0
    
    def pop(self):
        self.opt_combo.pop()

    def push(self,
             qc: QuantumCircuit) -> None:
        if not isinstance(qc, QuantumCircuit):
            raise ValueError(f"qc must be Quantum Circuit not {type(qc)}")
        self.qcircuits.append(qc)


class MultiCircuit:
    def __init__(self, name=None):
        if name is None:
            self.name = str(__name__)
        else:
            self.name = name

    def __repr__(self):
        return self.name


if __name__ ==  "__main__":
    # user
    qcs = []
    #  ------ run compiler --------
    # qc = [qc1, qc2, qc3, qc4, ... qcn] --> Input
    multi = MultiCircuitConverter(qcs)
    multi.optimize()
    # [[quantum circuit, qc2, qc3], [qc11, qc12], ..., []] -> Output
    circuits = multi.pop()
