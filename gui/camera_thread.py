import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from core.camera.base import Camera
from core.har.pose_detector import PoseDetector
from core.har.normalizer import normalize
from core.har.segmenter import MotionSegmenter
from core.har.gesture_recognizer import GestureRecognizer


class CameraThread(QThread):
    frame_ready = Signal(QImage)
    gesture_detected = Signal(str, float)   # name, dtw_distance  (matched)
    segment_analyzed = Signal(str, float)   # best_name, best_distance  (every segment)
    motion_energy_updated = Signal(float)
    recording_complete = Signal(object)     # np.ndarray of shape (n, FEATURE_DIM)
    recording_failed = Signal(str)          # reason

    def __init__(self, parent=None):
        super().__init__(parent)
        self._camera: Camera | None = None
        self._pose = PoseDetector()
        self._segmenter = MotionSegmenter()
        self._recognizer = GestureRecognizer()
        self._running = False
        self._recording = False
        self._record_name = ""

    # ------------------------------------------------------------------
    # Public API (called from the main thread)
    # ------------------------------------------------------------------

    def set_camera(self, camera: Camera) -> None:
        self._camera = camera

    @property
    def recognizer(self) -> GestureRecognizer:
        return self._recognizer

    @property
    def segmenter(self) -> MotionSegmenter:
        return self._segmenter

    def start_recording(self, name: str) -> None:
        self._record_name = name
        self._segmenter.reset()
        self._recording = True

    def cancel_recording(self) -> None:
        self._recording = False
        self._record_name = ""

    def stop(self) -> None:
        self._running = False
        self.wait()

    # ------------------------------------------------------------------
    # Thread body
    # ------------------------------------------------------------------

    def run(self) -> None:
        if self._camera is None:
            return
        try:
            self._camera.open()
        except Exception as exc:
            self.recording_failed.emit(str(exc))
            return

        self._running = True

        while self._running:
            ret, frame = self._camera.read()
            if not ret or frame is None:
                self.msleep(5)
                continue

            pose_result, annotated = self._pose.detect(frame)
            features = normalize(pose_result.landmarks) if pose_result else None

            segment = self._segmenter.update(features)

            self.motion_energy_updated.emit(self._segmenter.last_energy)

            if segment is not None:
                if self._recording:
                    self._recognizer.add_template(self._record_name, segment)
                    self.recording_complete.emit(segment)
                    self._recording = False
                else:
                    name, dist = self._recognizer.recognize(segment)
                    # Always report so the UI can show distance for calibration
                    self.segment_analyzed.emit(name or "", dist)
                    if name:
                        self.gesture_detected.emit(name, dist)

            # Emit annotated frame to GUI
            rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            img = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format.Format_RGB888)
            self.frame_ready.emit(img.copy())

        self._camera.close()
        self._pose.close()
