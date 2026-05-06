import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLineEdit, QLabel, QGroupBox, QFormLayout, QDoubleSpinBox,
    QSpinBox, QComboBox,
)
from PySide6.QtCore import Signal, Qt, QTimer

from gui.camera_thread import CameraThread

_USER_ROLE = Qt.ItemDataRole.UserRole


class ActionLibraryWidget(QWidget):
    gesture_list_changed = Signal()
    reload_requested = Signal()

    def __init__(self, camera_thread: CameraThread, parent=None):
        super().__init__(parent)
        self._ct = camera_thread

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QHBoxLayout()
        header.addWidget(QLabel("<b>Gesture Library</b>"))
        header.addStretch()
        self.reload_btn = QPushButton("⟳")
        self.reload_btn.setFixedWidth(28)
        self.reload_btn.setToolTip("Reload gestures from disk")
        self.reload_btn.clicked.connect(self.reload_requested.emit)
        header.addWidget(self.reload_btn)
        layout.addLayout(header)

        self.gesture_list = QListWidget()
        self.gesture_list.setAlternatingRowColors(True)
        layout.addWidget(self.gesture_list)

        # --- Record controls ---
        rec_box = QGroupBox("Record New Gesture")
        rec_layout = QVBoxLayout(rec_box)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Gesture name…")
        rec_layout.addWidget(self.name_input)

        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("Delay before recording:"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 10)
        self.delay_spin.setSuffix(" s")
        self.delay_spin.setValue(0)
        self.delay_spin.setFixedWidth(64)
        delay_row.addWidget(self.delay_spin)
        delay_row.addStretch()
        rec_layout.addLayout(delay_row)

        btn_row = QHBoxLayout()
        self.record_btn = QPushButton("⏺  Record")
        self.add_take_btn = QPushButton("+ Add Take")
        self.delete_btn = QPushButton("Delete")
        for b in (self.record_btn, self.add_take_btn, self.delete_btn):
            btn_row.addWidget(b)
        rec_layout.addLayout(btn_row)

        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet("color: gray;")
        rec_layout.addWidget(self.status_lbl)

        layout.addWidget(rec_box)

        # --- Recognition settings ---
        cfg_box = QGroupBox("Recognition Settings")
        cfg_form = QFormLayout(cfg_box)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.001, 5.0)
        self.threshold_spin.setSingleStep(0.005)
        self.threshold_spin.setDecimals(3)
        self.threshold_spin.setValue(0.30)
        cfg_form.addRow("DTW Threshold:", self.threshold_spin)

        self.cooldown_spin = QDoubleSpinBox()
        self.cooldown_spin.setRange(0.1, 30.0)
        self.cooldown_spin.setSingleStep(0.1)
        self.cooldown_spin.setValue(1.5)
        cfg_form.addRow("Cooldown (s):", self.cooldown_spin)

        self.motion_spin = QDoubleSpinBox()
        self.motion_spin.setRange(0.001, 0.5)
        self.motion_spin.setSingleStep(0.001)
        self.motion_spin.setDecimals(3)
        self.motion_spin.setValue(0.02)
        cfg_form.addRow("Motion Threshold:", self.motion_spin)

        layout.addWidget(cfg_box)

        # --- Performance settings ---
        perf_box = QGroupBox("Performance")
        perf_form = QFormLayout(perf_box)

        self.skip_spin = QSpinBox()
        self.skip_spin.setRange(1, 6)
        self.skip_spin.setValue(2)
        self.skip_spin.setToolTip(
            "Run YOLO every N frames. 1 = every frame (max CPU). "
            "2–3 = good balance. Higher = less CPU, less responsive skeleton."
        )
        perf_form.addRow("Frame skip:", self.skip_spin)

        self.imgsz_combo = QComboBox()
        for size in (192, 256, 320, 416, 640):
            self.imgsz_combo.addItem(f"{size} px", userData=size)
        self.imgsz_combo.setCurrentIndex(2)   # 320 default
        self.imgsz_combo.setToolTip(
            "YOLO inference resolution. Smaller = much less CPU/GPU, "
            "slightly lower pose accuracy."
        )
        perf_form.addRow("Inference size:", self.imgsz_combo)

        from core.har.pose_detector import _detect_device
        _dev, _dev_status = _detect_device()
        device_lbl = QLabel(_dev_status)
        if _dev == "cuda":
            color = "#27ae60"   # green — GPU active
        elif "ROCm" in _dev_status:
            color = "#e74c3c"   # red — ROCm present but unusable
        else:
            color = "#e67e22"   # orange — plain CPU
        device_lbl.setStyleSheet(f"color: {color};")
        device_lbl.setWordWrap(True)
        perf_form.addRow("Compute device:", device_lbl)

        layout.addWidget(perf_box)

        # --- Last segment diagnostic ---
        self.segment_lbl = QLabel("Last segment: —")
        self.segment_lbl.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.segment_lbl)

        # --- Connections ---
        self.record_btn.clicked.connect(self._start_recording)
        self.add_take_btn.clicked.connect(self._add_take)
        self.delete_btn.clicked.connect(self._delete_gesture)
        self.threshold_spin.valueChanged.connect(self._apply_settings)
        self.cooldown_spin.valueChanged.connect(self._apply_settings)
        self.motion_spin.valueChanged.connect(self._apply_settings)
        self.skip_spin.valueChanged.connect(self._apply_perf_settings)
        self.imgsz_combo.currentIndexChanged.connect(self._apply_perf_settings)

        camera_thread.recording_complete.connect(self._on_recording_complete)
        camera_thread.recording_failed.connect(
            lambda msg: self._set_status(f"Error: {msg}", "red")
        )
        camera_thread.segment_analyzed.connect(self._on_segment_analyzed)

        self._pending_name: str = ""
        self._last_recorded_name: str = ""
        self._countdown_left: int = 0
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._tick_countdown)

        self._refresh_list()

    # ------------------------------------------------------------------

    def _start_recording(self):
        name = self.name_input.text().strip()
        if not name:
            self._set_status("Enter a gesture name first.", "red")
            return
        self._begin_with_delay(name)

    def _add_take(self):
        item = self.gesture_list.currentItem()
        if item is None:
            self._set_status("Select a gesture first.", "red")
            return
        self._begin_with_delay(item.data(_USER_ROLE))

    def _begin_with_delay(self, name: str) -> None:
        self._pending_name = name
        delay = self.delay_spin.value()
        if delay > 0:
            self._countdown_left = delay
            self._set_status(f"Starting in {delay}s…", "#e67e22")
            self._countdown_timer.start()
        else:
            self._fire_recording()

    def _tick_countdown(self) -> None:
        self._countdown_left -= 1
        if self._countdown_left > 0:
            self._set_status(f"Starting in {self._countdown_left}s…", "#e67e22")
        else:
            self._countdown_timer.stop()
            self._fire_recording()

    def _fire_recording(self) -> None:
        name = self._pending_name
        self._last_recorded_name = name
        self._ct.start_recording(name)
        self._set_status(f"Recording '{name}' — perform the gesture…", "orange")

    def _delete_gesture(self):
        item = self.gesture_list.currentItem()
        if item is None:
            return
        name = item.data(_USER_ROLE)
        self._ct.recognizer.remove_template(name)
        self._refresh_list()
        self.gesture_list_changed.emit()

    def _on_recording_complete(self, sequence: object):
        seq: np.ndarray = sequence  # type: ignore[assignment]
        self._set_status(f"Saved! ({len(seq)} frames)", "green")
        self._refresh_list()
        self._reselect(self._last_recorded_name)
        self.gesture_list_changed.emit()

    def _reselect(self, name: str) -> None:
        for i in range(self.gesture_list.count()):
            item = self.gesture_list.item(i)
            if item.data(_USER_ROLE) == name:
                self.gesture_list.setCurrentItem(item)
                return

    def _refresh_list(self):
        self.gesture_list.clear()
        for name in self._ct.recognizer.list_gestures():
            count = self._ct.recognizer.get_template_count(name)
            item = QListWidgetItem(f"{name}  ({count} take{'s' if count != 1 else ''})")
            item.setData(_USER_ROLE, name)
            self.gesture_list.addItem(item)

    def _apply_settings(self):
        self._ct.recognizer.threshold = self.threshold_spin.value()
        self._ct.recognizer.cooldown_seconds = self.cooldown_spin.value()
        self._ct.segmenter.quiet_threshold = self.motion_spin.value()

    def _apply_perf_settings(self):
        self._ct.skip_frames = self.skip_spin.value()
        self._ct.imgsz = self.imgsz_combo.currentData()

    def _on_segment_analyzed(self, best_name: str, best_dist: float) -> None:
        thr = self._ct.recognizer.threshold
        if best_dist == float("inf"):
            self.segment_lbl.setText("Last segment: no templates")
            self.segment_lbl.setStyleSheet("color: gray; font-size: 11px;")
            return
        label = best_name if best_name else "no match"
        text = f"Last segment: {label}  d={best_dist:.3f}  (threshold={thr:.3f})"
        if best_name:                        # matched
            color = "#27ae60"
        elif best_dist < thr * 1.5:          # close — raise threshold slightly
            color = "#e67e22"
        else:                                # far off
            color = "#c0392b"
        self.segment_lbl.setText(text)
        self.segment_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")

    def recognition_settings(self) -> dict:
        return {
            "threshold":   self.threshold_spin.value(),
            "cooldown":    self.cooldown_spin.value(),
            "motion":      self.motion_spin.value(),
            "skip_frames": self.skip_spin.value(),
            "imgsz":       self.imgsz_combo.currentData(),
        }

    def apply_recognition_settings(self, s: dict) -> None:
        self.threshold_spin.setValue(s.get("threshold",   0.30))
        self.cooldown_spin.setValue(s.get("cooldown",     1.5))
        self.motion_spin.setValue(s.get("motion",         0.02))
        skip = s.get("skip_frames", 2)
        self.skip_spin.setValue(skip)
        imgsz = s.get("imgsz", 320)
        idx = self.imgsz_combo.findData(imgsz)
        if idx >= 0:
            self.imgsz_combo.setCurrentIndex(idx)
        self._apply_settings()
        self._apply_perf_settings()

    def _set_status(self, text: str, color: str):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(f"color: {color};")
