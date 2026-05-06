"""
Dynamic form widget built from Function.config_schema().

Usage:
    widget = FunctionConfigWidget(MyFunctionClass, parent)
    # ... user fills fields ...
    fn = widget.build_function()   # returns MyFunctionClass instance
"""
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox,
    QSpinBox, QHBoxLayout, QPushButton, QFileDialog,
)

from core.functions.base import Function


class FunctionConfigWidget(QWidget):
    def __init__(self, cls: type[Function], parent=None):
        super().__init__(parent)
        self._cls = cls
        self._inputs: dict[str, QWidget] = {}

        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)

        for field in cls.config_schema():
            key     = field["key"]
            label   = field.get("label", key)
            ftype   = field.get("type", "text")
            default = field.get("default", "")

            if ftype == "text":
                w = QLineEdit()
                w.setPlaceholderText(field.get("placeholder", ""))
                if default:
                    w.setText(str(default))
                self._inputs[key] = w
                form.addRow(label + ":", w)

            elif ftype == "file":
                row = QWidget()
                hl  = QHBoxLayout(row)
                hl.setContentsMargins(0, 0, 0, 0)
                w = QLineEdit()
                w.setPlaceholderText(field.get("placeholder", ""))
                btn = QPushButton("…")
                btn.setFixedWidth(28)
                filt = field.get("filter", "")
                btn.clicked.connect(lambda _, w=w, filt=filt: self._browse(w, filt))
                hl.addWidget(w)
                hl.addWidget(btn)
                self._inputs[key] = w
                form.addRow(label + ":", row)

            elif ftype == "select":
                w = QComboBox()
                w.addItems([str(o) for o in field.get("options", [])])
                idx = w.findText(str(default))
                if idx >= 0:
                    w.setCurrentIndex(idx)
                self._inputs[key] = w
                form.addRow(label + ":", w)

            elif ftype == "float":
                w = QDoubleSpinBox()
                w.setRange(field.get("min", 0.0), field.get("max", 9999.0))
                w.setSingleStep(field.get("step", 0.1))
                w.setDecimals(3)
                w.setValue(float(default) if default != "" else 0.0)
                self._inputs[key] = w
                form.addRow(label + ":", w)

            elif ftype == "int":
                w = QSpinBox()
                w.setRange(int(field.get("min", 0)), int(field.get("max", 9999)))
                w.setSingleStep(int(field.get("step", 1)))
                w.setValue(int(default) if default != "" else 0)
                self._inputs[key] = w
                form.addRow(label + ":", w)

    # ------------------------------------------------------------------

    def _browse(self, target: QLineEdit, filt: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", filt)
        if path:
            target.setText(path)

    def get_values(self) -> dict:
        values: dict = {}
        for field in self._cls.config_schema():
            key = field["key"]
            w   = self._inputs.get(key)
            if w is None:
                continue
            ftype = field.get("type", "text")
            if ftype in ("text", "file"):
                values[key] = w.text()              # type: ignore[union-attr]
            elif ftype == "select":
                values[key] = w.currentText()       # type: ignore[union-attr]
            elif ftype in ("float", "int"):
                values[key] = w.value()             # type: ignore[union-attr]
        return values

    def load_values(self, data: dict) -> None:
        for field in self._cls.config_schema():
            key = field["key"]
            w   = self._inputs.get(key)
            if w is None or key not in data:
                continue
            ftype = field.get("type", "text")
            val   = data[key]
            if ftype in ("text", "file"):
                w.setText(str(val))                 # type: ignore[union-attr]
            elif ftype == "select":
                idx = w.findText(str(val))          # type: ignore[union-attr]
                if idx >= 0:
                    w.setCurrentIndex(idx)          # type: ignore[union-attr]
            elif ftype in ("float", "int"):
                w.setValue(val)                     # type: ignore[union-attr]

    def build_function(self) -> Function:
        return self._cls.from_dict({"type": self._cls.TYPE_ID, **self.get_values()})
