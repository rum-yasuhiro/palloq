from qiskit import transpile


def esp(circuit,
        error_rates,
        do_transpile=False):
    if transpile:
        circuit = transpile(circuit, basis_gates=["cx", "u3", "id"])
    # error definition check
    for op in circuit.count_ops().keys():
        if op not in error_rates and op not in ("measure", "barrier", "reset"):
            raise Exception(f"Error rate for {op} is not defined.")
    e = sum([error_rates.get(i, 0) * v for i, v in circuit.count_ops().items()])
    return 1 - e
