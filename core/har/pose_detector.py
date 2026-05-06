import numpy as np
from dataclasses import dataclass

# COCO 17-keypoint layout (used by YOLO-pose):
#  0 nose | 1 l_eye | 2 r_eye | 3 l_ear | 4 r_ear
#  5 l_shoulder | 6 r_shoulder | 7 l_elbow | 8 r_elbow
#  9 l_wrist | 10 r_wrist | 11 l_hip | 12 r_hip
# 13 l_knee | 14 r_knee | 15 l_ankle | 16 r_ankle


@dataclass
class PoseResult:
    # 17 landmarks: (x_norm, y_norm, confidence)
    landmarks: list[tuple[float, float, float]]


def _auto_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


class PoseDetector:
    def __init__(
        self,
        model: str = "yolov8n-pose.pt",
        conf: float = 0.45,
        device: str | None = None,
        imgsz: int = 320,
    ):
        from ultralytics import YOLO
        self._device = device or _auto_device()
        self._model = YOLO(model)
        self._conf = conf
        self.imgsz = imgsz   # mutable — updated live from GUI

    @property
    def device(self) -> str:
        return self._device

    def detect(self, frame: np.ndarray) -> tuple[PoseResult | None, np.ndarray]:
        """Returns (pose_result_or_None, annotated_frame)."""
        results = self._model(
            frame, verbose=False, conf=self._conf,
            device=self._device, imgsz=self.imgsz,
        )
        annotated = results[0].plot()

        kps = results[0].keypoints
        if kps is None or len(kps.xyn) == 0:
            return None, annotated

        # Pick the person with highest box confidence (first in YOLO output)
        xy = kps.xyn[0].cpu().numpy()        # (17, 2) — normalized [0,1]
        conf_vals = (
            kps.conf[0].cpu().numpy()
            if kps.conf is not None
            else np.ones(17, dtype=np.float32)
        )

        landmarks = [
            (float(xy[i, 0]), float(xy[i, 1]), float(conf_vals[i]))
            for i in range(17)
        ]
        return PoseResult(landmarks), annotated

    def close(self) -> None:
        pass
