# 2021/8/
# qiskit version: 0.27.0
#

"""Multi Circuits transpile function"""
import logging
import warnings
from time import time
from typing import List, Union, Dict, Callable, Any, Optional, Tuple

from qiskit import user_config
from qiskit.circuit.quantumcircuit import (
    QuantumCircuit,
    QuantumRegister,
    ClassicalRegister,
)
from qiskit.circuit.quantumregister import Qubit
from qiskit.transpiler import CouplingMap
from qiskit.converters import (
    isinstanceint,
    isinstancelist,
    dag_to_circuit,
    circuit_to_dag,
)
from qiskit.dagcircuit import DAGCircuit
from qiskit.providers import BaseBackend
from qiskit.providers.backend import Backend
from qiskit.providers.models import BackendProperties
from qiskit.compiler import transpile

from palloq.transpiler.passes.layout.distance_layout import DistanceMultiLayout

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def dynamic_multiqc_compose(
    queued_qc: List[QuantumCircuit],
    backend: Optional[Union[Backend, BaseBackend]] = None,
    basis_gates: Optional[List[str]] = None,
    coupling_map: Optional[Union[CouplingMap, List[List[int]]]] = None,
    backend_properties: Optional[BackendProperties] = None,
    num_hw_dist=0,
    num_idle_qubits=0,
    output_name: Optional[Union[str, List[str]]] = None,
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
    coupling_map = _coupling_map(coupling_map, backend)

    # decompose all queued qc by basis_gate
    if basis_gates:
        pass
    elif backend.configuration().basis_gates:
        basis_gates = backend.configuration().basis_gates
    else:
        basis_gates = ["id", "rz", "sx", "x", "cx", "reset"]
    queued_qc = [transpile(_qc, basis_gates=basis_gates) for _qc in queued_qc]

    # repeat untill all queued qcs are assgined
    composed_circuits = []
    while len(queued_qc) > 0:
        comp_qc, layout, queued_qc = _sequential_layout(
            queued_qc,
            len(backend_properties.qubits),
            backend_properties,
            coupling_map,
            num_hw_dist,
        )
        composed_circuits.append((comp_qc, layout))

    # apply qiskit pass managers except for layout pass
    """TODO
    transpiled_multi_circuits = list(map(pass_manager.run, multi_circuits))
    if len(transpiled_multi_circuits) == 1:
        return transpiled_multi_circuits[0]
    return transpiled_multi_circuits
    """


def _sequential_layout(
    queued_circuits,
    num_hw_qubits,
    backend_properties,
    coupling_map,
    num_hw_dist,
) -> Tuple[QuantumCircuit, List[QuantumCircuit]]:

    allocated_dag = None
    dmlayout = DistanceMultiLayout(
        backend_properties,
        n_hop=num_hw_dist,
    )

    while dmlayout.hw_still_avaible:
        if not queued_circuits:
            break
        qc = _select_next_qc(queued_circuits)
        dag = circuit_to_dag(qc)
        allocated_dag = dmlayout.run(next_dag=dag, init_dag=allocated_dag)

    if dmlayout.floaded_dag:
        floaded_qc = dag_to_circuit(dmlayout.floaded_dag)
        queued_circuits.append(floaded_qc)

    composed_circuit = dag_to_circuit(allocated_dag)
    layout = dmlayout.property_set["layout"]

    return composed_circuit, layout, queued_circuits


def _select_next_qc(queue: List[QuantumCircuit]) -> QuantumCircuit:
    """FIXME"""
    # 何かしらの最適化処理を追記する
    next_qc = queue.pop(0)
    return next_qc


def _backend_properties(backend_properties, backend):
    if backend_properties is None:
        if backend:
            backend_properties = backend.properties()

    return backend_properties


def _create_faulty_qubits_map(backend):
    """If the backend has faulty qubits, those should be excluded. A faulty_qubit_map is a map
    from working qubit in the backend to dumnmy qubits that are consecutive and connected."""

    """TODO
    apply faulty qubits map checker on this layout sequence
    """

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
    # coupling_map = [CouplingMap(cm) if isinstance(cm, list) else cm for cm in coupling_map]
    return coupling_map
