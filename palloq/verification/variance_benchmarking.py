from typing import Tuple, List, Dict, Union

from pandas.core.frame import DataFrame
from tqdm import tqdm
import pandas as pd
import seaborn as sns

from pprint import pprint

# import qiskit tools
import qiskit.ignis.verification.randomized_benchmarking as rb
from qiskit.ignis.verification import calculate_1q_epg, calculate_2q_epg
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
        exp_list, epgs, xdata, rb_pattern = _prepare_rb(
            fake_backend,
            length_vector,
            nseeds=exp_tot,
            rb_pattern=rb_qubits,
            convert_pulse=convert_pulse,
        )
        for i, _counter in enumerate(range(0, exp_tot, nseeds)):
            exps_i = (exp_list[_counter : _counter + nseeds], epgs, xdata, rb_pattern)
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

    gpcs = {}
    trb_circs = [
        transpile(_rb_circ, basis_gates=["id", "u1", "u2", "u3", "cx"])
        for _rb_circ in rb_circs
    ]
    # Calculate gate per clifford (gpc)
    for _rb_seq, _qubits in zip(xdata, rb_pattern):
        gates_per_clifford = rb.rb_utils.gates_per_clifford(
            trb_circs,
            clifford_lengths=_rb_seq,
            basis=["id", "u1", "u2", "u3", "cx"],
            qubits=_qubits,
        )
        _qubits = tuple(_qubits)
        gpcs[_qubits] = gates_per_clifford

    if convert_pulse:
        sched = [schedule(_trb_circs, backend=fake_backend) for _trb_circs in trb_circs]
        return sched, gpcs

    basis_gates = fake_backend.configuration().basis_gates
    runnable_circs = [
        transpile(_rb_circ, basis_gates=basis_gates) for _rb_circ in rb_circs
    ]

    return runnable_circs, gpcs, xdata, rb_pattern


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
            _exps, gpcs, xdata, rb_pattern = exps
            _jobs = []
            for _nseed, _exp in tqdm(enumerate(_exps)):
                # run rb on backend
                _job = backend.run(
                    circuits=_exp,
                    shots=shots,
                )
                jobid = _job.job_id()
                _jobs.append(jobid)
            jobs = (_jobs, gpcs, xdata, rb_pattern)
            jobset.append(jobs)
        jobset_list.append(jobset)

    return jobset_list


def calculate_rbfit(
    jobset_list: List[
        List[
            Tuple[
                List[str],
                Dict[Tuple[int], dict],
                list,
                list,
            ],
        ],
    ],
    backend: IBMQBackend,
) -> DataFrame:
    """
    Args:
        jobset_list: List[ <-- repeat
            List[ <-- each experiments
                Tuple[
                    List[str], <-- list of job_id (str) for nseed
                    Dict[Tuple[int], dict], <-- gpcs
                ],
            ],
        ],
        rb_type: RB or SimRB
    """
    # list for fit object for each rb patterns
    fitobjs = []
    for _repeat, jobset in tqdm(enumerate(jobset_list)):
        for ex_i, jobinfo in tqdm(enumerate(jobset)):
            jobids, gpcs, xdata, rb_pattern = jobinfo  # unpack
            if _repeat == 0:
                # create fit object for each rb patterns at the very first time of repetition
                rbfit = rb.fitters.RBFitter(None, xdata, rb_pattern)
                fitobjs.append((rbfit, gpcs))
            for nseed, jobid in enumerate(jobids):  # by default nseed = 1
                try: 
                    result = backend.retrieve_job(jobid).result()
                except:
                    print("Job %s is faild" % jobid)
                    continue
                # add sample data to every fit object to repeatedly
                fitobjs[ex_i][0].add_data(result)  # fitobjs[ex_i][1] is rb_pattern
    return fitobjs


def fitobj_to_df(
    fitobjs,
    backend_name,
    rb_type="RB",
):
    # Data frame for saving epg of physical qubits.
    df = pd.DataFrame(
        columns=["Qubit", "EPG", "EPC", "Backend", "RB Type"],
        dtype=float,
    )
    for rbfit, gpcs in fitobjs:
        """
        RBFitter.fit is list of fit result of each component of rb_pattern
        self._fit[patt_ind] = {'params': params, 'params_err': params_err,
                               'epc': epc, 'epc_err': epc_err}
        """
        # calculate error per gate for every qubits in rb_pattern
        for idx, gpc_info in enumerate(gpcs.items()):
            qubits, gpc = gpc_info
            try:
                epc = rbfit.fit[idx]["epc"]
            except:
                print("Fitter object number %d is empty." % idx)
                continue
            if len(qubits) == 1:
                epg = calculate_1q_epg(
                    gate_per_cliff=gpc,
                    epc_1q=epc,
                    qubit=qubits[0],
                )["u2"]
                q_label = str(qubits[0])

            elif len(qubits) == 2:
                epg = calculate_2q_epg(
                    gate_per_cliff=gpc,
                    epc_2q=epc,
                    qubit_pair=list(qubits),
                    two_qubit_name="cx",
                )
                q0 = min(qubits[0], qubits[1])
                q1 = max(qubits[0], qubits[1])
                q_label = str((q0, q1))
            df = df.append(
                {
                    "Qubit": q_label,
                    "EPG": epg,
                    "EPC": epc,
                    "Backend": backend_name,
                    "RB Type": rb_type,
                },
                ignore_index=True,
            )
    return df


def plot_swam(df: DataFrame, save_path):
    sns.set_theme(style="whitegrid", palette="muted")

    # Plot distribution of error rates
    sns_plot = sns.swarmplot(
        data=df,
        x="Backend",
        y="EPG",
        hue="RB Type",
        dodge=True,
    )
    sns_plot.set(xlabel="", ylabel="Error rates")
    fig = sns_plot.get_figure()
    fig.savefig(save_path)


def gen_rb_pattern(
    backend: Union[IBMQBackend, FakeBackend],
    num_set_qubits: int = 1,
) -> List[List[List[int]]]:

    if num_set_qubits == 1:
        num_qubits = num_qubits = backend.configuration().num_qubits
        pattern_set = [[[i]] for i in range(num_qubits)]
    else:
        coupling_map = backend.configuration().coupling_map
        pattern_set = [[coup] for coup in coupling_map if coup[0]<coup[1]]

    return pattern_set


def gen_simrb_pattern(
    backend: Union[IBMQBackend, FakeBackend],
    num_set_qubits: int,
    rb_pattern: List[List[List[int]]],
) -> List[List[List[int]]]:
    """
    Args:
        backend_name
    """

    if num_set_qubits == 1:
        num_qubits = backend.configuration().num_qubits
        pattern_set = [[[i] for i in range(num_qubits)]]
    else:
        raise NotImplementedError("simRB pattern for more than 2 qubits is not implemented yet.")

    return pattern_set


def path_to_rbexperiments(
    job_dir: str,
    backend_name: str,
    date,
    num_qubits: int,
):
    expfile_path = (
        job_dir
        + "/rb_experiments/"
        + str(date)
        + "_"
        + backend_name
        + "_"
        + str(num_qubits)
        + "qubit-gate_variance.pickle"
    )
    return expfile_path


def path_to_jobfile(
    job_dir: str,
    backend_name: str,
    date,
    num_qubits: int,
):
    jobfile_path = (
        job_dir
        + "/jobfile/"
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
    csv_path = (
        result_dir
        + "/results/"
        + str(date)
        + "_"
        + backend_name
        + "_"
        + str(num_qubits)
        + "qubit-gate_variance.pickle"
    )
    return csv_path


def path_to_csvfile(
    result_dir: str,
    backend_name: str,
    date,
    num_qubits: int,
):
    csv_path = (
        result_dir
        + "/csv/"
        + str(date)
        + "_"
        + backend_name
        + "_"
        + str(num_qubits)
        + "qubit-gate_variance.csv"
    )
    return csv_path


def path_to_figure(
    result_dir: str,
    backend_name: str,
    date,
    num_qubits: int,
):
    figfile_path = (
        result_dir
        + "/plot/"
        + str(date)
        + "_"
        + backend_name
        + "_"
        + str(num_qubits)
        + "qubit-gate_variance.png"
    )
    return figfile_path
