# 1. get result
# 2. js, norm,  fidelity, evaluate

# Jensen-Shannonダイバージェンス
import numpy as np
from scipy.stats import norm, entropy

def js_divergence(self,
                  shots: int
                  answer: dict
                  answer2: dict):
    
    ans_rate = answer / shots
    ans_rate2 = answer2 / shots
    
    slf_ent_1 = sum(-1 * (ans_rate * np.log(ans_rate) + (1 - ans_rate2) * np.log(1 - ans_rate2)))
    slf_ent_2 = sum(-1 * (ans_rate2 * np.log(ans_rate2) + (1 - ans_rate) * np.log(1 - ans_rate)))
    crs_ent_1 = sum(-1 * (ans_rate * np.log(ans_rate2) + (1 - ans_rate2) * np.log(1 - ans_rate)))
    crs_ent_2 = sum(-1 * (ans_rate2 * np.log(ans_rate) + (1 - ans_rate) * np.log(1 - ans_rate2)))

    kld_1 = crs_ent_1 - slf_ent_1
    kld_2 = crs_ent_2 - slf_ent_2

    jsd = (kld_1 + kld_2) / 2
    
    return jsd