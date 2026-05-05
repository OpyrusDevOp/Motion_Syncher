import numpy as np


def dtw_distance(s: np.ndarray, t: np.ndarray) -> float:
    """
    DTW distance between two skeleton sequences, normalized by path length.

    s: (n, d)  t: (m, d)
    Returns a non-negative float; lower means more similar.
    """
    n, m = len(s), len(t)

    # Vectorized cost matrix: (n, m)
    cost = np.linalg.norm(s[:, None] - t[None, :], axis=2)

    acc = np.full((n + 1, m + 1), np.inf)
    acc[0, 0] = 0.0

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            acc[i, j] = cost[i - 1, j - 1] + min(
                acc[i - 1, j],
                acc[i, j - 1],
                acc[i - 1, j - 1],
            )

    return acc[n, m] / (n + m)
