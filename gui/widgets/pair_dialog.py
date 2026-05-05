from PySide6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QStackedWidget, QWidget,
    QHBoxLayout, QLineEdit, QPushButton, QDialogButtonBox,
    QFileDialog, QDoubleSpinBox, QLabel,
)

from core.choreography.models import Pair
from core.functions.audio import AudioFunction
from core.functions.shell_cmd import ShellFunction
from core.functions.keystroke import KeystrokeFunction
from core.functions.console_write import ConsoleWriteFunction


class PairDialog(QDialog):
    def __init__(self, gesture_names: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add / Edit Step")
        self.setMinimumWidth(440)
        layout = QFormLayout(self)

        # Gesture selector
        self.gesture_combo = QComboBox()
        if gesture_names:
            self.gesture_combo.addItems(gesture_names)
        else:
            self.gesture_combo.addItem("(no gestures recorded yet)")
            self.gesture_combo.setEnabled(False)
        layout.addRow("Gesture:", self.gesture_combo)

        # Function type
        self.func_type = QComboBox()
        self.func_type.addItems(["Shell Command", "Play Audio", "Keystroke", "Console Write"])
        layout.addRow("Function type:", self.func_type)

        # Stacked config pages (index matches func_type)
        self.stack = QStackedWidget()

        # 0 — Shell
        p0 = QWidget()
        l0 = QHBoxLayout(p0)
        l0.setContentsMargins(0, 0, 0, 0)
        self.shell_input = QLineEdit()
        self.shell_input.setPlaceholderText("e.g. notify-send 'Action triggered!'")
        l0.addWidget(self.shell_input)
        self.stack.addWidget(p0)

        # 1 — Audio
        p1 = QWidget()
        l1 = QHBoxLayout(p1)
        l1.setContentsMargins(0, 0, 0, 0)
        self.audio_path = QLineEdit()
        self.audio_path.setPlaceholderText("Path to audio file…")
        browse_btn = QPushButton("Browse")
        browse_btn.setFixedWidth(70)
        browse_btn.clicked.connect(self._browse_audio)
        self.audio_action_combo = QComboBox()
        self.audio_action_combo.addItems(["play", "stop", "toggle"])
        l1.addWidget(self.audio_path)
        l1.addWidget(browse_btn)
        l1.addWidget(self.audio_action_combo)
        self.stack.addWidget(p1)

        # 2 — Keystroke
        p2 = QWidget()
        l2 = QHBoxLayout(p2)
        l2.setContentsMargins(0, 0, 0, 0)
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("e.g. ctrl+c  |  space  |  media_play_pause")
        l2.addWidget(self.key_input)
        self.stack.addWidget(p2)

        # 3 — Console
        p3 = QWidget()
        l3 = QHBoxLayout(p3)
        l3.setContentsMargins(0, 0, 0, 0)
        self.console_input = QLineEdit()
        self.console_input.setPlaceholderText("Text to print to the console")
        l3.addWidget(self.console_input)
        self.stack.addWidget(p3)

        layout.addRow("Config:", self.stack)
        self.func_type.currentIndexChanged.connect(self.stack.setCurrentIndex)

        # OK / Cancel
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _browse_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "",
            "Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a *.aac)"
        )
        if path:
            self.audio_path.setText(path)

    def get_pair(self) -> Pair | None:
        gesture = self.gesture_combo.currentText()
        idx = self.func_type.currentIndex()

        if idx == 0:
            fn = ShellFunction(self.shell_input.text())
        elif idx == 1:
            fn = AudioFunction(
                self.audio_path.text(),
                action=self.audio_action_combo.currentText(),
            )
        elif idx == 2:
            fn = KeystrokeFunction(self.key_input.text())
        else:
            fn = ConsoleWriteFunction(self.console_input.text())

        return Pair(gesture, fn)
