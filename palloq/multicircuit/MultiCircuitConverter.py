import numpy as np

from typing import Union, List
from qiskit import QuantumCircuit
from .OptimizationFunction import CostFunction, DepthBaseCost


class MultiCircuitConverter:
    '''
    MultiCircuitConverter combine multiple circuit to a list based on ESP.

    Arguments:
        qcircuits: (list) List of Quantum Circuits
        max_size: (int) The number of qubits in device
        cost_function: (CostFunction) costfunction to evaluate circuit pairs
    '''
    def __init__(self,
                 qcircuits: List[QuantumCircuit],
                 device_size: int,
                 cost_function: CostFunction = DepthBaseCost) -> None:

        # The number of qubits in total
        if isinstance(device_size, int):
            self._device_size = device_size
        else:
            raise TypeError("Argument device_size must be int")

        # Other data type is also availale
        if not isinstance(qcircuits, list):
            raise TypeError(f"qcircuits must be a list of QuantumCircuit,\
not {type(qcircuits)}")
        if not all([isinstance(qc, QuantumCircuit) for qc in qcircuits]):
            raise ValueError("All elements in qcircuits \
must be Quantum Circuit")

        if any(map(lambda x:  x.num_qubits > device_size, qcircuits)):
            raise ValueError("One of circuit size is larger than device size.")

        self.qcircuits = qcircuits

        self.optimized_circuits = []
        # cost functions
        if issubclass(cost_function, CostFunction):
            self.cost_function = cost_function
        else:
            raise ValueError("Argument cost_function must\
 be subclass of CostFunction")

    def optimize(self) -> None:
        """
        This is the core function that optimize the combination of circuit

        Todo:
            1. Choose optimization method
            2. Calculate cost
            3. Packing up with 1 and 2

        Basic Optimization strategy.
        - Max: Throughput
        - Min: Error rate (For all quantum circuit)

        1. Prepare circuits with its information (dict?)
        2. 
        """
        # 0. size of total quantum circuits
        n = len(self.qcircuits)
        W = self._device_size

        # 1. translate num qubits as weight.
        # FIXME All of circuits have the same value
        weights = [qc.num_qubits for qc in self.qcircuits]

        # 2. prepare dp table
        dp = [[None]*(W+1) for _ in range(n+1)]
        rev = [[None]*(W+1) for _ in range(n+1)]
        # 2.1 Initialize dp table
        for w in range(W):
            dp[0][w] = 0

        # 3. loop dp
        for i in range(n):
            for w in range(W):
                if w >= weights[i]:
                    dp[i+1][w] = max(dp[i][w-weights[i]] + 1, dp[i][w])
                    rev[i+1][w] = w - weights[i]
                else:
                    dp[i+1][w] = dp[i][w]
                    rev[i+1][w] = w
        # 4. optimal
        _combination = []
        cur_w = W - 1
        for i in range(n):
            if rev[i+1][cur_w] == cur_w - weights[i]:
                _combination.append(i)
                print(i, weights[i], 1)
            cur_w = rev[i+1][cur_w]
        # 5. calculate costs
        _costs = []
        _cost_func = self.cost_function(self._device_size)
        for i, v in enumerate(self.qcircuits):
            pass

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


if __name__ == "__main__":
    # user
    qcs = []
    #  ------ run compiler --------
    # qc = [qc1, qc2, qc3, qc4, ... qcn] --> Input
    multi = MultiCircuitConverter(qcs)
    multi.optimize()
    # [[quantum circuit, qc2, qc3], [qc11, qc12], ..., []] -> Output
    # circuits = multi.pop()
