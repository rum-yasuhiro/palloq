from qiskit.test.mock import *

def choose_fakebackend(name): 
    fake_backend = None

    if name == 'armonk' or name == 'ibmq_armonk': 
        fake_backend = FakeArmonk()
    elif name == 'yorktown' or name == 'ibmq_yorktown': 
        fake_backend = FakeYorktown()
    elif name == 'tenerife' or name == 'ibmq_tenerife': 
        fake_backend = FakeTenerife()
    elif name == 'ourense' or name == 'ibmq_ourense': 
        fake_backend = FakeOurense()
    elif name == 'vigo' or name == 'ibmq_vigo': 
        fake_backend = FakeVigo()
    elif name == 'valencia' or name == 'ibmq_valencia': 
        fake_backend = FakeValencia()
    elif name == 'london' or name == 'ibmq_london': 
        fake_backend = FakeLondon()
    elif name == 'essex' or name == 'ibmq_essex': 
        fake_backend = FakeEssex()
    elif name == 'burlington' or name == 'ibmq_burlington': 
        fake_backend = FakeBurlington()
    elif name == 'melbourne' or name == 'ibmq_melbourne': 
        fake_backend = FakeMelbourne()
    elif name == 'paris' or name == 'ibmq_paris': 
        fake_backend = FakeParis()
    elif name == 'toronto' or name == 'ibmq_toronto': 
        fake_backend = FakeToronto()
    elif name == 'manhattan' or name == 'ibmq_manhattan': 
        fake_backend = FakeManhattan()
    else: 
        raise ChooseFakeBackendError("Doesn't support that fake backend") 
    
    return fake_backend

class ChooseFakeBackendError(Exception): 
    pass