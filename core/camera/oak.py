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


def list_devices() -> list[dict]:
    """
    Return a list of available OAK devices as dicts:
        {"mx_id": str, "label": str, "state": str}
    Returns an empty list if depthai is not installed or no device is found.
    """
    if not _DEPTHAI_AVAILABLE:
        return []
    try:
        found = []
        for dev_info in dai.Device.getAllAvailableDevices():
            mx_id = dev_info.getDeviceId()
            name = dev_info.name  # IP address or USB path
            state = str(dev_info.state).split(".")[-1]  # e.g. "UNBOOTED"
            found.append(
                {
                    "mx_id": mx_id,
                    "label": f"OAK {mx_id[-6:]} ({name})",
                    "state": state,
                }
            )
        return found
    except Exception as exc:
        print(f"[OAKCamera] device enumeration failed: {exc}")
        return []


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
        # Create the device once (here with USB speed constraint)
        device = dai.Device(maxUsbSpeed=dai.UsbSpeed.HIGH)

        # Create a pipeline bound to that device
        with dai.Pipeline(device) as self._pipeline:
            cam = self._pipeline.create(dai.node.Camera).build()

            cameraOutput = cam.requestOutput(
                (1280, 720),
                type=dai.ImgFrame.Type.NV12,
                fps=30,
            )

        # Store your queue
        self._queue = cameraOutput.createOutputQueue()

        # If you need to store the device, store this one
        self._device = device

        # Start the pipeline and begin using the queue
        self._pipeline.start()

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
            self._pipeline.stop()
            self._device.close()
            self._device = None
            self._queue = None

    @property
    def name(self) -> str:
        return f"OAK {self._mx_id[-6:] if self._mx_id else 'default'}"
