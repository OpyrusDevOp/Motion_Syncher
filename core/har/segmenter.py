import numpy as np


class MotionSegmenter:
    """
    Detects gesture segments using motion energy (mean absolute frame-to-frame change).

    A gesture is a contiguous active window (energy > quiet_threshold) that is at
    least min_gesture_frames long and followed by quiet_frames_to_end quiet frames.
    """

    def __init__(
        self,
        quiet_threshold: float = 0.02,
        min_gesture_frames: int = 15,
        max_gesture_frames: int = 90,
        quiet_frames_to_end: int = 10,
    ):
        self.quiet_threshold = quiet_threshold
        self.min_gesture_frames = min_gesture_frames
        self.max_gesture_frames = max_gesture_frames
        self.quiet_frames_to_end = quiet_frames_to_end

        self.last_energy: float = 0.0

        self._buffer: list[np.ndarray] = []
        self._prev: np.ndarray | None = None
        self._quiet_count: int = 0
        self._in_gesture: bool = False

    def reset(self) -> None:
        self._buffer.clear()
        self._prev = None
        self._quiet_count = 0
        self._in_gesture = False
        self.last_energy = 0.0

    def update(self, features: np.ndarray | None) -> np.ndarray | None:
        """
        Feed one frame. Returns a completed gesture sequence (shape: [n, FEATURE_DIM])
        when one is detected, otherwise None.
        """
        if features is None:
            if self._in_gesture:
                self._quiet_count += 1
                if self._quiet_count >= self.quiet_frames_to_end:
                    self.reset()
            return None

        if self._prev is None:
            self.last_energy = 0.0
        else:
            self.last_energy = float(np.mean(np.abs(features - self._prev)))
        self._prev = features.copy()

        moving = self.last_energy > self.quiet_threshold

        if moving:
            self._quiet_count = 0
            if not self._in_gesture:
                self._in_gesture = True
                self._buffer.clear()
            self._buffer.append(features.copy())

            if len(self._buffer) > self.max_gesture_frames:
                self.reset()
        else:
            if self._in_gesture:
                self._quiet_count += 1
                self._buffer.append(features.copy())

                if self._quiet_count >= self.quiet_frames_to_end:
                    active_len = len(self._buffer) - self.quiet_frames_to_end
                    if active_len >= self.min_gesture_frames:
                        sequence = np.array(self._buffer[:active_len])
                    else:
                        sequence = None
                    self.reset()
                    return sequence

        return None
