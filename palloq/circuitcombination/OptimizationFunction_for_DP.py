# This code is written by Ryosuke Satoh

from typing import List, Iterable
from qiskit import QuantumCircuit
from qiskit.compiler import transpile
import abc
import numpy as np
import collections

from palloq.utils import esp


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


class CrosstalkBaseCost(CostFunction):
    def __init__(
        self,
        total_qubits: int,
        device_errors: List[float] = None,
        device_topology: List = None,
    ):
        if not isinstance(total_qubits, int):
            raise TypeError("total_qubits must be int")
        self.total_qubits = total_qubits
        self.device_errors = device_errors
        self.device_topology = device_topology

    def _calculate_cost(self) -> float:
        cost = []

        for qc in self.circuit_pairs:
            each_cost = qc.num_qubits / self.total_qubits
            cost.append(each_cost)

        """
        cost = 0

            cost = qc.num_qubits / self.total_qubits
        """

        return cost

    def cost(self, circuit_pairs):
        if isinstance(circuit_pairs, (Iterable)):
            if all(map(lambda x: isinstance(x, QuantumCircuit), circuit_pairs)):
                self.circuit_pairs = circuit_pairs
            else:
                raise ValueError(
                    "Argument circuit_pairs must \
be the iterable of Quantum Circuit"
                )
        else:
            raise TypeError(
                "Argument circuit_pairs must be the iterable \
of Quantum Circuit not {type(circuit_pairs)}"
            )
        cost = self._calculate_cost()
        return cost


class DurationTimeCost(CostFunction):
    def __init__(
        self,
        total_qubits: int,
        device_errors: List[float] = None,
        device_topology: List = None,
    ):
        if not isinstance(total_qubits, int):
            raise TypeError("total_qubits must be int")
        self.total_qubits = total_qubits
        self.device_errors = device_errors
        self.device_topology = device_topology

    def _calculate_cost(self) -> float:

        cost = []
        each_cost = 0
        qc_ops = collections.OrderedDict()
        cx_duration_time = 2000
        rz_duration_time = 200
        sx_duration_time = 200
        x_duration_time = 200
        id_duration_time = 200
        cx_list = []
        rz_list = []
        sx_list = []
        x_list = []
        id_list = []

        for qc in self.circuit_pairs:
            uqc = transpile(qc, basis_gates=["rz", "cx", "sx", "x", "id"])
            qc_ops = uqc.count_ops()
            cx_num = qc_ops.get("cx", 0)
            rz_num = qc_ops.get("rz", 0)
            sx_num = qc_ops.get("sx", 0)
            x_num = qc_ops.get("x", 0)
            id_num = qc_ops.get("id", 0)

            cx_list.append(cx_num)
            rz_list.append(rz_num)
            sx_list.append(sx_num)
            x_list.append(x_num)
            id_list.append(id_num)

            total_cx = sum(cx_list)
            total_rz = sum(rz_list)
            total_sx = sum(sx_list)
            total_x = sum(x_list)
            total_id = sum(id_list)

            each_cost = (
                total_cx * cx_duration_time
                + total_rz * rz_duration_time
                + total_sx * sx_duration_time
                + total_x * x_duration_time
                + total_id * id_duration_time
            )
            cost.append(each_cost)

            cx_list = []
            rz_list = []
            sx_list = []
            x_list = []
            id_list = []

        return cost

        """
            uqc = transpile(qc, basis_gates = ['rz', 'cx', 'sx', 'x', 'id'])
            qc_ops = uqc.count_ops()
            cx_num = qc_ops.get('cx', 0)
            rz_num = qc_ops.get('rz', 0)
            sx_num = qc_ops.get('sx', 0)
            x_num = qc_ops.get('x', 0)
            id_num = qc_ops.get('id', 0)

            cost = cx_num * cx_duration_time + rz_num * rz_duration_time + sx_num * sx_duration_time + x_num * x_duration_time + id_num * id_duration_time
        
        """

    def cost(self, circuit_pairs):
        if isinstance(circuit_pairs, (Iterable)):
            if all(map(lambda x: isinstance(x, QuantumCircuit), circuit_pairs)):
                self.circuit_pairs = circuit_pairs
            else:
                raise ValueError(
                    "Argument circuit_pairs must \
be the iterable of Quantum Circuit"
                )
        else:
            raise TypeError(
                "Argument circuit_pairs must be the iterable \
of Quantum Circuit not {type(circuit_pairs)}"
            )
        cost = self._calculate_cost()
        return cost


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

    def __init__(
        self,
        total_qubits: int,
        device_errors: List[float] = None,
        device_topology: List = None,
    ):
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
        cost = []
        depths = []
        num_qubits_list = []
        # # 1. take information
        # # self.circuit_pairs
        # # self.device_errors
        # # self.device_topology
        # # depths = np.array([qc.depth() for qc in self.circuit_pairs]) etc.
        for qc in self.circuit_pairs:
            depth = qc.depth()
            depths.append(depth)
            num_qubits = qc.num_qubits
            num_qubits_list.append(num_qubits)

        # # 2. Using these information, calculate cost
        # # etc. e*depth

        cost = np.array(depths) * np.array(num_qubits_list)
        """
        depth = qc.depth()
        num_qubits = qc.num_qubits

        cost = depth * num_qubits
        """

        """
        cost計算
        """

        # 3. updating cost
        # cost = sum([...])
        return cost

    def cost(self, circuit_pairs):
        if isinstance(circuit_pairs, (Iterable)):
            if all(map(lambda x: isinstance(x, QuantumCircuit), circuit_pairs)):
                self.circuit_pairs = circuit_pairs
            else:
                raise ValueError(
                    "Argument circuit_pairs must \
be the iterable of Quantum Circuit"
                )
        else:
            raise TypeError(
                "Argument circuit_pairs must be the iterable \
of Quantum Circuit not {type(circuit_pairs)}"
            )
        cost = self._calculate_cost()
        return cost


if __name__ == "__main__":
    # multicircuit converter
    circuit_pairs = []
    """
    for i in range(10):
        qc = QuantumCircuit(3)
        for j in range(i):
            qc.x(i % 3)
            qc.h(0)
            qc.cx(0,1)
        circuit_pairs.append(qc)
    """

    qc = QuantumCircuit(3)
    qc.cx(0, 1)
    qc.h(1)
    qc.barrier()
    qc.measure_all()
    qc2 = QuantumCircuit(5)
    qc.cx(0, 1)
    qc.h(1)
    circuit_pairs.append(qc)
    circuit_pairs.append(qc2)
    # List[QuantumCircuit]
    costfunction = DepthBaseCost(10)
    costfunction2 = DurationTimeCost(10)
    costfunction3 = CrosstalkBaseCost(10)
    cost = costfunction.cost(circuit_pairs)
    cost2 = costfunction2.cost(circuit_pairs)
    cost3 = costfunction3.cost(circuit_pairs)
    print(cost, cost2, cost3)
