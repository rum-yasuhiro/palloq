from typing import Tuple, List

import qiskit.ignis.verification.randomized_benchmarking as rb

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
    backend,
    num_set_qubits= 1,
) -> Tuple[List[List[int]]]:
    """
    Args:
        backend_name
    """
    num_qubits = backend.configuration().num_qubits
    patterns = [[i] for i in range(num_qubits)]

    return patterns


def _run_RB(rb_pattern_set: List[List[List[int]]]): 

def _simRB(rb_pattern_set: List[List[List[int]]]):

    for rb_pattern in rb_pattern_set:
