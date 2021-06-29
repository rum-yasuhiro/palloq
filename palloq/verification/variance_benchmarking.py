from typing import Tuple, List, Dict, Union
from tqdm import tqdm

import qiskit.ignis.verification.randomized_benchmarking as rb
from qiskit.providers.ibmq.ibmqbackend import IBMQBackend
from qiskit.test.mock import FakeBackend
from qiskit.circuit import QuantumCircuit
from qiskit.pulse.schedule import Schedule
from qiskit.compiler import transpile, schedule


def prepare_rb(
    fake_backend: FakeBackend,
    repeat: int,
    rb_pattern_list: List[List[List[int]]],
    length_vector: List[int] = [1, 10, 20, 50, 75, 100, 125, 150, 175, 200],
    nseeds: int = 1,
    convert_pulse=False,
) -> List[List[Tuple[List[Union[Schedule, QuantumCircuit]], Dict[Tuple[int], dict]]]]:
    """The function for prepareing Randomized Benchmarking experiments

    Args:
        backend: IBMQBackend you want to run

    The role of `nseed` and `repeat` is same (rb_seeds).
    But in this function, `nseed` is used to create set of rb
    exp of one target qubit(s).
    Instead of that, `repeat` is used to create set of exps of whole
    sets of target qubits, and then repeat to create and send.
    e.g.
        `nseeds = n`
            _exps_1 = ([exp_1-1, exp_1-2, exp_1-3, ..., exp_1-n], gpc)
            ...
            _exps_m = ([exp_m-1, exp_m-2, exp_m-3, ..., exp_m-n], gpc)

            then,

            _expssets = [_expsr_1, ..., _exps_m]


        `repeat = n`
            _expsets_1 = [([exp_1-1], gpc), ([exp_2-1], gpc), ([exp_3-1], gpc), ..., ([exp_m-1], gpc)]
            ...
            _expsets_n = [([exp_1-n], gpc), ([exp_2-n], gpc), ([exp_3-n], gpc), ..., ([exp_m-n], gpc)]

        In both cases, `exp_i-j` object is `Tuple[Schedule, Dict[qubits, gpc]]`.
        `gpc` is gate per clifford represented as dict.
        `i` means number of patterns of target qubits.
        `j` means rb_seeds

        In general, the characteristics of hardware error is varing in time,
        so I prefer to use `nseeds = 1` and `repeat = n`, `n` is
        the rb_seeds you want to set in this case.
    """

    expsets_list = [[] for _ in range(repeat)]
    for rb_qubits in tqdm(rb_pattern_list):
        exp_tot = nseeds * repeat
        exp_list, epgs = _prepare_rb(
            fake_backend,
            length_vector,
            nseeds=exp_tot,
            rb_pattern=rb_qubits,
            convert_pulse=convert_pulse,
        )
        for i, _counter in enumerate(range(0, exp_tot, nseeds)):
            exps_i = (exp_list[_counter : _counter + nseeds], epgs)
            expsets_list[i].append(exps_i)

    return expsets_list


def _prepare_rb(
    fake_backend: FakeBackend,
    length_vector: List[int],
    nseeds: int,
    rb_pattern: List[List[int]],
    convert_pulse=False,
):
    rb_opts = {
        "length_vector": length_vector,
        "nseeds": nseeds,
        "rb_pattern": rb_pattern,
    }
    rb_circs, xdata = rb.randomized_benchmarking_seq(**rb_opts)
    basis_gates = fake_backend.configuration().basis_gates
    trb_circs = [transpile(_rb_circ, basis_gates=basis_gates) for _rb_circ in rb_circs]

    gpcs = {}
    # Calculate gate per clifford (gcp)
    for _rb_seq, _qubits in zip(xdata, rb_pattern):
        gates_per_clifford = rb.rb_utils.gates_per_clifford(
            trb_circs,
            clifford_lengths=_rb_seq,
            basis=basis_gates,
            qubits=_qubits,
        )
        _qubits = tuple(_qubits)
        gpcs[_qubits] = gates_per_clifford

    if convert_pulse:
        sched = [schedule(_trb_circs, backend=fake_backend) for _trb_circs in trb_circs]
        return sched, gpcs

    return trb_circs, gpcs


def run_rb(
    backend: IBMQBackend,
    shots: int,
    rb_exps: List[
        List[
            Tuple[
                List[Union[Schedule, QuantumCircuit]],
                Dict[Tuple[int], dict],
            ],
        ]
    ],
) -> List[List[Tuple[List[str], Dict[Tuple[int], dict]]]]:
    """Function for run Randomized Benchmarking on IBM Q Device

    Args:
        backend: IBMQBackend you want to run
        shots: number of trial of circuit
        rb_exps: RB circuits

    The role of `nseed` and `repeat` is same (rb_seeds).
    But in this function, `nseed` is used to create set of rb
    jobs of one target qubit(s).
    Instead of that, `repeat` is used to create set of jobs of whole
    sets of target qubits, and then repeat to create and send.
    e.g.
        `nseeds = n`
            _jobs_1 = ([job_1-1, job_1-2, job_1-3, ..., job_1-n], gpc)
            ...
            _jobs_m = ([job_m-1, job_m-2, job_m-3, ..., job_m-n], gpc)

            then,

            _jobssets = [_jobsr_1, ..., _jobs_m]


        `repeat = n`
            _jobsets_1 = [([job_1-1], gpc), ([job_2-1], gpc), ([job_3-1], gpc), ..., ([job_m-1], gpc)]
            ...
            _jobsets_n = [([job_1-n], gpc), ([job_2-n], gpc), ([job_3-n], gpc), ..., ([job_m-n], gpc)]

        In both cases, `job_i-j` object is `Tuple[IBMQJob, List[gpc]]`.
        `gpc` is gate per clifford represented as dict.
        `i` means number of patterns of target qubits.
        `j` means rb_seeds

        In general, the characteristics of hardware error is varing in time,
        so I prefer to use `nseeds = 1` and `repeat = n`, `n` is
        the rb_seeds you want to set in this case.
    """

    jobset_list = []
    for _repeat, _expset in tqdm(enumerate(rb_exps)):
        jobset = []
        for exps in tqdm(_expset):
            _exps, gpc = exps
            _jobs = []
            for _nseed, _exp in tqdm(enumerate(_exps)):
                # run rb on backend
                _job = backend.run(
                    circuits=_exp,
                    shots=shots,
                )
                jobid = _job.job_id()
                _jobs.append(jobid)
            jobs = (_jobs, gpc)
            jobset.append(jobs)
        jobset_list.append(jobset)

    return jobset_list


def calculate_rb(
    jobset_list: List[
        List[
            Tuple[
                List[str],
                Dict[Tuple[int], dict],
            ],
        ],
    ],
    backend: IBMQBackend,
):
    """
    Args:
        jobset_list: IBMQ job
    """

    return


def gen_rb_pattern(
    backend: Union[IBMQBackend, FakeBackend],
    num_set_qubits: int = 1,
) -> List[List[List[int]]]:

    if num_set_qubits == 1:
        num_qubits = num_qubits = backend.configuration().num_qubits
        pattern_set = [[[i]] for i in range(num_qubits)]
    else:
        """FIXME
        ２量子ビット以降も実装する
        """
        raise NotImplementedError("qubit_size = 1 以外はまだ実装されてない。")

    return pattern_set


def gen_simrb_pattern(
    backend: Union[IBMQBackend, FakeBackend],
    num_set_qubits: int = 1,
) -> List[List[List[int]]]:
    """
    Args:
        backend_name
    """

    if num_set_qubits == 1:
        num_qubits = backend.configuration().num_qubits
        pattern_set = [[[i] for i in range(num_qubits)]]
    else:
        """FIXME
        ２量子ビット以降はグラフ彩色問題として解く
        """
        raise NotImplementedError("qubit_size = 1 以外はまだ実装されてない。")

    return pattern_set


def path_to_jobfile(
    job_dir: str,
    backend_name: str,
    date,
    num_qubits: int,
):
    jobfile_path = (
        job_dir
        + "/"
        + str(date)
        + "_"
        + backend_name
        + "_"
        + str(num_qubits)
        + "qubit-gate_variance.pickle"
    )
    return jobfile_path


def path_to_resultfile(
    result_dir: str,
    backend_name: str,
    date,
    num_qubits: int,
):
    jobfile_path = (
        result_dir
        + "/"
        + str(date)
        + "_"
        + backend_name
        + "_"
        + str(num_qubits)
        + "qubit-gate_variance.pickle"
    )
    return jobfile_path
