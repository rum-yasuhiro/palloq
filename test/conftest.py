"""
This module povides quantum circuit style qasm bench for pytest
"""
# module path is pointing to palloq/palloc
import os
import pathlib
from typing import List
import pytest
import logging
from datetime import datetime

# import qiskit functions
from qiskit import QuantumCircuit
from qiskit.providers.models.backendproperties import BackendProperties, Nduv, Gate

_log = logging.getLogger(__name__)


def load_qasm(size: str):
    """
    This function loads qasm files

    Arguments:
        size: (str) circuit size (small, medium, large)
    """
    pos = os.path.abspath(os.path.dirname(__file__))
    test_files = str(pathlib.Path(pos).parent)
    QASM_BENCH = pathlib.Path(test_files + "/qasm_bench")
    if not QASM_BENCH.exists():
        raise Exception("Something wrong with path settings for test")

    if size == "small":
        small_path = QASM_BENCH.joinpath("small")
        return small_path
    elif size == "medium":
        medium_path = QASM_BENCH.joinpath("medium")
        return medium_path
    elif size == "large":
        large_path = QASM_BENCH.joinpath("large")
        return large_path
    else:
        raise ValueError("size must be small, medium or large")


def collect(path):
    # circuits = [qc.glob("*.qasm") for qc in path.iterdir()]
    circuits = [str(i) for qc in path.iterdir() for i in qc.glob("[a-z]*.qasm")]
    return circuits

# def change_register_name(qc):
#     """TODO"""
#     qregs = qc.qregs()
#     for _qreg 

@pytest.fixture(scope="session")
def small_circuits() -> list:
    """
    This function returns a list of small quantum circuits
    """
    path = load_qasm("small")
    circuits = []
    for qc_qasm in collect(path):
        try:
            qc = QuantumCircuit.from_qasm_file(qc_qasm)
            circuits.append(qc)
        except Exception:
            _log.warning(f"Parsing Qasm Failed at {qc_qasm}")
            continue
    return circuits


@pytest.fixture(scope="session")
def medium_circuits() -> list:
    """
    This function returns a list of medium quantum circuits
    """
    path = load_qasm("medium")
    circuits = []
    for qc_qasm in collect(path):
        try:
            qc = QuantumCircuit.from_qasm_file(qc_qasm)
            circuits.append(qc)
        except Exception:
            _log.warning(f"Parsing Qasm Failed at {qc_qasm}")
            continue
    return circuits


@pytest.fixture(scope="session")
def large_circuits() -> list:
    """
    This function returns a list of large quantum circuits
    """
    path = load_qasm("large")
    circuits = []
    for qc_qasm in collect(path):
        try:
            qc = QuantumCircuit.from_qasm_file(qc_qasm)
            circuits.append(qc)
        except Exception:
            _log.warning(f"Parsing Qasm Failed at {qc_qasm}")
            continue
    return circuits


# fixture with arguments for preparing mock backend
@pytest.fixture(scope="function")
def mock_backend_chain_topology(make_qubit_with_error):

    # nest function for receiving arguments
    def chained_backend(
        readout_errors: List[float],
        cx_errors: List[float],
    ):
        calib_time = datetime(year=2021, month=8, day=11, hour=0, minute=0, second=0)
        qubit_list = [
            make_qubit_with_error(ro_err, calib_time) for ro_err in readout_errors
        ]

        gate_list = []
        params = [
            [Nduv(date=calib_time, name="gate_error", unit="", value=cx_err)]
            for cx_err in cx_errors
        ]
        for i, param in enumerate(params):
            gate = Gate(
                name="CX" + str(i) + "_" + str(i + 1),
                gate="cx",
                parameters=param,
                qubits=[i, i + 1],
            )
            gate_list.append(gate)

        return BackendProperties(
            last_update_date=calib_time,
            backend_name="test_backend",
            qubits=qubit_list,
            backend_version="1.0.0",
            gates=gate_list,
            general=[],
        )

    return chained_backend


@pytest.fixture(scope="function")
def make_qubit_with_error():
    def qubit(readout_error, calib_time=None):
        """Create a qubit for BackendProperties"""
        if not calib_time:
            calib_time = datetime(
                year=2021, month=8, day=11, hour=0, minute=0, second=0
            )
        return [
            Nduv(name="T1", date=calib_time, unit="µs", value=100.0),
            Nduv(name="T2", date=calib_time, unit="µs", value=100.0),
            Nduv(name="frequency", date=calib_time, unit="GHz", value=5.0),
            Nduv(name="readout_error", date=calib_time, unit="", value=readout_error),
        ]

    return qubit
