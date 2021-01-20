from typing import List, Union
import os
import pathlib
import logging
from glob import glob
from copy import deepcopy

from qiskit.circuit import QuantumCircuit
from qiskit.compiler import transpile

from .pickle_tools import pickle_dump, pickle_load

_log = logging.getLogger(__name__)
class PrepareQASMBench():     
    def __init__(self, bench_names: List[str], path):
        """
        This function loads qasm files
        Arguments:
            size: (str) circuit size (small, medium, large)
        """
        self.bench_names = bench_names
        self.benchmarks = {}
        qasmbench = pickle_load(path)

        for name in self.bench_names: 
            self.benchmarks[name] = qasmbench[name]
        
    def qc_list(self):
        qc_list = []
        for i, name in enumerate(self.bench_names):
            qc = deepcopy(self.benchmarks[name]['qc'])
            qc.name = name + "_" +str(i)
            for qreg in qc.qregs: 
                qreg.name = qc.name
            qc_list.append(qc)
        return qc_list

    def to_dict(self): 
        return self.benchmarks


# From here you only have to execute save_QauntumCircuit function at first time.
def save_QuantumCircuit(qasmbench_path, save_dir, basis_gates=None):
    """
    Convert .qasm data to QuantumCircuit and save it with properties as dict in pickle file.
    
    Args: 
        qasmbench_path
    """

    # search qasm files
    bench_files = glob(str(qasmbench_path) + '/**/*.qasm', recursive=True)
    
    # convert qasm to QauntumCircuit and add properties
    bench_dict = {}
    for file in bench_files: 
        qc = qasm_to_qc(file)
        name = path_to_filename(file)
        if qc: 
            bench_dict[name] = qc_properties(qc, basis_gates)
    # save
    save_path = save_dir + '/qasmbench.pickle'
    pickle_dump(bench_dict, save_path)
    
    return bench_dict

def qasm_to_qc(qasmfile):
    try:
        qc = QuantumCircuit.from_qasm_file(qasmfile)
        qc.remove_final_measurements()
        qc.measure_active()
    except Exception:
        _log.warning(f"Parsing Qasm Failed at {qasmfile}")
        qc = None
    return qc

def path_to_filename(filepath: str):
    return os.path.splitext(os.path.basename(filepath))[0]

def qc_properties(qc, basis_gates):
    properties = {}
    properties["qc"] = qc
    if basis_gates: 
        qc = transpile(qc, basis_gates)
    properties['num_qubits'] = qc.num_qubits
    properties['num_clbits'] = qc.num_clbits
    properties['ops'] = qc.count_ops()
    properties['num_cx'] = properties['ops'].get('cx', 0)
    properties['depth'] = qc.depth()

    return properties

if __name__ == '__main__':
    this_path = os.path.abspath(__file__)
    par_dir = os.path.dirname(this_path) # /utils
    grandpar_dir = os.path.dirname(par_dir) # /benchkark
    grandgrandpar_dir = os.path.dirname(grandpar_dir) # /palloq
    qasmbench_path = grandgrandpar_dir + '/qasm_bench'

    basis_gates=['id', 'rz', 'sx', 'x', 'cx']
    
    save_QuantumCircuit(qasmbench_path, grandpar_dir)