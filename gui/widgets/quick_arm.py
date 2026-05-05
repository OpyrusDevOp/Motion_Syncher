from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QFileDialog,
)
from PySide6.QtCore import Signal

from core.functions.base import Function
from core.functions.shell_cmd import ShellFunction
from core.functions.audio import AudioFunction
from core.functions.keystroke import KeystrokeFunction
from core.functions.console_write import ConsoleWriteFunction


class QuickArmWidget(QWidget):
    """
    Toolbar-style widget: pick one gesture → one function and arm it instantly.
    When armed the binding fires on every detection (FREE mode alongside choreography).
    """

    armed = Signal(str, object)   # gesture_name, Function instance
    disarmed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        layout.addWidget(QLabel("Quick arm:"))

        self.gesture_combo = QComboBox()
        self.gesture_combo.setMinimumWidth(120)
        self.gesture_combo.setPlaceholderText("gesture…")
        layout.addWidget(self.gesture_combo)

        layout.addWidget(QLabel("→"))

        self.func_combo = QComboBox()
        self.func_combo.addItems(["Shell", "Audio", "Keystroke", "Console"])
        layout.addWidget(self.func_combo)

        self.config_input = QLineEdit()
        self.config_input.setPlaceholderText("command / file / key / text")
        self.config_input.setMinimumWidth(200)
        layout.addWidget(self.config_input)

        self._browse_btn = QPushButton("…")
        self._browse_btn.setFixedWidth(28)
        self._browse_btn.setVisible(False)
        self._browse_btn.clicked.connect(self._browse_audio)
        layout.addWidget(self._browse_btn)

        self.arm_btn = QPushButton("Arm")
        self.arm_btn.setCheckable(True)
        self.arm_btn.setFixedWidth(64)
        self.arm_btn.toggled.connect(self._on_toggled)
        layout.addWidget(self.arm_btn)

        self.func_combo.currentIndexChanged.connect(self._on_func_type_changed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_gestures(self, names: list[str]) -> None:
        current = self.gesture_combo.currentText()
        self.gesture_combo.clear()
        self.gesture_combo.addItems(names)
        idx = self.gesture_combo.findText(current)
        if idx >= 0:
            self.gesture_combo.setCurrentIndex(idx)

    def disarm(self) -> None:
        self.arm_btn.setChecked(False)

    # ------------------------------------------------------------------

    def _on_func_type_changed(self, idx: int) -> None:
        self._browse_btn.setVisible(idx == 1)  # Audio
        placeholders = [
            "shell command…",
            "path/to/audio.mp3",
            "e.g. ctrl+c  |  media_play_pause",
            "text to print",
        ]
        self.config_input.setPlaceholderText(placeholders[idx])

    def _browse_audio(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "",
            "Audio (*.mp3 *.wav *.ogg *.flac *.m4a *.aac)"
        )
        if path:
            self.config_input.setText(path)

    def _on_toggled(self, checked: bool) -> None:
        if checked:
            fn = self._build_function()
            gesture = self.gesture_combo.currentText()
            if fn is None or not gesture:
                self.arm_btn.setChecked(False)
                return
            self.arm_btn.setText("Armed")
            self.arm_btn.setStyleSheet(
                "QPushButton { background: #1a5c1a; color: white; border-radius: 3px; }"
            )
            self.armed.emit(gesture, fn)
        else:
            self.arm_btn.setText("Arm")
            self.arm_btn.setStyleSheet("")
            self.disarmed.emit()

    def _build_function(self) -> Function | None:
        text = self.config_input.text().strip()
        idx = self.func_combo.currentIndex()
        if idx == 0:
            return ShellFunction(text)
        if idx == 1:
            return AudioFunction(text)
        if idx == 2:
            return KeystrokeFunction(text)
        return ConsoleWriteFunction(text)
