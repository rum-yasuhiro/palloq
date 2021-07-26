# 2020/12/3
# qiskit version: 0.23.1
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
from qiskit.providers.models.backendproperties import Gate
from qiskit.pulse import Schedule
from qiskit.tools.parallel import parallel_map
from qiskit.transpiler import Layout, CouplingMap, PropertySet, PassManager
from qiskit.transpiler.basepasses import BasePass
from qiskit.transpiler.exceptions import TranspilerError
from qiskit.transpiler.instruction_durations import (
    InstructionDurations,
    InstructionDurationsType,
)
from qiskit.transpiler.passes import ApplyLayout
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.preset_passmanagers import (
    level_0_pass_manager,
    level_1_pass_manager,
    level_2_pass_manager,
    level_3_pass_manager,
)

from qiskit.compiler import transpile
from palloq.transpiler.preset_passmanagers import multi_pass_manager


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def dynamic_multitranspile(
    circuits: List[QuantumCircuit],
    backend: Optional[Union[Backend, BaseBackend]] = None,
    basis_gates: Optional[List[str]] = None,
    coupling_map: Optional[Union[CouplingMap, List[List[int]]]] = None,
    backend_properties: Optional[BackendProperties] = None,
    layout_method: Optional[str] = "distance_multiplelayout",
    routing_method: Optional[str] = None,
    translation_method: Optional[str] = None,
    scheduling_method: Optional[str] = None,
    instruction_durations: Optional[InstructionDurationsType] = None,
    seed_transpiler: Optional[int] = None,
    pass_manager: Optional[PassManager] = None,
    num_idle_qubits=0,
    output_name: Optional[Union[str, List[str]]] = None,
):
    """Mapping several circuits to single circuit based on calibration for the backend

    Args:
        circuits: List of quantum circuits you want to execute concurrently.
                  Transpiler selects the combination of circuits and compose those as
                  single circuit.
        backend:
        backend_properties:
        output_name: the name of output circuit. str or List[str]

    Returns:
        composed multitasking circuit(s)..
    """
    # check the type of input argument
    if not isinstancelist(circuits):
        raise TypeError(
            "Expected input type of 'circuits' argument was list of QuantumCircuit object."
        )
    # get backend information
    backend_properties = _backend_properties(backend_properties, backend)
    coupling_map = _coupling_map(coupling_map, backend)

    # define pass manager.
    """FIXME
    I still expected only dist_layout pass. 
    But eventually I hope marge this to multi_transpile function. 
    """
    pass_manager_config = PassManagerConfig(
        basis_gates=basis_gates,
        coupling_map=coupling_map,
        backend_properties=backend_properties,
        initial_layout=Layout(),
        layout_method=layout_method,
        routing_method=routing_method,
        translation_method=translation_method,
        scheduling_method=scheduling_method,
        instruction_durations=instruction_durations,
        seed_transpiler=seed_transpiler,
    )
    """FIXME
    resolve output_name
    """
    if pass_manager:
        raise NotImplementedError(
            "I put the 'pass_manager' argument but still expected as 'None' that. Sorry... "
        )
    elif layout_method == "distance_multiplelayout":
        logger.info("############## dist_layout ##############")
        pass_manager = multi_pass_manager(pass_manager_config)
    else:
        raise NotImplementedError(
            "layout method for this transpiler is only expected 'distance_multiplelayout'. Others have not implemented yet. "
        )

    # repeat untill all queued qcs are assgined
    composed_circuits = []
    while len(circuits) > 0:
        comp_qc, circuits = _sequential_layout(
            circuits,
            len(backend_properties.qubits),
        )
        composed_circuits.append(comp_qc)

    # apply qiskit pass managers except for layout pass
    """FIXME
    transpiled_multi_circuits = list(map(pass_manager.run, multi_circuits))
    if len(transpiled_multi_circuits) == 1:
        return transpiled_multi_circuits[0]
    return transpiled_multi_circuits
    """


def _sequential_layout(
    queued_circuits,
    num_hw_qubits,
) -> Tuple[QuantumCircuit, List[QuantumCircuit]]:

    hw_still_avaible = True
    qc = QuantumCircuit()
    while hw_still_avaible:
        if not queued_circuits:
            break
        next_qc = _select_next_qc(queued_circuits)

    return composed_circuit, queued_circuits


def _select_next_qc(queue: List[QuantumCircuit]) -> QuantumCircuit:
    """FIXME"""
    # 何かしらの最適化処理を追記する
    next_qc = queue.pop(0)
    return next_qc


def _append_qc(
    qc,
    base_qc: QuantumCircuit = None,
) -> QuantumCircuit:

    return


def _append_dag() -> DAGCircuit:

    return combined_dag


# def _compose_multicircuits(circuits: List[QuantumCircuit]) -> QuantumCircuit:

#     composed_multicircuit = QuantumCircuit()
#     name_list = []
#     bit_counter = 0
#     dag_list = [circuit_to_dag(circuit.copy()) for circuit in circuits]
#     return dag_to_circuit(_compose_dag(dag_list))


# def _compose_dag(dag_list):
#     """Compose each dag and return new multitask dag"""

#     """FIXME 下記と同様
#     """
#     name_list = []
#     #################
#     qubit_counter = 0
#     clbit_counter = 0
#     composed_multidag = DAGCircuit()
#     for i, dag in enumerate(dag_list):
#         num_qubits = dag.num_qubits()
#         num_clbits = dag.num_clbits()
#         """FIXME
#         Problem:
#             register_name: register nameを定義すると、outputの `new_dag` に対して `dag_to_circuit()`
#             を実行した時、
#             qiskit.circuit.exceptions.CircuitError: 'register name "定義した名前" already exists'
#             が発生するため、任意のレジスター名をつけることができない

#         Code:
#             reg_name_tmp = dag.qubits[0].register.name
#             register_name = reg_name_tmp if (reg_name_tmp not in name_list) and (
#                 not reg_name_tmp == 'q') else None
#             name_list.append(register_name)
#         """
#         ############################################################
#         reg_name_tmp = dag.qubits[0].register.name
#         register_name = (
#             reg_name_tmp
#             if (reg_name_tmp not in name_list) and (not reg_name_tmp == "q")
#             else None
#         )
#         name_list.append(register_name)
#         ############################################################

#         qr = QuantumRegister(size=num_qubits, name=register_name)
#         composed_multidag.add_qreg(qr)
#         qubits = composed_multidag.qubits[qubit_counter : qubit_counter + num_qubits]

#         if num_clbits > 0:
#             cr = ClassicalRegister(size=num_clbits, name=None)
#             composed_multidag.add_creg(cr)
#             clbits = composed_multidag.clbits[
#                 clbit_counter : clbit_counter + num_clbits
#             ]

#             composed_multidag.compose(dag, qubits=qubits, clbits=clbits)
#         else:
#             composed_multidag.compose(dag, qubits=qubits)

#         qubit_counter += num_qubits
#         clbit_counter += num_clbits
#     return composed_multidag


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
    # coupling_map = [CouplingMap(cm) if isinstance(cm, list) else cm for cm in coupling_map]
    return coupling_map


if __name__ == "__main__":
    pass
