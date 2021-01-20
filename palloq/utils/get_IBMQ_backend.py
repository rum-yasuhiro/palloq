from qiskit import IBMQ

def get_IBM_backend(backend_name, reservations=False): 
    
    IBMQ.load_account()
    if reservations:
        provider = IBMQ.get_provider(hub='ibm-q-utokyo', group='keio-internal', project='reservations')
    else: 
        provider = IBMQ.get_provider(hub='ibm-q-utokyo', group='keio-internal', project='keio-students')

    backend = provider.get_backend(backend_name)

    return backend