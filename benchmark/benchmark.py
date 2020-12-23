"""
Benchmark environement for multi circuit composer
"""
import logging

from typing import List
from qiskit import QuantumCircuit, IBMQ, execute, Aer

# internal
from palloq.multicircuit.mcircuit_composer import MultiCircuitComposer, MCC

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
        if not all(map(lambda x: isinstance(x, QuantumCircuit), circuits)):
            raise Exception("Input circuit must be instance of QuantumCircuit")
        self.qcircuits = circuits

#         if not isinstance(backend, (IBMQ, Aer)):
#             raise NotImplementedError("Currently, IBMQ and Aer simulators\
# are only available ")

        if "properties" not in dir(backend):
            raise Exception("No property found in backend")
        self.backend = backend
        self._device_size = self.backend.configuration().n_qubits
        self._track = track

        # Initialize composer and compiler
        self._composer = None
        self._compiler = None

        # metric to evaluate probability distribution
        self._metric = None

        # results
        self.results = []

    def set_composer(self, composer, *prop):
        """
        Set a multi-circuit composer to fold up several different circiuts.

        Arguments:
            composer: (MultiCircuitComposer) 
                      This composer must have compose function.
                      This composer must be instanciated before.
        """
        if not issubclass(composer, MultiCircuitComposer):
            raise Exception("composer must be a subclass\
of multicircuit composer")
        self._composer = composer(self.qcircuits, self._device_size, *prop)

    def set_compiler(self, compiler):
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
        pass

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

    def summary(self):
        pass

    def _execute(self, qc):
        """
        Actual execution of quantum circuit.
        """
        job = execute(qc, backend=self.backend)
        return job.result()

    def run(self) -> QuantumCircuit:
        """
        run function do optimization in just one time.

        This function pop out pair of circuits.
        """
        # 0. if there is composer and compiler, do compose
        if self._composer is not None and self._compiler is not None:
            # 1. compose multiple circuits
            self._composer.compose()
            # 1.1 take composed circuit
            _s = len(self.qcircuits)
            multi_circuit = self._composer.pop()
            # debug reason
            assert _s != self.qcircuits
            # 1.2 compile multi circuit
            qc = self._compiler(multi_circuit)
            return qc
        elif self._composer is None and self._compiler is None:
            # 2. just sequencial
            return self.qcircuits.pop()
        else:
            raise Exception("Both of composer and compiler is None or\
neither of them are None is fine.")

    def evaluate(self,
                 track: bool = False):
        """
        evaluate entire performance.

        Loop for all quantum circuits. 
        """
        # 0. if track mode, all executions are tracked
        if track:
            logging.basicConfig(level=logging.INFO)

        # previous size
        _size = len(self.qcircuits)

        # 1. loop for circuiuts
        while len(self.qcircuits) > 0:
            # 2.1 run compose and compile
            qc = self.run()
            # 2.2 actual execution
            result = self._execute(qc)
            self.results.append(result)
            # loop interupter
            if _size == len(self.qcircuits):
                raise Exception("Something went wrong")


class QCEnv:
    def __init__(self):
        pass


if __name__ == "__main__":
    # preparer circuits
    qcs = []
    for i in range(10):
        qc = QuantumCircuit(3)
        for j in range(i):
            qc.h(0)
            qc.cx(0, 1)
        qcs.append(qc)

    # prepare benchmark environments
    provider = IBMQ.load_account()
    backend = provider.get_backend("ibmq_vigo")
    bench = MCCBench(circuits=qcs, backend=backend)

    # set composer and compiler
    bench.set_composer(MCC, 0.1)
    bench.set_compiler()
    
