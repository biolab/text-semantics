import numpy as np


def cos_sim(x: np.ndarray, y: np.ndarray) -> float:
    if x.sum() == 0 or y.sum() == 0:
        return 0
    return x.dot(y) / np.linalg.norm(x) / np.linalg.norm(y)