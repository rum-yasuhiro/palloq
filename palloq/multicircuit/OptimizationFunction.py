from fractions import Fraction
from scipy.optimize import fmin
from qiskit import QuantumCircuit
import math
import numpy as np

Ei = np.array([]) #list of error rates of specific block
Emn = 1 #one link error rate for one alogrithm
gamma = 1 #constant
occ = Fraction(qc.num_qubits, #number of qubits in quantum computer ) #occupation rate

opt = Fraction(gamma,occ) * sum np.prod(Ei) * Emn

print(opt)