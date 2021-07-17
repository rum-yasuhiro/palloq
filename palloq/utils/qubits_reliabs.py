from typing import List, Dict, Tuple


def erates_1qmeas(backend)->List[int]:

    prop = backend.properties()
    prop

def erates_2qgates(backend)->Dict[Tuple[int], float]:
    prop = backend.properties()
    qubits_reliabs = {}

    for ginfo in prop.gates:
            if ginfo.gate == "cx":
                for item in ginfo.parameters:
                    if item.name == "gate_error":
                        g_reliab = 1.0 - item.value
                        break
                    g_reliab = 1.0
                _q_i = min(ginfo.qubits[0], ginfo.qubits[1])
                _q_j = max(ginfo.qubits[0], ginfo.qubits[1])
                qubits_reliabs[(_q_i, _q_j)] = g_reliab
    return qubits_reliabs