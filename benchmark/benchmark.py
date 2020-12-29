"""
Benchmark environement for multi circuit composer and compiler
"""
import logging
import numpy as np

from typing import List
from qiskit import QuantumCircuit, IBMQ, execute, Aer

# internal
from palloq.multicircuit.mcircuit_composer import MultiCircuitComposer, MCC, MCC_dp
from palloq.compiler.multi_transpile import multi_transpile

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
        job = execute(qc, backend=self.backend)
        return job.result().get_counts(qc)

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
            _log.info(f"Got count {count}")
            self.results[_c] = {}
            self.results[_c]["count"] = count
            self.results[_c]["circuit"] = qc
            _c += 1
            # loop interupter
            if _size == len(self.qcircuits):
                break
        if len(self.qcircuits) > 0:
            raise Exception(f"Something went wrong.\
{len(self.qcircuits)} circuits remain. ")

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

    def summary(self):
        """
        Show summary of entire execution.

        This function should visualize performance for each pairs of execution.
        """
        if self.results == {}:
            raise Exception("No results to show.")

        for i, res in self.results.items():
            # show the pairs of circuits
            _log.info("Circuit pairs")
            # parse results for each circuit
            _count = self._parse_count(res["count"])
            print("count", _count)
            # evaluation result
            _log.info(f"Evaluaiton Result with {self._metric.__name__}")


class QCEnv:
    def __init__(self):
        pass


def kd(prob_distA: List,
       prob_distB: List):
    p1 = np.array(prob_distA) + 1e-10
    p2 = np.array(prob_distB) + 1e-10
    return sum(p1 * np.log(p1/p2))

def jsd(prob_distA, prob_distB):
    """
    Jensen Shanon Divergence
    """
    pass

if __name__ == "__main__":
    # preparer circuits
    qcs = []
    for i in range(20):
        qc = QuantumCircuit(8, 3)
        for j in range(i):
            qc.h(0)
            qc.cx(0, 1)
        qc.measure(0, 0)
        qc.measure(1, 1)
        qc.measure(2, 2)
        qcs.append(qc)

    # prepare benchmark environments
    IBMQ.load_account()
    provider = IBMQ.get_provider(hub='ibm-q-utokyo',
                                 group='keio-internal',
                                 project='keio-students')
    backend = provider.get_backend("ibmq_manhattan")
    bench = MCCBench(circuits=qcs, backend=backend)

    # set composer and compiler
    bench.set_composer(MCC_dp)
    bench.set_compiler(multi_transpile)

    # evaluate with circuit datasets
    # with tracking all info level log
    bench.evaluate(track=True)
    # TODO dazai: 
    # 1. get result
    # 2. js, norm, fidelity, evaluate
    bench.summary()
