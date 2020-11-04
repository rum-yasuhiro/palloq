from fractions import Fraction
from scipy.optimize import fmin
from qiskit import QuantumCircuit
import abc
import math
import numpy as np


# What is input?
Ei = np.array([]) #list of error rates of specific block
Emn = 1 #one link error rate for one alogrithm
gamma = 1 #constant
occ = Fraction(qc.num_qubits) #number of qubits in quantum computer ) #occupation rate

opt = Fraction(gamma,occ) * sum np.prod(Ei) * Emn

print(opt)
# What is output?


class CostFunctions(abc.ABCMeta):
    "a series of cost functions"
    def __init__(self):
        pass

    @abc.abstractmethod
    def cost(self):
        pass


class DepthCost(CostFunctions):
    def cost(self):
        return 0


if __name__ == "__main__":
    # multicircuit converter
    qcs = []
    costfunction = CostFunctions()
    cost = costfunction.cocori_function(qcs)