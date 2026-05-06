from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox, QLineEdit,
    QPushButton, QFileDialog,
)
from PySide6.QtCore import Signal

from core.functions.base import Function
from core.functions import get_registry


class QuickArmWidget(QWidget):
    """
    Toolbar-style widget: pick one gesture → one function and arm it instantly.
    Shows the first config field inline; multi-field functions fall back to
    their schema defaults for the remaining fields.
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
        registry = get_registry()
        for tid, cls in registry.items():
            self.func_combo.addItem(cls.DISPLAY_NAME or tid, userData=tid)
        layout.addWidget(self.func_combo)

        self.config_input = QLineEdit()
        self.config_input.setMinimumWidth(200)
        layout.addWidget(self.config_input)

        self._browse_btn = QPushButton("…")
        self._browse_btn.setFixedWidth(28)
        self._browse_btn.setVisible(False)
        self._browse_btn.clicked.connect(self._browse_file)
        layout.addWidget(self._browse_btn)

        self.arm_btn = QPushButton("Arm")
        self.arm_btn.setCheckable(True)
        self.arm_btn.setFixedWidth(64)
        self.arm_btn.toggled.connect(self._on_toggled)
        layout.addWidget(self.arm_btn)

        self.func_combo.currentIndexChanged.connect(self._on_func_type_changed)
        self._on_func_type_changed(0)

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

    def _first_field(self) -> dict | None:
        tid = self.func_combo.currentData()
        cls = get_registry().get(tid)
        if cls is None:
            return None
        schema = cls.config_schema()
        return schema[0] if schema else None

    def _on_func_type_changed(self, _idx: int) -> None:
        field = self._first_field()
        if field is None:
            self.config_input.setPlaceholderText("")
            self._browse_btn.setVisible(False)
            return
        self.config_input.setPlaceholderText(
            field.get("placeholder", field.get("label", ""))
        )
        self._browse_btn.setVisible(field.get("type") == "file")

    def _browse_file(self) -> None:
        field = self._first_field()
        filt  = field.get("filter", "") if field else ""
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", filt)
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
        tid = self.func_combo.currentData()
        cls = get_registry().get(tid)
        if cls is None:
            return None
        schema = cls.config_schema()
        if not schema:
            return cls()
        # Fill the first field from the inline input; rest get schema defaults
        first_key = schema[0]["key"]
        kwargs: dict = {first_key: self.config_input.text().strip()}
        for field in schema[1:]:
            kwargs[field["key"]] = field.get("default", "")
        return cls(**kwargs)
