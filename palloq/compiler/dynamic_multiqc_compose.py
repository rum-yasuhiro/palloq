# 2021 / 08 / 30
# qiskit version: 0.29.0
# This code is based on https://qiskit.org/documentation/stubs/qiskit.compiler.transpile.html?highlight=transpiler
# Written by Yasuhiro Ohkura

# import python tools
import logging
from time import time
from typing import List, Union, Dict, Callable, Any, Optional, Tuple
from networkx.algorithms.components.connected import connected_components

# import qiskit tools
from qiskit.circuit.quantumcircuit import (
    QuantumCircuit,
    QuantumRegister,
    ClassicalRegister,
)
from qiskit.transpiler import CouplingMap
from qiskit.converters import (
    isinstancelist,
    dag_to_circuit,
    circuit_to_dag,
)
from qiskit.providers import BaseBackend
from qiskit.providers.backend import Backend
from qiskit.providers.models import BackendProperties
from qiskit.compiler import transpile

# import palloq tools
from palloq.transpiler.passes.layout.buffered_layout import BufferedMultiLayout

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def dynamic_multiqc_compose(
    queued_qc: List[QuantumCircuit],
    backend: Optional[Union[Backend, BaseBackend]] = None,
    basis_gates: Optional[List[str]] = None,
    backend_properties: Optional[BackendProperties] = None,
    coupling_map=None,
    routing_method=None,
    scheduling_method=None,
    num_hw_dist=0,
    num_idle_qubits=0,
    output_name: Optional[Union[str, List[str]]] = None,
    return_num_usage=False,
) -> List[Tuple[QuantumCircuit, dict]]:
    """Mapping several circuits to single circuit based on calibration for the backend

    Args:
        circuits: List of quantum circuits you want to execute concurrently.
                  our layout pass selects the combination of circuits and compose those as
                  single circuit.
        backend:
        backend_properties:
        output_name: the name of output circuit. str or List[str]

    Returns:
        list of tuple of composed QuantumCircuit and its layout
    """

    # translate all of QCs to basis gates, sort list of QuantumCircuit by number of cx gates
    # loop list of QCs find combination of concurrent execution and its layout until all QCs are allocated

    # check the type of input argument
    if not isinstancelist(queued_qc):
        raise TypeError(
            "Expected input type of 'circuits' argument was list of QuantumCircuit object."
        )
    # get backend information
    backend_properties = _backend_properties(backend_properties, backend)
    coupling_map = _coupling_map(coupling_map=coupling_map, backend=backend)

    # decompose all queued qc by basis_gate
    if basis_gates:
        pass
    elif backend:
        basis_gates = backend.configuration().basis_gates
    else:
        basis_gates = ["id", "rz", "sx", "x", "cx", "reset"]
    queued_qc = [transpile(_qc, basis_gates=basis_gates) for _qc in queued_qc]

    # alter the register name identically
    queued_qc = _alter_reg_names(queued_qc)

    # repeat until all queued qcs are assigned
    composed_circuits = []
    name_list_list = []
    while len(queued_qc) > 0:
        comp_qc, layout, name_list, queued_qc = _sequential_layout(
            queued_qc,
            len(backend_properties.qubits),
            backend_properties,
            num_hw_dist,
        )
        composed_circuits.append((comp_qc, layout))
        name_list_list.append(name_list)

    # apply qiskit pass managers except for layout pass
    transpiled_circuit = []
    num_usage = []
    for comp_qc, layout in composed_circuits:
        print("Num Qubits in QC: ", comp_qc.num_qubits)
        print("Layout: ", layout)
        num_usage.append(comp_qc.num_qubits)
        _transpied = transpile(
            circuits=comp_qc,
            backend=backend,
            basis_gates=basis_gates,
            coupling_map=coupling_map,
            backend_properties=backend_properties,
            initial_layout=layout,
            routing_method=routing_method,
            scheduling_method=scheduling_method,
        )
        transpiled_circuit.append(_transpied)

    if return_num_usage:
        return transpiled_circuit, num_usage, name_list_list
    return transpiled_circuit


def _sequential_layout(
    queued_circuits,
    num_hw_qubits,
    backend_properties,
    num_hw_dist,
) -> Tuple[QuantumCircuit, List[QuantumCircuit]]:

    init_dag = None
    dmlayout = BufferedMultiLayout(
        backend_properties,
        n_hop=num_hw_dist,
    )

    num_cx_before = 0
    qc_names = []

    while queued_circuits:
        if not dmlayout.hw_still_avaible:
            break

        qc, num_cx = _select_next_qc(queued_circuits)

        # check difference of number of CX gate to previous mapped QC
        if num_cx > num_cx_before + 10:
            break

        dag = circuit_to_dag(qc)
        allocated_dag = dmlayout.run(next_dag=dag, init_dag=init_dag)

        # update number of CX pointer
        num_cx_before = num_cx

        # save qc name
        if dmlayout.hw_still_avaible:
            qc_names.append(qc.name)

        init_dag = allocated_dag

    if dmlayout.floaded_dag:
        floaded_qc = dag_to_circuit(dmlayout.floaded_dag)
        queued_circuits.append(floaded_qc)

    composed_circuit = dag_to_circuit(allocated_dag)
    layout = dmlayout.property_set["layout"]

    return composed_circuit, layout, qc_names, queued_circuits


def _select_next_qc(queue: List[QuantumCircuit]) -> QuantumCircuit:
    queue.sort(key=lambda x: x.count_ops().get("cx", 0))
    next_qc = queue.pop(0)
    num_cx = next_qc.count_ops().get("cx", 0)
    return next_qc, num_cx


def _alter_reg_names(queue: List[QuantumCircuit]) -> List[QuantumCircuit]:

    new_queue = []
    for i, _qc in enumerate(queue):
        new_qc = QuantumCircuit(name=_qc.name)
        # add quantum register
        for k, _qreg in enumerate(_qc.qregs):
            num_qubits = _qreg.size
            qreg_name = (
                _qc.name + "_" + str(i) + "_" + str(k)
                if _qc.name
                else "q_" + str(i) + "_" + str(k)
            )
            new_qreg = QuantumRegister(size=num_qubits, name=qreg_name)
            new_qc.add_register(new_qreg)

        for k, _creg in enumerate(_qc.cregs):
            num_clbits = _creg.size
            creg_name = (
                _creg.name + "_" + str(i) + "_" + str(k)
                if _creg.name
                else "c_" + str(i) + "_" + str(k)
            )
            new_creg = ClassicalRegister(size=num_clbits, name=creg_name)
            new_qc.add_register(new_creg)

        _dag = circuit_to_dag(_qc)
        new_dag = circuit_to_dag(new_qc)

        new_dag.compose(_dag, qubits=new_dag.qubits, clbits=new_dag.clbits)

        new_queue.append(dag_to_circuit(new_dag))
    return new_queue


def _backend_properties(backend_properties, backend):
    if backend_properties is None:
        if backend:
            backend_properties = backend.properties()

    return backend_properties


def _create_faulty_qubits_map(backend):
    """If the backend has faulty qubits, those should be excluded. A faulty_qubit_map is a map
    from working qubit in the backend to dumnmy qubits that are consecutive and connected."""

    faulty_qubits_map = None
    if backend is not None:
        if backend.properties():
            faulty_qubits = backend.properties().faulty_qubits()
            faulty_edges = [
                gates.qubits for gates in backend.properties().faulty_gates()
            ]
        else:
            faulty_qubits = []
            faulty_edges = []

        if faulty_qubits or faulty_edges:
            faulty_qubits_map = {}
            configuration = backend.configuration()
            full_coupling_map = configuration.coupling_map
            functional_cm_list = [
                edge
                for edge in full_coupling_map
                if (set(edge).isdisjoint(faulty_qubits) and edge not in faulty_edges)
            ]

            connected_working_qubits = CouplingMap(
                functional_cm_list
            ).largest_connected_component()
            dummy_qubit_counter = 0
            for qubit in range(configuration.n_qubits):
                if qubit in connected_working_qubits:
                    faulty_qubits_map[qubit] = dummy_qubit_counter
                    dummy_qubit_counter += 1
                else:
                    faulty_qubits_map[qubit] = None
    return faulty_qubits_map


def _coupling_map(coupling_map, backend):
    # try getting coupling_map from user, else backend
    if coupling_map is None:
        if getattr(backend, "configuration", None):
            configuration = backend.configuration()
            if hasattr(configuration, "coupling_map") and configuration.coupling_map:
                faulty_map = _create_faulty_qubits_map(backend)
                if faulty_map:
                    coupling_map = CouplingMap()
                    for qubit1, qubit2 in configuration.coupling_map:
                        if (
                            faulty_map[qubit1] is not None
                            and faulty_map[qubit2] is not None
                        ):
                            coupling_map.add_edge(
                                faulty_map[qubit1], faulty_map[qubit2]
                            )
                else:
                    coupling_map = CouplingMap(configuration.coupling_map)
    return coupling_map
