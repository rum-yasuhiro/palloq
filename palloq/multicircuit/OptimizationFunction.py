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

    Arguments:
        circuit_pairs: (list) List of Quantum Circuit to calculate cost
        device_errors: (?) Device error information
        device_topology: (np.ndarray, list or Other) Qubit
        topology of target device

    FIXME If you don't need  some of parameters, please remove it.
    """
    def __init__(self,
                 circuit_pairs: List[QuantumCircuit],
                 device_errors: List[float] = None,
                 device_topology: List = None):
        if isinstance(circuit_pairs, (Iterable)):
            if all(map(lambda x: isinstance(x, QuantumCircuit), circuit_pairs)):
                self.circuit_pairs = circuit_pairs
            else:
                raise ValueError("Argument circuit_pairs must \
be the iterable of Quantum Circuit")
        else:
            raise TypeError(f"Argument circuit_pairs must be the iterable \
of Quantum Circuit not {type(circuit_pairs)}")
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
        # 1. take information
        # self.circuit_pairs
        # self.device_errors
        # self.device_topology
        # depths = np.array([qc.depth() for qc in self.circuit_pairs]) etc.

        # 2. Using these information, calculate cost
        # etc. e*depth

        # 3. updating cost
        # cost = sum([...])
        return cost

    def cost(self):
        cost = self._calculate_cost(self)
        return cost


# if __name__ == "__main__":
#     # multicircuit converter
#     qcs = []
#     costfunction = CostFunctions()
#     cost = costfunction.cocori_function(qcs)