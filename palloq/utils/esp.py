from qiskit import transpile


def esp(circuit,
        error_rates,
        do_transpile=False):
    if transpile:
        circuit = transpile(circuit, basis_gates=["cx", "u2"])
    e = sum([error_rates.get[i] * v for i, v in circuit.count_ops().items()])
    return e
