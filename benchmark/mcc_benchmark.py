"""
Benchmark environement for multi circuit composer and compiler
"""
import logging
import numpy as np
import copy

from typing import List
from scipy.spatial.distance import jensenshannon as jsd
from qiskit import QuantumCircuit, IBMQ, execute, Aer
from concurrent.futures import ProcessPoolExecutor

# internal
from palloq.multicircuit.mcircuit_composer import MultiCircuitComposer, MCC, MCC_dp, MCC_random
from palloq.compiler.multi_transpile import multi_transpile

from qiskit.test.mock import FakeToronto
from utils import PrepareQASMBench

_log = logging.getLogger(__name__)


class MCCBench:
    """
    MCCBench benchmarks multi circuit composer.

    This class has series of support tools for benchmarks
    Arugments:
        circuits: (list) list or array of QuantumCircuit in qiskit.
        backend: TODO extend fake device
        track: (bool) if track the all execution or not
    """

    def __init__(self,
                 circuits: List[QuantumCircuit],
                 backend,
                 shots,
                 track: bool = False):
        # list of circuits
        if not all(map(lambda x: isinstance(x, QuantumCircuit), circuits)):
            raise Exception("Input circuit must be instance of QuantumCircuit")
        self.qcircuits = circuits

        # need backend property to get the number of qubits in a device
        if "properties" not in dir(backend):
            raise Exception("No property found in backend")
        self.backend = backend
        # the number of qubits
        self._device_size = self.backend.configuration().n_qubits
        self._track = track

        # Initialize composer and compiler
        self._composer = None
        self._compiler = None

        # how many times the circuit is executed
        self.shots = shots

        # metric to evaluate probability distribution
        self._metric = None

        # results
        self.results = {}

    def set_composer(self, composer, *prop):
        """
        Set a multi-circuit composer to fold up several different circiuts.

        Arguments:
            composer: (MultiCircuitComposer) 
                      This composer must have compose function.
        """
        if not issubclass(composer, MultiCircuitComposer):
            raise Exception("composer must be a subclass\
of multicircuit composer")
        self._composer = composer(self.qcircuits, self._device_size, *prop)

    def set_compiler(self, compiler, *prop):
        """
        setting compiler for actual execution
        """
        self._compiler = compiler

    def set_metric(self, metric_func):
        """
        setting metric to evaluate the final probability distribution

        Argument:
            metric_func: (function(a, b))Function to evaluate 
                         two different probability distribution
        """
        self._metric = metric_func

    def compose(self) -> list:
        """
        compose circuit with composer
        """
        if self._composer is None:
            raise Exception("No composer found")
        # generate multi circuit
        done = self._composer.compose()
        # TODO check if this' ok or not
        yield done

    def _execute(self, qc):
        """
        Execution wrapper for getting count
        """
        job = execute(qc, backend=self.backend, shots=self.shots)
        count = job.result().get_counts(qc)
        return count

    def _execute_sim(self, qc):
        """
        Execution on the qasm_simulator
        """
        job = execute(qc, backend=Aer.get_backend("qasm_simulator"), shots=self.shots)
        count = job.result().get_counts(qc)
        return count

    def run(self) -> QuantumCircuit:
        """
        Compose several circuit into one circuit and compile it.

        This function pop out pair of circuits.
        """
        # 0. if there is composer and compiler, do compose
        if self._composer is not None and self._compiler is not None:
            # 1. compose multiple circuits
            # record the number of circuits before composition
            _s = len(self.qcircuits)
            # 1.1 take composed circuit
            multi_circuit = self._composer.compose()
            # debug reason
            assert _s != len(self.qcircuits)
            _log.info([i.name for i in multi_circuit.circuits()])
            # 1.2 compile multi circuit
            # FIXME choose one of either
            qc = self._compiler(multi_circuit.circuits(), xtalk_prop={})
            return qc
        elif self._composer is None and self._compiler is None:
            # 2. just sequencial
            return [self.qcircuits.pop()]
        else:
            raise Exception("Both of composer and compiler is None or\
neither of them are None is fine.")


    def evaluate(self,
                 track: bool = False):
        """
        Evaluate entire performance of composer.

        Loop for all quantum circuits.
        """
        # 0. if track mode, all executions are tracked
        if track:
            logging.basicConfig(level=logging.INFO)

        # previous size
        _size = len(self.qcircuits)

        # 1. loop for circuiuts
        _c = 0  # loop counter
        while len(self.qcircuits) > 0:
            # 2.1 run compose and compile
            _log.info(f"{_c} time execution start")
            qc = self.run()
            # 2.2 actual execution
            count = self._execute(qc)
            # simulation count
            sim_count = self._execute_sim(qc)

            _log.info(f"Got count {count}")
            self.results[_c] = {}
            self.results[_c]["count"] = count
            self.results[_c]["sim_count"] = sim_count
            self.results[_c]["circuit"] = qc
            _c += 1
            # loop interupter
            if _size == len(self.qcircuits):
                break
        if len(self.qcircuits) > 0:
            raise Exception(f"Something went wrong.\
{len(self.qcircuits)} circuits remain. ")
        print("count", _c)

    def _parse_count(self, count):
        """
        Parse output counts and make it readable.

        Argument:
            count: (dict) output count of execution.
            i.g. {'000 001': 100, '000 010': 80...}
        """
        _result = {}
        # 0. initialize result format
        first_count = next(iter(count)).split(" ")
        for ib, b in enumerate(first_count):
            # make empty dict to store the measurement results
            _csize = len(b)
            _result[ib] = {format(t, "0%db" % (_csize)): 0
                           for t in range(2**_csize)}
        # update count values
        for ct, val in count.items():
            _split_count = ct.split(" ")
            for ic, b in enumerate(_split_count):
                _result[ic][b] += val
        return _result
    
    def _calc_pst(self, emp_count, sim_count):
        # success trial
        pst = 0
        for label, count in sim_count.items():
            # label, count
            _s = 0
            if count != 0:
                emp_c = emp_count.get(label, 0)
                _s = emp_c/count
                # _success_rate = _s if _s <= 1 else 0
            pst += _s
        return pst

    
    def _calc_jsd(self, emp_count, sim_count):
        _size_r = len(next(iter(emp_count)))
        _size_s = len(next(iter(sim_count)))
        if _size_s != _size_r:
            raise Exception("The size of bit must be the same between two results")
        bits = [format(i, '0%db'%_size_r) for i in range(2**_size_r)]
        prob_r = np.array([emp_count.get(b, 0)/self.shots for b in bits])
        prob_s = np.array([sim_count.get(b, 0)/self.shots for b in bits])
        return jsd(prob_r, prob_s)

    def summary(self):
        """
        Show summary of entire execution.

        This function should visualize performance for each pairs of execution.
        """
        if self.results == {}:
            raise Exception("No results to show.")
        jsds = []
        for i, res in self.results.items():
            # show the pairs of circuits
            _log.info("Circuit pairs")
            # parse results for each circuit
            _count = self._parse_count(res["count"])
            _sim_count = self._parse_count(res["sim_count"])
            _jsd = []
            for c, s in zip(_count.values(), _sim_count.values()):
                # evaluation result
                _jsd.append(self._calc_pst(c, s))
            jsds.append(np.mean(_jsd))
        return np.mean(jsds)


def qcircuits(num):
    # 0. prepare circuits (no "inverseqft_n4","shor_n5")
    qasm_bench = ["adder_n4",
                  "basis_change_n3",
                  "cat_state_n4",
                  "deutsch_n2",
                  "error_correctiond3_n5",
                  "fredkin_n3",
                  "grover_n2",
                  "hs4_n4",
                  "iswap_n2",
                  "linearsolver_n3",
                  "lpn_n5",
                  "qec_en_n5",
                  "toffoli_n3",
                  "variational_n4",
                  "wstate_n3"]
    # kakeru 2
    qcircuit = PrepareQASMBench(qasm_bench, "qasmbench.pickle").qc_list()
    _qcs = []
    for _ in range(num):
        for qc in qcircuit:
            _qcs.append(copy.copy(qc))
    return _qcs


def dp_bench(offset):
    ave = []
    IBMQ.load_account()
    # prepare benchmark environments
    provider = IBMQ.get_provider(hub='ibm-q-utokyo',
                                 group='keio-internal',
                                 project='keio-students')
    backend = provider.get_backend("ibmq_sydney")
    # backend = FakeToronto()
    for _ in range(5):
        qcs = qcircuits(2)
        bench = MCCBench(circuits=qcs, backend=backend, shots=8192)
        # set composer and compiler
        
        # print("offset", offset)
        bench.set_composer(MCC_dp, offset)
        bench.set_compiler(multi_transpile)

        # evaluate with circuit datasets
        # with tracking all info level log
        bench.evaluate(track=False)
        _jsd = bench.summary()
        print("cp", _jsd)
        ave.append(_jsd)
    return np.mean(ave), np.std(ave), offset


def dp_bench_single(offset):
    IBMQ.load_account()
    # prepare benchmark environments
    provider = IBMQ.get_provider(hub='ibm-q-utokyo',
                                 group='keio-internal',
                                 project='keio-students')
    backend = provider.get_backend("ibmq_sydney")
    # backend = FakeToronto()
    qcs = qcircuits(2)
    bench = MCCBench(circuits=qcs, backend=backend, shots=8192)
    # set composer and compiler
    
    # print("offset", offset)
    bench.set_composer(MCC_dp, offset)
    bench.set_compiler(multi_transpile)

    # evaluate with circuit datasets
    # with tracking all info level log
    bench.evaluate(track=False)
    _jsd = bench.summary()
    return _jsd


def rd_bench_single(offset):
    IBMQ.load_account()
    # prepare benchmark environments
    provider = IBMQ.get_provider(hub='ibm-q-utokyo',
                                 group='keio-internal',
                                 project='keio-students')
    backend = provider.get_backend("ibmq_sydney")
    # backend = FakeToronto()
    qcs = qcircuits(2)
    bench = MCCBench(circuits=qcs, backend=backend, shots=8192)
    # set composer and compiler
    
    # print("offset", offset)
    bench.set_composer(MCC_random, offset)
    bench.set_compiler(multi_transpile)

    # evaluate with circuit datasets
    # with tracking all info level log
    bench.evaluate(track=False)
    _jsd = bench.summary()
    return _jsd


def rand_bench(offset):
    ave = []
    IBMQ.load_account()
    # prepare benchmark environments
    provider = IBMQ.get_provider(hub='ibm-q-utokyo',
                                 group='keio-internal',
                                 project='keio-students')
    backend = provider.get_backend("ibmq_sydney")
    # backend = FakeToronto()
    for _ in range(5):
        qcs = qcircuits(2)
        bench = MCCBench(circuits=qcs, backend=backend, shots=8192)
        # set composer and compiler
        
        # print("offset", offset)
        bench.set_composer(MCC_random, offset)
        bench.set_compiler(multi_transpile)

        # evaluate with circuit datasets
        # with tracking all info level log
        bench.evaluate(track=False)
        _jsd = bench.summary()
        print("rd", _jsd)
        ave.append(_jsd)
    return np.mean(ave), np.std(ave), offset



if __name__ == "__main__":
    # preparer circuits
    # prepare two same circuits for each
    ave = []
    # start process
    max_workers = None
    offsets = [i for i in range(5)]
    # 
    # dp_qualities = {}
    # with ProcessPoolExecutor(max_workers=max_workers) as executor:
    #     for quality, std, offset in executor.map(dp_bench, offsets):
    #         dp_qualities[offset] = [quality, std]

    # # for of in offsets:
    # #     quality, std = dp_bench(of)
    # #     dp_qualities[of] = [quality, std]
    # print("dp", dp_qualities)

    space = 0
    quality_dp = dp_bench_single(space)
    print(quality_dp)
    quality_rd = rd_bench_single(space)
    print(quality_rd)

    # rand_qualities = {}
    # with ProcessPoolExecutor(max_workers=max_workers) as executor:
    #     for quality, std, offset in executor.map(rand_bench, offsets):
    #         rand_qualities[offset] = [quality, std]

    # for of in offsets:
    #     quality, std = rand_bench(of)
    #     rand_qualities[of] = [quality, std]
    
    # print("random", rand_qualities)

    # MCC_dp
    # data
    # random 
    # [0.531828905104023, 0.4015653639266842, 0.5002611681912982, 0.5769783672760296, 0.43200043949544337]
    
    # mcc_dp
    # [0.42855881015065445, 0.33203026010954634, 0.5153705028449385, 0.7083726421240693]
    # [0.337240682194642, 0.3362892689513287, 0.2501621169814029, 0.35773913544107594, 0.4458317494754765, 0.5355503073535636, 0.5467164954868409, 0.711480176484298]
