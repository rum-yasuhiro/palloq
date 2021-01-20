# 1. get result
# 2. js, norm,  fidelity, evaluate

# Jensen-Shannonダイバージェンス
import numpy as np
from typing import Union, List
from scipy.stats import norm, entropy


def js_divergence(self,
                  answer: Union[List, np.ndarray],
                  answer2: Union[List, np.ndarray]):
    """
    Arguments:
        answer: (list, array) Probability distribution
        answer2: (list, array) Probability distribution
    """
    ans_rate = np.array(answer)
    ans_rate2 = np.array(answer2)
    
    slf_ent_1 = sum(-1 * (ans_rate * np.log(ans_rate) + (1 - ans_rate2) * np.log(1 - ans_rate2)))
    slf_ent_2 = sum(-1 * (ans_rate2 * np.log(ans_rate2) + (1 - ans_rate) * np.log(1 - ans_rate)))
    crs_ent_1 = sum(-1 * (ans_rate * np.log(ans_rate2) + (1 - ans_rate2) * np.log(1 - ans_rate)))
    crs_ent_2 = sum(-1 * (ans_rate2 * np.log(ans_rate) + (1 - ans_rate) * np.log(1 - ans_rate2)))

    kld_1 = crs_ent_1 - slf_ent_1
    kld_2 = crs_ent_2 - slf_ent_2

    jsd = (kld_1 + kld_2) / 2
    
    return jsd


def calculate_jsd(self, results):
    """
    1. get computational result
    2. calculate jsd

    Argument:
        result: (list(dict)) [{'00':100, '11': 100},
                              {'00': 200, '11': 0}]
    """
    if len(results) != 2:
        raise Exception("The size of result must be two.")

    # 1. calculate probability distribution
    prob1, prob2 = results

    # 00, 01, 10, 11 
    base = len(next(iter(prob1)))
    base2 = len(next(iter(prob2)))

    if base != base2:
        raise Exception("The sizes of two binaries are different.")

    # binary = ['00', '01', '10', '11']
    binary = [format(i, '0%db' % base) for i in range(2**base)]

    prob_dist1 = np.array([])
    prob_dist2 = np.array([])
    # take results according to binary table
    shots1 = sum(prob1.values())  # ex. 200
    shots2 = sum(prob2.values())  # ex. 200

    for b in binary:
        np.append(prob_dist1, prob1.get(b, 0) / shots1)
        np.append(prob_dist2, prob2.get(b, 0) / shots2)

    jsd = js_divergence(prob_dist1, prob_dist2)
    return jsd