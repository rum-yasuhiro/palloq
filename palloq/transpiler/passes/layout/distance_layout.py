# This program is based on https://github.com/Qiskit/qiskit-terra/blob/main/qiskit/transpiler/passes/layout/noise_adaptive_layout.py
# Edited by Yasuhiro Ohkura
# github: https://github.com/rum-yasuhiro/palloq
#

import math
from os import name
from copy import copy
from typing import OrderedDict

import networkx as nx
from qiskit.circuit.classicalregister import ClassicalRegister
from qiskit.circuit.quantumcircuit import QuantumCircuit
from qiskit.circuit.quantumregister import QuantumRegister
from qiskit.dagcircuit.dagcircuit import DAGCircuit

from qiskit.transpiler.layout import Layout
from qiskit.transpiler.basepasses import AnalysisPass
from qiskit.transpiler.exceptions import LayoutError, TranspilerError
from qiskit.providers.models import BackendProperties


class DistanceMultiLayout(AnalysisPass):
    def __init__(
        self,
        backend_prop: BackendProperties,
        n_hop=0,
        output_name: str = None,
    ):

        super().__init__()
        self.backend_prop = backend_prop

        self.hw_still_avaible = True
        self.floaded_dag = None
        self.largest_hw_qubits = len(backend_prop.qubits)

        self.n_hop = n_hop
        self.output_name = output_name
        self.consumed_hw_edges = []
        self.swap_graph = nx.Graph()
        self.cx_reliability = {}
        self.readout_reliability = {}
        self.available_hw_qubits = []
        self.gate_list = []
        self.swap_paths = {}
        self.swap_reliabs = {}
        self.gate_reliability = {}
        self.qarg_to_id = {}
        self.pending_program_edges = []
        self.prog2hw = {}
        self.layout_dict = OrderedDict()
        self.used_hwq = 0
        self.reg_name_list = []

        # initialize backend info
        self._initialize_backend_prop()

    def _initialize_backend_prop(self):
        """Extract readout and CNOT errors and compute swap costs."""
        backend_prop = self.backend_prop
        for ginfo in backend_prop.gates:
            if ginfo.gate == "cx":
                for item in ginfo.parameters:
                    if item.name == "gate_error":
                        g_reliab = 1.0 - item.value
                        break
                    g_reliab = 1.0
                swap_reliab = pow(g_reliab, 3)
                # convert swap reliability to edge weight
                # for the Floyd-Warshall shortest weighted paths algorithm
                swap_cost = -math.log(swap_reliab) if swap_reliab != 0 else math.inf
                self.swap_graph.add_edge(
                    ginfo.qubits[0], ginfo.qubits[1], weight=swap_cost
                )
                self.cx_reliability[(ginfo.qubits[0], ginfo.qubits[1])] = g_reliab
                self.gate_list.append((ginfo.qubits[0], ginfo.qubits[1]))

        idx = 0
        for q in backend_prop.qubits:
            for nduv in q:
                if nduv.name == "readout_error":
                    self.readout_reliability[idx] = 1.0 - nduv.value
                    self.available_hw_qubits.append(idx)
            idx += 1

        for edge in self.cx_reliability:
            self.gate_reliability[edge] = (
                self.cx_reliability[edge]
                * self.readout_reliability[edge[0]]
                * self.readout_reliability[edge[1]]
            )
        (
            self.swap_paths,
            swap_reliabs_temp,
        ) = nx.algorithms.shortest_paths.dense.floyd_warshall_predecessor_and_distance(
            self.swap_graph, weight="weight"
        )
        for i in swap_reliabs_temp:
            self.swap_reliabs[i] = {}
            for j in swap_reliabs_temp[i]:
                if (i, j) in self.cx_reliability:
                    self.swap_reliabs[i][j] = self.cx_reliability[(i, j)]
                elif (j, i) in self.cx_reliability:
                    self.swap_reliabs[i][j] = self.cx_reliability[(j, i)]
                else:
                    best_reliab = 0.0
                    for n in self.swap_graph.neighbors(j):
                        if (n, j) in self.cx_reliability:
                            reliab = (
                                math.exp(-swap_reliabs_temp[i][n])
                                * self.cx_reliability[(n, j)]
                            )
                        else:
                            reliab = (
                                math.exp(-swap_reliabs_temp[i][n])
                                * self.cx_reliability[(j, n)]
                            )
                        if reliab > best_reliab:
                            best_reliab = reliab
                    self.swap_reliabs[i][j] = best_reliab

    def _create_program_graphs(self, dag):
        """Program graph has virtual qubits as nodes.

        Two nodes have an edge if the corresponding virtual qubits
        participate in a 2-qubit gate. The edge is weighted by the
        number of CNOTs between the pair.
        """
        idx = 0
        for q in dag.qubits:
            self.qarg_to_id[q.register.name + str(q.index)] = idx + self.used_hwq
            idx += 1

        # every time next_graph is assgined, prog_graph is initialized
        self.prog_graph = nx.Graph()
        for gate in dag.two_qubit_ops():
            qid1 = self._qarg_to_id(gate.qargs[0])
            qid2 = self._qarg_to_id(gate.qargs[1])
            min_q = min(qid1, qid2)
            max_q = max(qid1, qid2)
            edge_weight = 1
            if self.prog_graph.has_edge(min_q, max_q):
                edge_weight = self.prog_graph[min_q][max_q]["weight"] + 1
            self.prog_graph.add_edge(min_q, max_q, weight=edge_weight)
        return idx

    def _adjacent_heavier_node(self, edge, graph):
        q0 = min(edge[0], edge[1])
        q1 = max(edge[0], edge[1])

        weight_q0 = 0
        for adj0 in nx.all_neighbors(graph, q0):
            if adj0 != q1:
                weight_q0 += graph[q0][adj0]["weight"]

        weight_q1 = 0
        for adj1 in nx.all_neighbors(graph, q1):
            if adj1 != q0:
                weight_q1 += graph[q1][adj1]["weight"]

        if weight_q0 >= weight_q1:
            return q0
        return q1

    def _qarg_to_id(self, qubit):
        """Convert qarg with name and value to an integer id."""
        return self.qarg_to_id[qubit.register.name + str(qubit.index)]

    def _select_next_edge(self):
        """Select the next edge.

        If there is an edge with one endpoint mapped, return it.
        Else return in the first edge
        """
        for edge in self.pending_program_edges:
            q1_mapped = edge[0] in self.prog2hw
            q2_mapped = edge[1] in self.prog2hw
            assert not (q1_mapped and q2_mapped)
            if q1_mapped or q2_mapped:
                return edge
        return self.pending_program_edges[0]

    def _select_best_remaining_cx(self):
        """Select best remaining CNOT in the hardware for the next program edge."""
        """TODO
        edgeの隣接をみてlook ahead して選ぶ
        """

        candidates = []
        for gate in self.gate_list:
            chk1 = gate[0] in self.available_hw_qubits
            chk2 = gate[1] in self.available_hw_qubits
            if chk1 and chk2:
                candidates.append(gate)
        best_reliab = 0
        best_item = None
        for item in candidates:
            if self.gate_reliability[item] > best_reliab:
                best_reliab = self.gate_reliability[item]
                best_item = item
        return best_item

    def _select_best_remaining_qubit(self, prog_qubit, prog_graph):
        """Select the best remaining hardware qubit for the next program qubit."""
        reliab_store = {}
        for hw_qubit in self.available_hw_qubits:
            reliab = 1
            for n in prog_graph.neighbors(prog_qubit):
                if n in self.prog2hw:
                    reliab *= self.swap_reliabs[self.prog2hw[n]][hw_qubit]
            reliab *= self.readout_reliability[hw_qubit]
            reliab_store[hw_qubit] = reliab
        max_reliab = 0
        best_hw_qubit = None
        for hw_qubit in reliab_store:
            if reliab_store[hw_qubit] > max_reliab:
                max_reliab = reliab_store[hw_qubit]
                best_hw_qubit = hw_qubit
        return best_hw_qubit

    def _combine_dag(
        self,
        init_dag: DAGCircuit,
        next_dag: DAGCircuit,
    ) -> DAGCircuit:
        # if dag with no bits return initial dag
        next_numq = next_dag.num_qubits()
        next_numc = next_dag.num_clbits()
        if next_numq == 0 and next_numc == 0:
            return init_dag

        # prepare new dag
        combined_dag = DAGCircuit()

        # add empty qregs to combined_dag based on init_dag and next_dag's info
        init_qregs = init_dag.qregs
        for i, _qreg in enumerate(init_qregs.values()):
            _qr = QuantumRegister(
                size=_qreg.size,
                name=None,
            )
            combined_dag.add_qreg(_qr)
        if next_numq > 0:
            next_qregs = next_dag.qregs
            for i, _qreg in enumerate(next_qregs.values()):
                _qr = QuantumRegister(
                    size=_qreg.size,
                    name=None,
                )
                combined_dag.add_qreg(_qr)

        # add empty cregs to combined_dag based on init_dag and next_dag's info
        init_cregs = init_dag.cregs
        for i, _creg in enumerate(init_cregs.values()):
            _cr = ClassicalRegister(
                size=_creg.size,
                name=None,
            )
            combined_dag.add_creg(_cr)
        if next_numc > 0:
            next_cregs = next_dag.cregs
            for i, _creg in enumerate(next_cregs.values()):
                _cr = ClassicalRegister(
                    size=_creg.size,
                    name=None,
                )
                combined_dag.add_creg(_cr)

        # combine dags
        qubits = None
        clbits = None
        init_numq = init_dag.num_qubits()
        init_numc = init_dag.num_clbits()

        if init_numq > 0:
            qubits = combined_dag.qubits[0:init_numq]
        if init_numc > 0:
            clbits = combined_dag.clbits[0:init_numc]
        combined_dag.compose(init_dag, qubits=qubits, clbits=clbits)

        # update layout values (Qubit)
        for _qubit_init, _qubit_combined in zip(init_dag.qubits, qubits):
            if _qubit_init in self.layout_dict:
                self.layout_dict[_qubit_combined] = self.layout_dict.pop(_qubit_init)

        # update layout values (Clbit)
        for _clbit_init, _clbit_combined in zip(init_dag.clbits, clbits):
            if _clbit_init in self.layout_dict:
                self.layout_dict[_clbit_combined] = self.layout_dict.pop(_clbit_init)
        
        if next_numq > 0:
            qubits = combined_dag.qubits[init_numq : init_numq + next_numq]
        if next_numc > 0:
            clbits = combined_dag.clbits[init_numc : init_numc + next_numc]
        combined_dag.compose(next_dag, qubits=qubits, clbits=clbits)

        # update layout values (Qubit)
        for _qubit_next, _qubit_combined in zip(next_dag.qubits, qubits):
            if _qubit_next in self.layout_dict:
                self.layout_dict[_qubit_combined] = self.layout_dict.pop(_qubit_next)

        # update layout values (Clbit)
        for _clbit_next, _clbit_combined in zip(next_dag.clbits, clbits):
            if _clbit_next in self.layout_dict:
                self.layout_dict[_clbit_combined] = self.layout_dict.pop(_clbit_next)


        return combined_dag

    def _largest_connected_hw_qubits(self):
        for hw_qubit_set in nx.connected_components(self.swap_graph):
            if len(hw_qubit_set) >= self.largest_hw_qubits:
                self.largest_hw_qubits = len(hw_qubit_set)
        

    def _disable_qubits(self, hw_qubit, n=0):
        """disable qubits adjacent to used qubit in n hop range"""
        if n == 1:
            adj_list = [
                adj
                for adj in nx.all_neighbors(self.swap_graph, hw_qubit)
                if adj in self.available_hw_qubits
            ]
            for adj in adj_list:
                self.swap_graph.remove_node(adj)
                self.available_hw_qubits.remove(adj)

        self.swap_graph.remove_node(hw_qubit)

    def run(self, next_dag: DAGCircuit, init_dag=None):
        """Run the DistanceMultiLayout pass on `list of dag`."""

        # Compare next dag.qubits to left num qubits status and check the status by using self.hw_still_avaible.
        # If so, hw_still_avaible=False and return init_dag
        # find next_dag's hw_qubits
        # Combine init_dag and next_dag
        # Return init_dag

        # initialize dag as program graphs
        num_qubits = self._create_program_graphs(dag=next_dag)

        # check the hardware availability
        # if num_qubits > largest_connected_hw_qubits:
        #     self.hw_still_avaible = False
        #     self.floaded_dag = next_dag
        #     return init_dag

        # sort program sub-graphs by weight
        self.pending_program_edges = sorted(
            self.prog_graph.edges(data=True),
            key=lambda x: x[2].get("weight", 1),
            reverse=True,
        )
        while self.pending_program_edges:
            edge = self._select_next_edge()
            q1_mapped = edge[0] in self.prog2hw
            q2_mapped = edge[1] in self.prog2hw

            if (not q1_mapped) and (not q2_mapped):
                best_hw_edge = self._select_best_remaining_cx()

                # deal exception
                if best_hw_edge is None:
                    # hw has no capacity to add next_dag
                    if init_dag is not None:
                        self.hw_still_avaible = False
                        self.floaded_dag = next_dag
                        return init_dag
                    raise TranspilerError(
                        "CNOT({}, {}) could not be placed "
                        "in selected device.".format(edge[0], edge[1])
                    )
                # allocate and update hw qubits info
                better_adj_hw_qubit = self._adjacent_heavier_node(
                    best_hw_edge, self.swap_graph
                )
                less_reliab_adj_hw_qubit = (
                    best_hw_edge[1]
                    if best_hw_edge[0] == better_adj_hw_qubit
                    else best_hw_edge[0]
                )

                heavier_prog_qubit = self._adjacent_heavier_node(edge, self.prog_graph)
                ligher_prog_qubit = (
                    edge[1] if edge[0] == heavier_prog_qubit else edge[0]
                )

                self.prog2hw[heavier_prog_qubit] = better_adj_hw_qubit
                self.prog2hw[ligher_prog_qubit] = less_reliab_adj_hw_qubit
                self.available_hw_qubits.remove(better_adj_hw_qubit)
                self.available_hw_qubits.remove(less_reliab_adj_hw_qubit)

            elif not q1_mapped:
                best_hw_qubit = self._select_best_remaining_qubit(
                    edge[0], self.prog_graph
                )

                # deal exception
                if best_hw_qubit is None:
                    # hw has no capacity to add next_dag
                    if init_dag is not None:
                        self.hw_still_avaible = False
                        self.floaded_dag = next_dag
                        return init_dag
                    raise TranspilerError(
                        "CNOT({}, {}) could not be placed in selected device. "
                        "No qubit near qr[{}] available".format(
                            edge[0], edge[1], edge[0]
                        )
                    )

                # allocate and update hw qubits info
                self.prog2hw[edge[0]] = best_hw_qubit
                self.available_hw_qubits.remove(best_hw_qubit)

            else:
                best_hw_qubit = self._select_best_remaining_qubit(
                    edge[1], self.prog_graph
                )

                # deal exception
                if best_hw_qubit is None:
                    # hw has no capacity to add next_dag
                    if init_dag is not None:
                        self.hw_still_avaible = False
                        self.floaded_dag = next_dag
                        return init_dag
                    raise TranspilerError(
                        "CNOT({}, {}) could not be placed in selected device. "
                        "No qubit near qr[{}] available".format(
                            edge[0], edge[1], edge[1]
                        )
                    )

                # allocate and update hw qubits info
                self.prog2hw[edge[1]] = best_hw_qubit
                self.available_hw_qubits.remove(best_hw_qubit)

            # update program graph edges
            new_edges = [
                x
                for x in self.pending_program_edges
                if not (x[0] in self.prog2hw and x[1] in self.prog2hw)
            ]

            self.pending_program_edges = new_edges

        for qid in self.qarg_to_id.values():
            if qid not in self.prog2hw:
                self.prog2hw[qid] = self.available_hw_qubits[0]
                self.available_hw_qubits.remove(self.prog2hw[qid])

        for q in next_dag.qubits:
            pid = self._qarg_to_id(q)
            hwid = self.prog2hw[pid]
            self.layout_dict[q] = hwid

            # update number of used hw qubits
            self.used_hwq += 1

            # disable n hop qubits
            self._disable_qubits(hwid, n=self.n_hop)

        if init_dag:
            next_dag = self._combine_dag(init_dag, next_dag)

        """FIXME
        入力量子回路の順番によって、なぜかlayoutにはない量子回路が追加されるバグが生じることがある
        バグが生じる際、
        len(self.layout_dict.keys())
        が、更新されなくなる部分が出てくることまで確認できている↓
        
        else:
            print("Initialized!\n")
        print(self.property_set["layout"])
        print(self.layout_dict)
        print(len(self.layout_dict.keys()))
        """
        
        self.property_set["layout"] = Layout(input_dict=self.layout_dict)

        self._largest_connected_hw_qubits()
        return next_dag
