import numpy as np

# COCO keypoint indices (YOLO-pose output)
_NOSE       = 0
_L_SHOULDER = 5
_R_SHOULDER = 6
_L_ELBOW    = 7
_R_ELBOW    = 8
_L_WRIST    = 9
_R_WRIST    = 10
_L_HIP      = 11
_R_HIP      = 12

# 9 upper-body joints × 2D = 18-dim feature vector per frame
_JOINTS = [
    _NOSE,
    _L_SHOULDER, _R_SHOULDER,
    _L_ELBOW,    _R_ELBOW,
    _L_WRIST,    _R_WRIST,
    _L_HIP,      _R_HIP,
]

FEATURE_DIM = len(_JOINTS) * 2  # 18


def normalize(landmarks: list[tuple[float, float, float]]) -> np.ndarray | None:
    """
    Hip-centered, shoulder-width-scaled 2D feature vector.
    Returns float32 array of shape (FEATURE_DIM,), or None if scale is degenerate.
    """
    l_hip      = np.array(landmarks[_L_HIP][:2])
    r_hip      = np.array(landmarks[_R_HIP][:2])
    l_shoulder = np.array(landmarks[_L_SHOULDER][:2])
    r_shoulder = np.array(landmarks[_R_SHOULDER][:2])

    center = (l_hip + r_hip) / 2.0
    scale  = float(np.linalg.norm(l_shoulder - r_shoulder))
    if scale < 1e-6:
        return None

    features: list[float] = []
    for j in _JOINTS:
        xy     = np.array(landmarks[j][:2])
        normed = (xy - center) / scale
        features.extend(normed.tolist())

    return np.array(features, dtype=np.float32)
