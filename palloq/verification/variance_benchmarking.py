from typing import List, Union

import qiskit.ignis.verification.randomized_benchmarking as rb
from qiskit.providers.ibmq.ibmqbackend import IBMQBackend
from qiskit.providers.ibmq.job.ibmqjob import IBMQJob

from palloq.utils import get_IBMQ_backend


def run(backend):
    """
    Args:
        backend: Backend device you want to run


    """
    # prepare backend device
    get_IBMQ_backend()

    # prepare rb pattern based on backend device.

    # run simRB

    # run individual RB

    # run simRB again

    return


def results(job):
    """
    Args:
        job: IBMQ job
    """

    return


def rb_pattern(
    backend: IBMQBackend,
    num_set_qubits: int = 1,
) -> List[List[List[int]]]:

    if num_set_qubits == 1:
        num_qubits = num_qubits = backend.configuration().num_qubits
        pattern_set = [[[i]] for i in range(num_qubits)]
    return pattern_set


def sim_rb_pattern(
    backend: IBMQBackend,
    num_set_qubits: int = 1,
) -> List[List[List[int]]]:
    """
    Args:
        backend_name
    """

    if num_set_qubits == 1:
        num_qubits = backend.configuration().num_qubits
        pattern_set = [[[i] for i in range(num_qubits)]]

    return pattern_set


def _run_RB(
    backend: IBMQBackend,
    shots: int,
    length_vector: List[int],
    nseeds: int,
    rb_pattern: List[List[int]],
) -> Union[IBMQJob, List[IBMQJob]]:
    """Function for Randomized Benchmarking"""
    rb_opts = {
        "length_vector": length_vector,
        "nseeds": nseeds,
        "rb_pattern": rb_pattern,
    }

    rb_circs, xdata = rb.randomized_benchmarking_seq(**rb_opts)

    # Calculate gate per clifford (gcp)
    gates_per_cliff = rb.rb_utils.gates_per_clifford(
        transpile_list_pairs,
        xdata[0],
        basis_gates,
        qubits=list(twoQconnection),
    )

    # run rb on backend
    job = backend.run(
        circuits=rb_circs,
        shots=shots,
    )

    return job


def _simRB(rb_pattern_set: List[List[List[int]]]):
    """Function for Simultaneous Randomized Benchmarking"""
    for rb_pattern in rb_pattern_set:
        pass
    return
