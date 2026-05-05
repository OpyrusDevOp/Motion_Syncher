# Phase B: OAK camera support via DepthAI.
# Provides the same Camera interface; the rest of the pipeline is unchanged.

import numpy as np
from .base import Camera

try:
    import depthai as dai
    _DEPTHAI_AVAILABLE = True
except ImportError:
    _DEPTHAI_AVAILABLE = False


def is_available() -> bool:
    return _DEPTHAI_AVAILABLE


class OAKCamera(Camera):
    def __init__(self, mx_id: str | None = None):
        if not _DEPTHAI_AVAILABLE:
            raise RuntimeError(
                "depthai is not installed. Install it with: pip install depthai"
            )
        self._mx_id = mx_id
        self._device: "dai.Device | None" = None
        self._queue = None

    def open(self) -> None:
        pipeline = dai.Pipeline()

        cam = pipeline.create(dai.node.ColorCamera)
        cam.setPreviewSize(640, 480)
        cam.setInterleaved(False)
        cam.setColorOrder(dai.ColorCameraProperties.ColorOrder.RGB)
        cam.setFps(30)

        xout = pipeline.create(dai.node.XLinkOut)
        xout.setStreamName("rgb")
        cam.preview.link(xout.input)

        device_info = dai.DeviceInfo(self._mx_id) if self._mx_id else None
        self._device = dai.Device(pipeline, device_info) if device_info else dai.Device(pipeline)
        self._queue = self._device.getOutputQueue("rgb", maxSize=1, blocking=False)

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self._queue is None:
            return False, None
        pkt = self._queue.tryGet()
        if pkt is None:
            return False, None
        frame = pkt.getCvFrame()
        return True, frame

    def close(self) -> None:
        if self._device:
            self._device.close()
            self._device = None
            self._queue = None

    @property
    def name(self) -> str:
        return f"OAK {self._mx_id or 'default'}"
