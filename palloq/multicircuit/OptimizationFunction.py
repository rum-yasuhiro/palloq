from typing import List, Tuple, Union, Iterable
from fractions import Fraction
from scipy.optimize import fmin
from qiskit import QuantumCircuit
import abc
import math
import numpy as np
from datetime import datetime


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
        depth = []
        size = []
        # 1. take information
        # self.circuit_pairs
        # self.device_errors
        # self.device_topology
        # depths = np.array([qc.depth() for qc in self.circuit_pairs]) etc.
        for qc in self.circuit_pairs:
            depth = qc.depth()
            size = qc.num_qubits()

            qc_depth = QuantumCircuit.depth(circuit_pairs) #get the depth imformation
            depth.append(qc_depth) #add the result
        
        for qc_size in self.circuit_pairs:
            qc_size = QuantumCircuit.size(circuit_pairs) #get the size imformation
            size.append(qc_size)#add the result

        for qc_ops in self.circuit_pairs:
        qc_ops = QuantumCircuit.count_ops(circuit_pairs) #Count each operation kind in the circuit.
        """
        errorsのリストはどう読んだら良い？
        """
        a_day = datetime.now()
        backend = provider.backends.ibmq_essex 
        """
        backendsどうすれば？
        """
        prop = backend.properties(datetime=a_day)
        _qubit_key_list = list(prop._gates.get('u1').keys())
        u2_errors = [prop._gates.get('u2').get((0, )).get('gate_error')[0] for qubit in _qubit_key_list]
        u3_errors= [prop._gates.get('u3').get((0, )).get('gate_error')[0] for qubit in _qubit_key_list]

        _cx_key_list = list(prop._gates.get('cx').keys())
        cx_errors = [prop._gates.get('cx').get(cx_connection).get('gate_error')[0] for cx_connection in _cx_key_list]

        # 2. Using these information, calculate cost
        # etc. e*depth

        cost = [x * y for (x, y) in zip(qc_depth, qc_size)]
        """
        cost計算
        """

        # 3. updating cost
        # cost = sum([...])
        return cost

    def cost(self):
        cost = self._calculate_cost()
        return cost


if __name__ == "__main__":
    # multicircuit converter
    qcs = [QuantumCircuit(3), QuantumCircuit(4)]
    # List[QuantumCircuit]
    costfunction = DepthBaseCost(qcs)
    cost = costfunction.cost()
    print(cost)
