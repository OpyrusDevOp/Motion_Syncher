import cv2
import numpy as np
from .base import Camera


class WebcamCamera(Camera):
    def __init__(self, index: int = 0):
        self._index = index
        self._cap: cv2.VideoCapture | None = None

    def open(self) -> None:
        self._cap = cv2.VideoCapture(self._index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open webcam {self._index}")

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self._cap is None or not self._cap.isOpened():
            return False, None
        ret, frame = self._cap.read()
        return ret, frame if ret else None

    def close(self) -> None:
        if self._cap:
            self._cap.release()
            self._cap = None

    @property
    def name(self) -> str:
        return f"Webcam {self._index}"
