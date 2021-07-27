# This program is based on https://github.com/Qiskit/qiskit-terra/blob/main/qiskit/transpiler/passes/layout/noise_adaptive_layout.py
# Edited by Yasuhiro Ohkura
# github: https://github.com/rum-yasuhiro/palloq
#

import math
import networkx as nx
from qiskit.transpiler.layout import Layout
from qiskit.transpiler.basepasses import AnalysisPass
from qiskit.transpiler.exceptions import TranspilerError
from qiskit.providers.models import BackendProperties


class DistanceMultiLayout(AnalysisPass):
    def __init__(
        self,
        backend_prop: BackendProperties,
        coupling_map,
        output_name: str = None,
    ):

        super().__init__()
        self.backend_prop = backend_prop
        self.prog_graphs = []
        self.output_name = output_name
        self.consumed_hw_edges = []
        self.swap_graph = nx.DiGraph()
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
                self.swap_graph.add_edge(
                    ginfo.qubits[1], ginfo.qubits[0], weight=swap_cost
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
        self._update_edge_prop()

    def _update_edge_prop(self):
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
            self.qarg_to_id[q.register.name + str(q.index)] = idx
            idx += 1
        prog_graph = nx.Graph()
        for gate in dag.two_qubit_ops():
            qid1 = self._qarg_to_id(gate.qargs[0])
            qid2 = self._qarg_to_id(gate.qargs[1])
            min_q = min(qid1, qid2)
            max_q = max(qid1, qid2)
            edge_weight = 1
            if prog_graph.has_edge(min_q, max_q):
                edge_weight = prog_graph[min_q][max_q]["weight"] + 1
            prog_graph.add_edge(min_q, max_q, weight=edge_weight)

        prog_subgraphs = list(
            prog_graph.subgraph(c) for c in nx.connected_components(prog_graph)
        )
        self.prog_graphs = self._sort_graphs(prog_subgraphs)
        return idx

    def _sort_graphs(self, graph_list):
        """
        w: total weight of edges in graph

        """
        graph_volumes = {}
        order = []
        for i, graph in enumerate(graph_list):
            graph_volumes[i] = graph.size(weight="weight") * graph.number_of_nodes()
        return [
            graph_list[id_kq[0]]
            for id_kq in sorted(graph_volumes.items(), key=lambda x: x[1], reverse=True)
        ]

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

    def run(self, dag):
        """Run the DistanceMultiLayout pass on `list of dag`."""
        self._initialize_backend_prop()
        num_qubits = self._create_program_graphs(dag=dag)

        if num_qubits > len(self.available_hw_qubits):
            raise TranspilerError("Number of qubits greater than device.")

        for hwid, q in enumerate(dag.qubits):
            self.qarg_to_id[q.register.name + str(q.index)] = hwid

        for prog_graph in self.prog_graphs:
            # sort by weight, then edge name for determinism (since networkx on python 3.5 returns
            # different order of edges)
            self.pending_program_edges = sorted(
                prog_graph.edges(data=True),
                key=lambda x: [x[2]["weight"], -x[0], -x[1]],
                reverse=True,
            )

            while self.pending_program_edges:

                edge = self._select_next_edge()
                q1_mapped = edge[0] in self.prog2hw
                q2_mapped = edge[1] in self.prog2hw
                if (not q1_mapped) and (not q2_mapped):
                    best_hw_edge = self._select_best_remaining_cx()
                    if best_hw_edge is None:
                        raise TranspilerError(
                            "CNOT({}, {}) could not be placed "
                            "in selected device.".format(edge[0], edge[1])
                        )
                    self.prog2hw[edge[0]] = best_hw_edge[0]
                    self.prog2hw[edge[1]] = best_hw_edge[1]
                    self.available_hw_qubits.remove(best_hw_edge[0])
                    self.available_hw_qubits.remove(best_hw_edge[1])

                elif not q1_mapped:
                    best_hw_qubit = self._select_best_remaining_qubit(
                        edge[0], prog_graph
                    )
                    if best_hw_qubit is None:
                        raise TranspilerError(
                            "CNOT({}, {}) could not be placed in selected device. "
                            "No qubit near qr[{}] available".format(
                                edge[0], edge[1], edge[0]
                            )
                        )
                    self.prog2hw[edge[0]] = best_hw_qubit
                    self.available_hw_qubits.remove(best_hw_qubit)
                else:
                    best_hw_qubit = self._select_best_remaining_qubit(
                        edge[1], prog_graph
                    )
                    if best_hw_qubit is None:
                        raise TranspilerError(
                            "CNOT({}, {}) could not be placed in selected device. "
                            "No qubit near qr[{}] available".format(
                                edge[0], edge[1], edge[1]
                            )
                        )
                    self.prog2hw[edge[1]] = best_hw_qubit
                    self.available_hw_qubits.remove(best_hw_qubit)
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

        layout_dict = {}
        for q in dag.qubits:
            pid = self._qarg_to_id(q)
            hwid = self.prog2hw[pid]
            # layout[q] = hwid
            layout_dict[q] = hwid
            print("prog: {} , hw: {}".format(q, hwid))
        self.property_set["layout"] = Layout(input_dict=layout_dict)
