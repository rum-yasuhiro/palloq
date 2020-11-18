from typing import List, Tuple, Union, Iterable
from fractions import Fraction
from scipy.optimize import fmin
from qiskit import QuantumCircuit
import abc
import math
import numpy as np


# What is input?
# Ei = np.array([]) #list of error rates of specific block
# Emn = 1 #one link error rate for one alogrithm
# gamma = 1 #constant
# occ = Fraction(qc.num_qubits) #number of qubits in quantum computer ) #occupation rate

# opt = Fraction(gamma,occ) * sum np.prod(Ei) * Emn

# print(opt)
# # What is output?


class CostFunction(metaclass=abc.ABCMeta):
    "a series of cost functions"
    def __init__(self):
        pass

    @abc.abstractmethod
    def cost(self):
        """
        Function return cost of circuit pairs
        """
        pass


class DepthBaseCost(CostFunction):
    """
    This Cost function returns a cost taking
    several quantum circuits as inputs.

QuantumCircuit.depth:depth
QuantumCircuit.size():Returns total number of gate operations in circuit.
QuantumCircuit.count_ops():Count each operation kind in the circuit.
QuantumCircuit.num_qubits:Return number of qubits.

    Arguments:
        circuit_pairs: (list) List of Quantum Circuit to calculate cost
        device_errors: (?) Device error information
        device_topology: (np.ndarray, list or Other) Qubit
        topology of target device
        
    FIXME If you don't need  some of parameters, please remove it.
    """
    def __init__(self,
                 total_qubits: int,
                 device_errors: List[float] = None,
                 device_topology: List = None):
        if not isinstance(total_qubits, int):
            raise TypeError("total_qubits must be int")
        self.total_qubits = total_qubits
        self.device_errors = device_errors
        self.device_topology = device_topology

    def _calculate_cost(self) -> float:
        """
        Todo:
            1: Get circuits information (depth, gates etc.)
            2: Based on that information, calculate cost.
            3: Update cost based on that.
        """
        cost = 0
        depth = []
        num_qubits = []
        # # 1. take information
        # # self.circuit_pairs
        # # self.device_errors
        # # self.device_topology
        # # depths = np.array([qc.depth() for qc in self.circuit_pairs]) etc.
        for QuantumCircuit in self.circuit_pairs:
            depth = QuantumCircuit.depth()
            depth.append(depth)
            num_qubits = QuantumCircuit.num_qubits()
            num_qubits.append(num_qubits)

        # # 2. Using these information, calculate cost
        # # etc. e*depth

        cost = depth * num_qubits
        """
        cost計算
        """

        # 3. updating cost
        # cost = sum([...])
        return cost

    def cost(self, circuit_pairs):
        if isinstance(circuit_pairs, (Iterable)):
            if all(map(lambda x: isinstance(x, QuantumCircuit),
                       circuit_pairs)):
                self.circuit_pairs = circuit_pairs
            else:
                raise ValueError("Argument circuit_pairs must \
be the iterable of Quantum Circuit")
        else:
            raise TypeError("Argument circuit_pairs must be the iterable \
of Quantum Circuit not {type(circuit_pairs)}")
        cost = self._calculate_cost()
        return cost


if __name__ == "__main__":
    # multicircuit converter
    circuit_pairs = [QuantumCircuit(3), QuantumCircuit(4)]
    # List[QuantumCircuit]
    costfunction = DepthBaseCost(circuit_pairs)
    cost = costfunction.cost()
    print(cost)
