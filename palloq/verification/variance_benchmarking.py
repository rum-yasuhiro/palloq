from typing import List, Tuple

import qiskit.ignis.verification.randomized_benchmarking as rb
from qiskit.providers.ibmq.ibmqbackend import IBMQBackend
from qiskit.providers.ibmq.job.ibmqjob import IBMQJob
from qiskit.compiler import transpile


def run_rb(
    backend,
    shots,
    repeat: int,
    length_vector: List[int] = [1, 10, 20, 50, 75, 100, 125, 150, 175, 200],
    nseeds: int = 1,
):
    """
    Args:
        backend: Backend device you want to run

    The roll of `nseed` and `repeat` is same (rb_seeds).
    But in this function, `nseed` is used to create set of rb
    jobs of one target qubit(s).
    Instead of that, `repeat` is used to create set of jobs of whole
    sets of target qubits, and then repeat to create and send.
    e.g.
        `nseeds = n`
            _jobs_1 = [job_1-1, job_1-2, job_1-3, ..., job_1-n]
            ...
            _jobs_m = [job_m-1, job_m-2, job_m-3, ..., job_m-n]

            then,

            _jobssets = [_jobsr_1, ..., _jobs_m]


        `repeat = n`
            _jobsets_1 = [[job_1-1], [job_2-1], [job_3-1], ..., [job_m-1]]
            ...
            _jobsets_n = [[job_1-n], [job_2-n], [job_3-n], ..., [job_m-n]]

        In both cases, `job_i-j` object is `Tuple[IBMQJob, List[gpc]]`.
        `gpc` is gate per clifford represented as dict.
        `i` means number of patterns of target qubits.
        `j` means rb_seeds

        In general, the characteristics of hardware error is varing in time,
        so I prefer to use `nseeds = 1` and `repeat = n`, `n` is
        the rb_seeds you want to set in this case.
    """

    # prepare rb pattern based on backend device.

    # run simRB

    # run individual RB
    for i in range(repeat):
        _run_RB(
            backend,
            shots,
            length_vector,
            nseeds,
            rb_pattern,
        )

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
) -> List[Tuple[IBMQJob, List[dict]]]:
    """Function for Randomized Benchmarking"""
    rb_opts = {
        "length_vector": length_vector,
        "nseeds": nseeds,
        "rb_pattern": rb_pattern,
    }

    rb_circs, xdata = rb.randomized_benchmarking_seq(**rb_opts)
    basis_gates = backend.configuration().basis_gates
    rb_circs = [transpile(_rb_circ, basis_gates=basis_gates) for _rb_circ in rb_circs]

    gpcs = []
    # Calculate gate per clifford (gcp)
    for _rb_seq, _qubits in zip(xdata, rb_pattern):
        gates_per_cliff = rb.rb_utils.gates_per_clifford(
            rb_circs,
            clifford_lengths=_rb_seq,
            basis=basis_gates,
            qubits=_qubits,
        )
    gpcs.append(gates_per_cliff)

    jobs = []
    for rb_seed, rb_circ_i in enumerate(rb_circs):

        # run rb on backend
        _job = backend.run(
            circuits=rb_circ_i,
            shots=shots,
        )
        job = (_job, gpcs)
        jobs.append(job)

    return jobs


def _simRB(rb_pattern_set: List[List[List[int]]]):
    """Function for Simultaneous Randomized Benchmarking"""
    for rb_pattern in rb_pattern_set:
        pass
    return
