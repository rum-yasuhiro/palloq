from typing import List, Optional, Tuple, Dict, Optional
import networkx as nx
from qiskit.compiler import transpile
import qiskit.ignis.verification.randomized_benchmarking as rb
from palloq.utils import get_IBMQ_backend, pickle_load, pickle_dump


def run_rb(
    backend_name,
    shots,
    nseeds=5,
    qubit_size: int = 2,
    jobfile_path=None,
    test_on_simulator=False,
    reservations=False,
):

    backend = get_IBMQ_backend(
        backend_name=backend_name,
        reservations=reservations,
    )
    coupling_map = backend.configuration().coupling_map
    basis_gates = backend.configuration().basis_gates

    if test_on_simulator:
        backend = get_IBMQ_backend(backend_name="ibmq_qasm_simulator")
    adj_couples = find_adjacent_couples(coupling_map=coupling_map)
    job_dict = _run_rb(
        backend=backend,
        twoQgate_pairs=adj_couples,
        rb_opts={
            "length_vector": [1, 10, 20, 50, 75, 100, 125, 150, 175, 200],
            "nseeds": nseeds,
        },
        basis_gates=basis_gates,
        shots=shots,
    )

    # save as pickle file
    if jobfile_path:
        pickle_dump(job_dict, jobfile_path)

    return job_dict


def _run_rb(
    backend,
    twoQgate_pairs: Dict[Tuple[int], List[Tuple[int]]],
    rb_opts: dict,
    basis_gates: Optional[List],
    shots: int = 8192,
) -> List[Dict[str, float]]:
    """
    Args:
        backend           : IBMQ backend device or simulator
        twoQgate_pairs    :
        rb_opts           : options for randomized banchmarking protocol as dict
            length_vector       : list of clifford length of each run
            nseeds              : random seeds
            rb_pattern          : combination of qubits
        basis_gates       : basis_gates list
        shots             : number of shots (by default 1024)

    Return:
        Error per gate

    """

    # return of this function
    job_dict = {}

    #################### rum each pairs of 2q gate ######################
    print("#################### Start make jobs ######################\n")
    for twoQconnection, pair_list in twoQgate_pairs.items():
        # start sigle rb
        print("############ start " + str(twoQconnection) + " ############")
        try:
            job_dict[twoQconnection] = job_dict[twoQconnection]
        except KeyError:
            job_dict[twoQconnection] = {}

        for pair in pair_list:
            try:
                job_dict[twoQconnection][pair] = job_dict[twoQconnection][pair]
            except KeyError:
                job_dict[twoQconnection][pair] = {}

            # make rb job
            if twoQconnection == pair:
                rb_opts["rb_pattern"] = [list(twoQconnection)]
                rb_pattern = [list(twoQconnection)]
            else:
                rb_opts["rb_pattern"] = [list(twoQconnection), list(pair)]
                rb_pattern = [list(twoQconnection), list(pair)]

            # define each randomized benchmarking circuit with clifford length
            print("####### start making the RB job " + str(rb_pattern) + " #######")
            rb_circs, xdata = rb.randomized_benchmarking_seq(**rb_opts)
            transpile_list_pairs = []
            for rb_seed, rb_circ_seed in enumerate(rb_circs):
                print("Compiling seed %d" % rb_seed)
                rb_circ_transpile = transpile(
                    rb_circ_seed,
                    basis_gates=basis_gates,
                )
                transpile_list_pairs.append(rb_circ_transpile)

            # Calculate gpc
            gates_per_cliff = rb.rb_utils.gates_per_clifford(
                transpile_list_pairs,
                xdata[0],
                basis_gates,
                qubits=list(twoQconnection),
            )

            # add the gpc to the dict
            job_dict[twoQconnection][pair]["gpc"] = gates_per_cliff

            # execute jobs
            print("###### start executing the job " + str(rb_pattern) + " #####")

            jobid_list = []
            for rb_seed, rb_circ_transpile in enumerate(transpile_list_pairs):
                print("Executing seed %d" % rb_seed)
                job = backend.run(
                    circuits=rb_circ_transpile,
                    shots=shots,
                )
                jobid_list.append(job.job_id())

            # add the list of job_id
            job_dict[twoQconnection][pair]["job_id"] = jobid_list

    return job_dict


def get_result(
    backend_name,
    jobfile_path,
    twoQgate_date=None,
    remove_list=None,
    provider=None,
    reservations=False,
):

    epc_dict, epg_dict = calculate_simrb(
        jobfile_path,
        backend_name=backend_name,
        provider=provider,
        rb_opts={
            "length_vector": [1, 10, 20, 50, 75, 100, 125, 150, 175, 200],
            "nseeds": 1,
        },
    )
    _save_base_xtalk(epc_dict, epg_dict, experiments_dir_name)


def find_adjacent_couples(coupling_map: List[List[int]]) -> dict:
    # reconstract processor topology as graph object
    coupling_map = [tuple(coup) for coup in coupling_map]
    g = nx.Graph()
    g.add_edges_from(coupling_map)

    adj_dict = {}
    for node_i in g.nodes():
        for node_j in nx.all_neighbors(g, node_i):
            if node_j > node_i:
                targ = (node_i, node_j)
                adj_dict[targ] = []

                # add itself
                adj_dict[targ].append(targ)

                # search lesser node adjacented
                for adj_i in nx.all_neighbors(g, node_i):
                    if adj_i != node_j:
                        for adj_j in nx.all_neighbors(g, adj_i):
                            if adj_j != node_i:
                                adj_coup = (
                                    min(
                                        adj_i,
                                        adj_j,
                                    ),
                                    max(
                                        adj_i,
                                        adj_j,
                                    ),
                                )
                                adj_dict[targ].append(adj_coup)

                # search greater node adjacented
                for adj_k in nx.all_neighbors(g, node_j):
                    if adj_k != node_i:
                        for adj_l in nx.all_neighbors(g, adj_k):
                            if adj_l != node_j:
                                adj_coup = (
                                    min(
                                        adj_k,
                                        adj_l,
                                    ),
                                    max(
                                        adj_k,
                                        adj_l,
                                    ),
                                )
                                adj_dict[targ].append(adj_coup)

    return adj_dict


def path_to_jobfile(job_dir: str, backend_name: str, date, num_qubits: int):
    jobfile_path = (
        job_dir
        + "/"
        + str(date)
        + "_"
        + backend_name
        + "_"
        + str(num_qubits)
        + "qubit-gate_1hop.pickle"
    )
    return jobfile_path
