"""
This module povides quantum circuit style qasm bench for pytest
"""
# module path is pointing to palloq/palloc
import os
import pathlib
import pytest
import logging

from qiskit import QuantumCircuit

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
    circuits = [str(i) for qc in path.iterdir() 
                for i in qc.glob("[a-z]*.qasm")]
    return circuits


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
