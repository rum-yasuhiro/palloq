import abc
import numpy as np
import copy
import logging

from typing import Union, List
from qiskit import QuantumCircuit
from palloq.multicircuit.OptimizationFunction import CostFunction, DepthBaseCost
from palloq.utils.esp import esp


_log = logging.getLogger(__name__)


class MultiCircuitComposer(metaclass=abc.ABCMeta):
    """
    Metaclass for cirucit composers
    """
    @abc.abstractmethod
    def compose():
        """
        compose multiple circuit into list of circuits
        """
        pass


class MCC(MultiCircuitComposer):
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

    def compose(self) -> bool:
        """
        This is the core function that optimize the combination of circuit
        - Max: Throughput
        - Min: Error rate (For all quantum circuit)

        if there is no more possible compbination,
        this function returns False, otherwise True
        """
        # FIXME here using class variables, but could be global scope
        self._cost_func = self.cost_function(self._device_size)
        _candidates = []

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
                _candidates.append((circuits[:-1], _c))
                return
            # don't add
            _nqc = copy.copy(circuits)
            _nqc.append((index, self.qcircuits[index]))
            # add index+1 circuits
            dfs(_nqc, index+1)
            dfs(circuits, index+1)

        dfs([(0, self.qcircuits[0])], 1)

        # FIXME Post processing 
        _sorted_candidates = sorted(_candidates,
                                    key=lambda x: (len(x[0]), 1/(x[1]+1e-6)),
                                    reverse=True)
        _best_choice = None
        # TODO max len
        for _choice in _sorted_candidates:
            if len(_choice[0]) > 1:
                _best_choice = _choice
                break
        _log.info(f"choice: {'Single' if _best_choice is None else 'Multi'}")
        # If there is no chice to take, then just return single qc
        if _best_choice is None:
            _log.info("No good grouping is found. Return single circuit")
            # prepare multi circuit class
            mulcirc = MultiCircuit()
            # pop out from quantum circuit
            _qc = self.qcircuits.pop(0)
            mulcirc.set_circuit_pairs([_qc])
            mulcirc.set_cost(0)
            # What is the cost in the sequencial execution?
            return mulcirc
        else:
            _log.info("pop out circuit based on cost calculations")
            # take circuits and costs from choice
            _qcs, _cost = _best_choice
            # get circuit index and instances
            _index, _circuits = _qcs[0]
            # TODO check if this process is working properly
            # print(_index, _circuits)
            self.qcircuits.pop(_index)
            mulcirc = MultiCircuit()
            mulcirc.set_circuit_pairs(_circuits)
            mulcirc.set_cost(_cost)
            return mulcirc

    def has_qc(self) -> bool:
        return len(self.qcircuits) > 0

    def push(self,
             qc: QuantumCircuit) -> None:
        if not isinstance(qc, QuantumCircuit):
            raise ValueError(f"qc must be Quantum Circuit not {type(qc)}")
        self.qcircuits.append(qc)


class MCC_dp(MultiCircuitComposer):
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
                 eval_func=esp) -> None:

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
        # function that evaluate circuit
        self.eval_func = eval_func

    def compose(self) -> None:
        """
        optimize circuit conbination based on just single circuit property.

        Optimization policy:
            combine high esp circuits as many as possible 
        """
        # 0. size of total quantum circuits
        n = len(self.qcircuits)
        W = self._device_size

        # 1. The number of qubits in one circuit
        # corresonds to the weight for it
        weights = [qc.num_qubits for qc in self.qcircuits]
        # using estimated successs probability as the value for single circuit
        # TODO take this as class argument
        error_rates = {"u3": 0.0001,
                       "cx": 0.001,
                       "id": 0}
        # TODO find proper evaluation method for one
        # circuit in multiple circuit
        values = [self.eval_func(qc, error_rates) for qc in self.qcircuits]

        # 2. prepare dp table and reverse table
        dp = [[0] * (W) for _ in range(n+1)]
        rev = [[0] * (W) for _ in range(n+1)]

        # 2.1 Initialize dp table
        for w in range(W):
            dp[0][w] = 0

        # 3. loop dp
        for i in range(n):
            for w in range(W):
                # pick up ith item
                if w >= weights[i]:
                    if dp[i+1][w] < dp[i][w-weights[i]] + values[i]:
                        dp[i+1][w] = dp[i][w-weights[i]] + values[i]
                        rev[i+1][w] = w - weights[i]

                # do not pick up ith item
                if dp[i+1][w] < dp[i][w]:
                    dp[i+1][w] = dp[i][w]
                    rev[i+1][w] = w
        # 4. optimal
        _combination = []
        cur_w = W - 1
        for i in range(n-1, -1, -1):
            if rev[i+1][cur_w] == cur_w - weights[i]:
                _combination.append(i)
            cur_w = rev[i+1][cur_w]
        # 5. calculate costs
        if _combination == []:
            return self.qcircuits.pop(0)
        else:
            # 5.1 create multi circuit class and add circuit
            mult = MultiCircuit()
            mult.set_circuit_pairs([self.qcircuits[i] for i in _combination])
            for i, corr in enumerate(sorted(_combination)):
                if len(self.qcircuits) == 0:
                    break
                # need correction for popout
                self.qcircuits.pop(corr-i)
            return mult

    def has_qc(self) -> bool:
        return len(self.qcircuits) > 0

    def push(self,
             qc: QuantumCircuit) -> None:
        if not isinstance(qc, QuantumCircuit):
            raise ValueError(f"qc must be Quantum Circuit not {type(qc)}")
        self.qcircuits.append(qc)


class MCC_random(MultiCircuitComposer):
    '''
    Random Circuit composer.

    Arguments:
        qcircuits: (list) List of Quantum Circuits
        max_size: (int) The number of qubits in device
        threshold: (float) the threshold to cut the circuit pairs
        cost_function: (CostFunction) costfunction to evaluate circuit pairs
    '''
    def __init__(self,
                 qcircuits: List[QuantumCircuit],
                 device_size: int,
                 threshold: int,
                 eval_func=esp) -> None:

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
        # function that evaluate circuit
        self.eval_func = eval_func

    def compose(self) -> None:
        """
        optimize circuit conbination based on just single circuit property.

        Optimization policy:
            combine high esp circuits as many as possible 
        """
        indices = []
        qcs = []
        nq = 0
        for iq, qc in enumerate(self.qcircuits):
            nq += qc.num_qubits
            if nq > self._device_size:
                break
            indices.append(iq)
            qcs.append(qc)
        mcirc = MultiCircuit()
        mcirc.set_circuit_pairs(qcs)
        return mcirc

    def has_qc(self) -> bool:
        return len(self.qcircuits) > 0

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