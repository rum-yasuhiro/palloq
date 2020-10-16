from typing import List, Union, Dict, Callable, Any, Optional, Tuple
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.providers import BaseBackend
from qiskit.providers.models import BackendProperties
from qiskit.providers.models.backendproperties import Gate
from qiskit.transpiler import Layout, CouplingMap, PropertySet, PassManager
from qiskit.transpiler.basepasses import BasePass
from qiskit.dagcircuit import DAGCircuit
from qiskit.tools.parallel import parallel_map
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.passes import ApplyLayout
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.compiler import transpile
from qiskit.transpiler.preset_passmanagers import (level_0_pass_manager,
                                                   level_1_pass_manager,
                                                   level_2_pass_manager,
                                                   level_3_pass_manager)

from palloq.transpiler.preset_passmanagers.multi_pm import multi_tasking_pass_manager


def multitasking_transpile(multi_circuits: Union[QuantumCircuit, List[QuantumCircuit]],
                           backend=None,
                           basis_gates: Optional[List[str]] = None,
                           coupling_map: Optional[Union[CouplingMap, List[List[int]]]] = None,
                           backend_properties=None,
                           initial_layout: Optional[Union[Layout, Dict, List]] = None,
                           layout_method: Optional[str] = None,
                           routing_method: Optional[str] = None,
                           translation_method: Optional[str] = None,
                           seed_transpiler: Optional[int] = None,
                           optimization_level: Optional[int] = None,
                           pass_manager: Optional[PassManager] = None,
                           callback: Optional[Callable[[BasePass, DAGCircuit, float,
                                                        PropertySet, int], Any]] = None,
                           output_name: Optional[Union[str, List[str]]] = None,
                           crosstalk_prop: Optional[Dict[Tuple[int],
                                                         Dict[Tuple[int], int]]] = None,
                           multi_opt=False,
                           ) -> Union[QuantumCircuit, List[QuantumCircuit]]:
    """Mapping several circuits to single circuit based on calibration for the backend

    Args:
        multi_circuits: Small circuits to compose one big circuit(s)
        backend:
        backend_properties:
        output_name: the name of output circuit. str or List[str]

    Returns:
        composed multitasking circuit(s).
    """
    multi_circuits = multi_circuits if isinstance(
        multi_circuits[0], list) else [multi_circuits]

    # Get combine_args(mp_args) to configure the circuit combine job(s)
    transpile_args = _parse_transpile_args(multi_circuits, backend, basis_gates, coupling_map,
                                           backend_properties, initial_layout,
                                           layout_method, routing_method, translation_method,
                                           seed_transpiler, optimization_level,
                                           callback, output_name, multi_opt, crosstalk_prop)

    # combine circuits in parallel
    multi_programming_circuit = list(map(
        _multitasking_transpile, list(zip(multi_circuits, transpile_args))))

    if len(multi_programming_circuit) == 1:
        return multi_programming_circuit[0]
    return multi_programming_circuit


def _multitasking_transpile(circuit_config_tuple: Tuple[List[QuantumCircuit], Dict]) -> QuantumCircuit:
    circuits, transpile_config = circuit_config_tuple
    circuit = _compose_multicircuits(circuits, transpile_config)
    pass_manager_config = transpile_config['pass_manager_config']
    optimization_level = transpile_config['optimization_level']
    multi_opt = transpile_config['multi_opt']
    crosstalk_prop = transpile_config['crosstalk_prop']

    if multi_opt and isinstance(crosstalk_prop, Dict):
        pass_manager = multi_tasking_pass_manager(pass_manager_config,
                                                  crosstalk_prop)
        print("############## xtalk-aware multi-tasking ##############")
    elif multi_opt:
        pass_manager = multi_tasking_pass_manager(pass_manager_config)
        print("############## noise-aware multi-tasking ##############")
    elif optimization_level == 3:
        pass_manager = level_3_pass_manager(pass_manager_config)
        print("############## qiskit_noise-aware ##############")
    else:
        return circuit

    return pass_manager.run(circuit, callback=transpile_config['callback'],
                            output_name=transpile_config['output_name'])


def _compose_multicircuits(circuits: List[QuantumCircuit], transpile_config: Dict) -> QuantumCircuit:

    # num_qubit = combine_args['num_qubit']
    output_name = transpile_config['output_name']

    """FIXME!
    入力の量子回路の量子ビット数合計がbackendの量子ビット数を超える場合のErrorを作る

        if sum([circuit.num_qubit for circuit in circuits]) > num_qubit:
            raise
    """

    composed_multicircuit = QuantumCircuit(name=output_name)
    name_list = []
    bit_counter = 0
    dag_list = [circuit_to_dag(circuit) for circuit in circuits]
    return dag_to_circuit(_compose_dag(dag_list))


def _compose_dag(dag_list):
    """Compose each dag and return new multitask dag"""

    """FIXME 下記と同様
    # name_list = []
    """
    bit_counter = 0
    composed_multidag = DAGCircuit()
    for i, dag in enumerate(dag_list):
        register_size = dag.num_qubits()
        """FIXME
        Problem:
            register_name: register nameを定義すると、outputの `new_dag` に対して `dag_to_circuit()`
            を実行した時、
            qiskit.circuit.exceptions.CircuitError: 'register name "定義した名前" already exists'
            が発生するため、任意のレジスター名をつけることができない

        Code:
            reg_name_tmp = dag.qubits[0].register.name
            register_name = reg_name_tmp if (reg_name_tmp not in name_list) and (
                not reg_name_tmp == 'q') else None
            name_list.append(register_name)
        """
        # 上記FIXME部分はNoneで対応中: 2020 / 08 / 16
        register_name = None
        ########################

        qr = QuantumRegister(size=register_size, name=register_name)
        cr = ClassicalRegister(size=register_size, name=register_name)
        composed_multidag.add_qreg(qr)
        composed_multidag.add_creg(cr)
        qubits = composed_multidag.qubits[bit_counter: bit_counter+register_size]
        clbits = composed_multidag.clbits[bit_counter: bit_counter+register_size]
        composed_multidag.compose(dag, qubits=qubits, clbits=clbits)

        bit_counter += register_size
    return composed_multidag


def _remap_circuit_faulty_backend(circuit, num_qubits, backend_prop, faulty_qubits_map):
    faulty_qubits = backend_prop.faulty_qubits() if backend_prop else []
    disconnected_qubits = {k for k, v in faulty_qubits_map.items()
                           if v is None}.difference(faulty_qubits)
    faulty_qubits_map_reverse = {v: k for k, v in faulty_qubits_map.items()}
    if faulty_qubits:
        faulty_qreg = circuit._create_qreg(len(faulty_qubits), 'faulty')
    else:
        faulty_qreg = []
    if disconnected_qubits:
        disconnected_qreg = circuit._create_qreg(
            len(disconnected_qubits), 'disconnected')
    else:
        disconnected_qreg = []

    new_layout = Layout()
    faulty_qubit = 0
    disconnected_qubit = 0

    for real_qubit in range(num_qubits):
        if faulty_qubits_map[real_qubit] is not None:
            new_layout[real_qubit] = circuit._layout[faulty_qubits_map[real_qubit]]
        else:
            if real_qubit in faulty_qubits:
                new_layout[real_qubit] = faulty_qreg[faulty_qubit]
                faulty_qubit += 1
            else:
                new_layout[real_qubit] = disconnected_qreg[disconnected_qubit]
                disconnected_qubit += 1
    physical_layout_dict = {}
    for qubit in circuit.qubits:
        physical_layout_dict[qubit] = faulty_qubits_map_reverse[qubit.index]
    for qubit in faulty_qreg[:] + disconnected_qreg[:]:
        physical_layout_dict[qubit] = new_layout[qubit]
    dag_circuit = circuit_to_dag(circuit)
    apply_layout_pass = ApplyLayout()
    apply_layout_pass.property_set['layout'] = Layout(physical_layout_dict)
    circuit = dag_to_circuit(apply_layout_pass.run(dag_circuit))
    circuit._layout = new_layout
    return circuit


def _remap_layout_faulty_backend(layout, faulty_qubits_map):
    if layout is None:
        return layout
    new_layout = Layout()
    for virtual, physical in layout.get_virtual_bits().items():
        if faulty_qubits_map[physical] is None:
            raise TranspilerError("The initial_layout parameter refers to faulty"
                                  " or disconnected qubits")
        new_layout[virtual] = faulty_qubits_map[physical]
    return new_layout


def _parse_transpile_args(circuits, backend,
                          basis_gates, coupling_map, backend_properties,
                          initial_layout, layout_method, routing_method, translation_method,
                          seed_transpiler, optimization_level,
                          callback, output_name, multi_opt, crosstalk_prop) -> List[Dict]:
    """Resolve the various types of args allowed to the transpile() function through
    duck typing, overriding args, etc. Refer to the transpile() docstring for details on
    what types of inputs are allowed.

    Here the args are resolved by converting them to standard instances, and prioritizing
    them in case a transpile option is passed through multiple args (explicitly setting an
    arg has more priority than the arg set by backend).

    Returns:
        list[dicts]: a list of transpile parameters.
    """
    if initial_layout is not None and layout_method is not None:
        warnings.warn("initial_layout provided; layout_method is ignored.",
                      UserWarning)
    # Each arg could be single or a list. If list, it must be the same size as
    # number of circuits. If single, duplicate to create a list of that size.
    num_circuits = len(circuits)

    basis_gates = _parse_basis_gates(basis_gates, backend, num_circuits)
    """FIXME
    _parse_faulty_qubits_mapの周りの実装
    """
    faulty_qubits_map = [None]*num_circuits

    coupling_map = _parse_coupling_map(coupling_map, backend, num_circuits)
    backend_properties = _parse_backend_properties(
        backend_properties, backend, num_circuits)
    backend_num_qubits = _parse_backend_num_qubits(backend, num_circuits)
    """FIXME
    _parse_initial_layoutの引数に、combine後のcircuitを入れたい
    現状、num_circuitsにしているため、initial_layoutは実際には指定しても、作用しない
    """
    initial_layout = _parse_initial_layout(initial_layout, num_circuits)

    layout_method = _parse_layout_method(layout_method, num_circuits)
    routing_method = _parse_routing_method(routing_method, num_circuits)
    translation_method = _parse_translation_method(
        translation_method, num_circuits)
    seed_transpiler = _parse_seed_transpiler(seed_transpiler, num_circuits)
    optimization_level = _parse_optimization_level(
        optimization_level, num_circuits)
    output_name = _parse_output_name(output_name, num_circuits)
    callback = _parse_callback(callback, num_circuits)
    multi_opt = _parse_multi_opt(multi_opt, num_circuits)
    crosstalk_prop = _parse_crosstalk_prop(crosstalk_prop, num_circuits)

    list_transpile_args = []
    for args in zip(basis_gates, coupling_map, backend_properties,
                    initial_layout, layout_method, routing_method, translation_method,
                    seed_transpiler, optimization_level,
                    output_name, callback, backend_num_qubits, faulty_qubits_map, multi_opt, crosstalk_prop):
        transpile_args = {'pass_manager_config': PassManagerConfig(basis_gates=args[0],
                                                                   coupling_map=args[1],
                                                                   backend_properties=args[2],
                                                                   initial_layout=args[3],
                                                                   layout_method=args[4],
                                                                   routing_method=args[5],
                                                                   translation_method=args[6],
                                                                   seed_transpiler=args[7],),
                          'optimization_level': args[8],
                          'output_name': args[9],
                          'callback': args[10],
                          'backend_num_qubits': args[11],
                          'faulty_qubits_map': args[12],
                          'multi_opt': args[13],
                          'crosstalk_prop': args[14]
                          }
        list_transpile_args.append(transpile_args)

    return list_transpile_args


def _create_faulty_qubits_map(backend):
    """If the backend has faulty qubits, those should be excluded. A faulty_qubit_map is a map
       from working qubit in the backend to dumnmy qubits that are consecutive and connected."""
    faulty_qubits_map = None
    if backend is not None:
        if backend.properties():
            faulty_qubits = backend.properties().faulty_qubits()
            faulty_edges = [
                gates.qubits for gates in backend.properties().faulty_gates()]
        else:
            faulty_qubits = []
            faulty_edges = []

        if faulty_qubits or faulty_edges:
            faulty_qubits_map = {}
            configuration = backend.configuration()
            full_coupling_map = configuration.coupling_map
            functional_cm_list = [edge for edge in full_coupling_map
                                  if (set(edge).isdisjoint(faulty_qubits) and
                                      edge not in faulty_edges)]

            connected_working_qubits = CouplingMap(
                functional_cm_list).largest_connected_component()
            dummy_qubit_counter = 0
            for qubit in range(configuration.n_qubits):
                if qubit in connected_working_qubits:
                    faulty_qubits_map[qubit] = dummy_qubit_counter
                    dummy_qubit_counter += 1
                else:
                    faulty_qubits_map[qubit] = None
    return faulty_qubits_map


def _parse_basis_gates(basis_gates, backend, num_circuits):
    # try getting basis_gates from user, else backend
    if basis_gates is None:
        if getattr(backend, 'configuration', None):
            basis_gates = getattr(backend.configuration(), 'basis_gates', None)
    # basis_gates could be None, or a list of basis, e.g. ['u3', 'cx']
    if basis_gates is None or (isinstance(basis_gates, list) and
                               all(isinstance(i, str) for i in basis_gates)):
        basis_gates = [basis_gates] * num_circuits

    return basis_gates


def _parse_coupling_map(coupling_map, backend, num_circuits):
    # try getting coupling_map from user, else backend
    if coupling_map is None:
        if getattr(backend, 'configuration', None):
            configuration = backend.configuration()
            if hasattr(configuration, 'coupling_map') and configuration.coupling_map:
                faulty_map = _create_faulty_qubits_map(backend)
                if faulty_map:
                    coupling_map = CouplingMap()
                    for qubit1, qubit2 in configuration.coupling_map:
                        if faulty_map[qubit1] is not None and faulty_map[qubit2] is not None:
                            coupling_map.add_edge(
                                faulty_map[qubit1], faulty_map[qubit2])
                else:
                    coupling_map = CouplingMap(configuration.coupling_map)

    # coupling_map could be None, or a list of lists, e.g. [[0, 1], [2, 1]]
    if coupling_map is None or isinstance(coupling_map, CouplingMap):
        coupling_map = [coupling_map] * num_circuits
    elif isinstance(coupling_map, list) and all(isinstance(i, list) and len(i) == 2
                                                for i in coupling_map):
        coupling_map = [coupling_map] * num_circuits

    coupling_map = [CouplingMap(cm) if isinstance(
        cm, list) else cm for cm in coupling_map]

    return coupling_map


def _parse_backend_properties(backend_properties, backend, num_circuits):
    # try getting backend_properties from user, else backend
    if backend_properties is None:
        if getattr(backend, 'properties', None):
            backend_properties = backend.properties()
            if backend_properties and \
                    (backend_properties.faulty_qubits() or backend_properties.faulty_gates()):
                faulty_qubits = sorted(
                    backend_properties.faulty_qubits(), reverse=True)
                faulty_edges = [
                    gates.qubits for gates in backend_properties.faulty_gates()]
                # remove faulty qubits in backend_properties.qubits
                for faulty_qubit in faulty_qubits:
                    del backend_properties.qubits[faulty_qubit]

                gates = []
                for gate in backend_properties.gates:
                    # remove gates using faulty edges or with faulty qubits (and remap the
                    # gates in terms of faulty_qubits_map)
                    faulty_qubits_map = _create_faulty_qubits_map(backend)
                    if any([faulty_qubits_map[qubits] is not None for qubits in gate.qubits]) or \
                            gate.qubits in faulty_edges:
                        continue
                    gate_dict = gate.to_dict()
                    replacement_gate = Gate.from_dict(gate_dict)
                    gate_dict['qubits'] = [faulty_qubits_map[qubit]
                                           for qubit in gate.qubits]
                    args = '_'.join([str(qubit)
                                     for qubit in gate_dict['qubits']])
                    gate_dict['name'] = "%s%s" % (gate_dict['gate'], args)
                    gates.append(replacement_gate)

                backend_properties.gates = gates
    if not isinstance(backend_properties, list):
        backend_properties = [backend_properties] * num_circuits
    return backend_properties


def _parse_backend_num_qubits(backend, num_circuits):
    if backend is None:
        return [None] * num_circuits
    if not isinstance(backend, list):
        return [backend.configuration().n_qubits] * num_circuits
    backend_num_qubits = []
    for a_backend in backend:
        backend_num_qubits.append(a_backend.configuration().n_qubits)
    return backend_num_qubits


"""FIXME
combine前のcircuitsでは、initial_layoutを取り扱えない
combineしてから、transpileの形に戻すか、別の方法で実装する必要がある。

def _parse_initial_layout(initial_layout, circuits):
    initial_layout could be None, or a list of ints, e.g. [0, 5, 14]
    or a list of tuples/None e.g. [qr[0], None, qr[1]] or a dict e.g. {qr[0]: 0}
    def _layout_from_raw(initial_layout, circuit):
        if initial_layout is None or isinstance(initial_layout, Layout):
            return initial_layout
        elif isinstancelist(initial_layout):
            if all(isinstanceint(elem) for elem in initial_layout):
                initial_layout = Layout.from_intlist(
                    initial_layout, *circuit.qregs)
            elif all(elem is None or isinstance(elem, Qubit) for elem in initial_layout):
                initial_layout = Layout.from_qubit_list(initial_layout)
        elif isinstance(initial_layout, dict):
            initial_layout = Layout(initial_layout)
        else:
            raise TranspilerError(
                "The initial_layout parameter could not be parsed")
        return initial_layout

    # multiple layouts?
    if isinstance(initial_layout, list) and \
            any(isinstance(i, (list, dict)) for i in initial_layout):
        initial_layout = [_layout_from_raw(lo, circ) if isinstance(lo, (list, dict)) else lo
                          for lo, circ in zip(initial_layout, circuits)]
    else:
        # even if one layout, but multiple circuits, the layout needs to be adapted for each
        initial_layout = [_layout_from_raw(
            initial_layout, circ) for circ in circuits]
"""


def _parse_initial_layout(initial_layout, num_circuits):

    if initial_layout is None:
        initial_layout = [None] * num_circuits
    if not isinstance(initial_layout, list):
        initial_layout = [initial_layout] * num_circuits

    return initial_layout


def _parse_layout_method(layout_method, num_circuits):
    if not isinstance(layout_method, list):
        layout_method = [layout_method] * num_circuits
    return layout_method


def _parse_routing_method(routing_method, num_circuits):
    if not isinstance(routing_method, list):
        routing_method = [routing_method] * num_circuits
    return routing_method


def _parse_translation_method(translation_method, num_circuits):
    if not isinstance(translation_method, list):
        translation_method = [translation_method] * num_circuits
    return translation_method


def _parse_seed_transpiler(seed_transpiler, num_circuits):
    if not isinstance(seed_transpiler, list):
        seed_transpiler = [seed_transpiler] * num_circuits
    return seed_transpiler


def _parse_optimization_level(optimization_level, num_circuits):
    if not isinstance(optimization_level, list):
        optimization_level = [optimization_level] * num_circuits
    return optimization_level


def _parse_callback(callback, num_circuits):
    if not isinstance(callback, list):
        callback = [callback] * num_circuits
    return callback


def _parse_output_name(output_name, num_circuits):
    if output_name is None:
        output_name = [None] * num_circuits
    if output_name is not list:
        if num_circuits != 1 and not isinstance(output_name, None):
            output_name = [str(output_name)+"_" +
                           str(i) for i in range(num_circuits)]
        else:
            output_name = [None] * num_circuits
    return output_name


def _parse_multi_opt(multi_opt, num_circuits):
    if multi_opt is not list:
        multi_opt = [multi_opt] * num_circuits
    return multi_opt


def _parse_crosstalk_prop(crosstalk_prop, num_circuits):
    if crosstalk_prop is None:
        crosstalk_prop = [None] * num_circuits
    if crosstalk_prop is not list:
        crosstalk_prop = [crosstalk_prop] * num_circuits
    return crosstalk_prop


def _split_inputcircuits(multi_circuits):
    """TODO

    """
    multi_circuits = multi_circuits
    return multi_circuits
