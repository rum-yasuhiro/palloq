from benchmark import noisy_simulator

def test_noisy_simulator(): 
    xtalk_prop = {(0, 1): {(2, 3): 1.5}}
    sim = noisy_simulator(backend='toronto', xtalk_prop=xtalk_prop)

