import numpy as np
import copy
import logging

from typing import Union, List
from qiskit import QuantumCircuit
from palloq.multicircuit.OptimizationFunction import CostFunction, DepthBaseCost


_log = logging.getLogger(__name__)


class MultiCircuitConverter:
    '''
    MultiCircuitConverter combine multiple circuit to a list based on ESP.

    Arguments:
        qcircuits: (list) List of Quantum Circuits
        max_size: (int) The number of qubits in device
        threshold: (float) the threshold to cut the circuit pairs
        cost_function: (CostFunction) costfunction to evaluate circuit pairs
    '''
    def __init__(self,
                 qcircuits: List[QuantumCircuit],
                 device_size: int,
                 threshold: float,
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
        self._threshold = threshold
        self.optimized_circuits = []
        # cost functions
        if issubclass(cost_function, CostFunction):
            self.cost_function = cost_function
        else:
            raise ValueError("Argument cost_function must\
 be subclass of CostFunction")

    def _optimize(self) -> None:
        """
        TEST
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

    def optimize(self) -> None:
        """
        This is the core function that optimize the combination of circuit
        - Max: Throughput
        - Min: Error rate (For all quantum circuit)
        """
        # FIXME here using class variables, but could be global scope
        self._cost_func = self.cost_function(self._device_size)
        self._candidates = []

        # depth first search
        def dfs(circuits: List,
                index: int):
            # TODO clean up
            # depth first search
            # circuits: [(index, QuantumCircuit)]
            _circuit_instances = [i[1] for i in circuits]
            total_qubits = sum([i.num_qubits for i in _circuit_instances])
            _cost = self._cost_func.cost(_circuit_instances)
            # Three conditions to quit this dfs
            if (total_qubits >= self._device_size or
               _cost >= self._threshold or index >= len(self.qcircuits)):
                _c = self._cost_func.cost(_circuit_instances[:-1])
                self._candidates.append((circuits[:-1], _c))
                return
            # don't add
            _nqc = copy.copy(circuits)
            _nqc.append((index, self.qcircuits[index]))
            # add index+1 circuits
            dfs(_nqc, index+1)
            dfs(circuits, index+1)

        dfs([(0, self.qcircuits[0])], 1)

        # FIXME Post processing 
        _sorted_candidates = sorted(self._candidates,
                                    key=lambda x: (len(x[0]), 1/(x[1]+1e-6)),
                                    reverse=True)
        _best_choice = None
        # TODO max len
        for _choice in _sorted_candidates:
            if len(_choice[0]) > 1:
                _best_choice = _choice
                break
        _log.info("choice", _best_choice)
        if _best_choice is None:
            _log.info("No good grouping is found. All sequencially")
            for qc in self.qcircuits:
                _mulcirc = MultiCircuit()
                _mulcirc.set_circuit_pairs([qc])
                _mulcirc.set_cost(0)
                # just pop out from the first cicuit
                self.qcircuits.pop(0)
                # What is the cost in the sequencial execution?
                self.optimized_circuits.append(_mulcirc)
        else:
            # take circuits and costs from choice
            _qcs, _cost = _best_choice
            # get circuit index and instances
            _index, _circuits = _qcs[0]
            self.qcircuits.pop(_index)
            _mulcirc = MultiCircuit()
            _mulcirc.set_circuit_pairs(_circuits)
            _mulcirc.set_cost(_cost)
            self.optimized_circuits.append(_mulcirc)

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
        self.cost = 0

    def __repr__(self):
        return self.name

    def set_circuit_pairs(self, circuits):
        self.circuit_pairs = circuits

    def circuits(self):
        # TODO could be generator
        return self.circuit_pairs

    def set_cost(self, _cost):
        self.cost = _cost


if __name__ == "__main__":
    # user
    qcs = []
    #  ------ run compiler --------
    # qc = [qc1, qc2, qc3, qc4, ... qcn] --> Input
    multi = MultiCircuitConverter(qcs, 100)
    multi.optimize()
    # [[quantum circuit, qc2, qc3], [qc11, qc12], ..., []] -> Output
    # circuits = multi.pop()
