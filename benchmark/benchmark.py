"""
Benchmark environement for multi circuit composer
"""
import logging

from typing import List
from qiskit import QuantumCircuit, IBMQ, execute

# internal
from daq.multicircuit.mcircuit_composer import MultiCircuitComposer

_log = logging.getLogger(__name__)


class MCCBench:
    """
    MCCBench benchmarks multi circuit composer.

    This class has series of support tools for benchmarks
    Arugments:
        circuits: (list) list or array of QuantumCircuit in qiskit.
        backend: TODO extend fake device (currently only real IBMQ device)
        track: (bool) if track the all execution or not
    """

    def __init__(self,
                 circuits: List[QuantumCircuit],
                 backend=None,
                 track: bool = False):
        if not all(map(lambda x: isinstance(x, QuantumCircuit), circuits)):
            raise Exception("Input circuit must be instance of QuantumCircuit")
        self.qcircuits = circuits

        if not isinstance(backend, IBMQ):
            raise NotImplementedError("Currently, IBMQ is only available ")

        if "properties" not in dir(backend):
            raise Exception("No property found in backend")
        self.backend = backend
        self._device_size = self.backend.properties.n_qubits
        self._track = track

        # Initialize composer and compiler
        self._composer = None
        self._compiler = None

        # results
        self.results = []

    def set_composer(self, composer):
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
        self._composer = composer(self.qcirciuts, self._device_size)

    def set_compiler(self, compiler):
        """
        setting compiler for actual execution
        """
        self._compiler = compiler

    def set_metric(self):
        """
        setting metric to evaluate the final probability distribution
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
            multi_circuit = self._composer.pop()

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

        # 1. loop for circuiuts
        while len(self.qcircuits) > 0:
            # 2.1 run compose and compile
            qc = self.run()
            # 2.2 actual execution
            result = self._execute(qc)
            self.results.append(result)


class QCEnv:
    def __init__(self):
        pass


if __name__ == "__maim__":
    # preparer circuits
    bench_circuits = []
    bench = MCCBench()