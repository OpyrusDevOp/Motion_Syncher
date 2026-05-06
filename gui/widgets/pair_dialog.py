from PySide6.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QStackedWidget,
    QDialogButtonBox,
)

from core.choreography.models import Pair
from core.functions import get_registry
from gui.widgets.function_config import FunctionConfigWidget

_USER_ROLE = 0x0100  # Qt.ItemDataRole.UserRole


class PairDialog(QDialog):
    def __init__(self, gesture_names: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add / Edit Step")
        self.setMinimumWidth(460)
        layout = QFormLayout(self)

        # Gesture selector
        self.gesture_combo = QComboBox()
        if gesture_names:
            self.gesture_combo.addItems(gesture_names)
        else:
            self.gesture_combo.addItem("(no gestures recorded yet)")
            self.gesture_combo.setEnabled(False)
        layout.addRow("Gesture:", self.gesture_combo)

        # Function type — driven by registry
        self.func_type = QComboBox()
        self._config_pages: list[FunctionConfigWidget] = []
        self.stack = QStackedWidget()

        registry = get_registry()
        for tid, cls in registry.items():
            display = cls.DISPLAY_NAME or tid
            self.func_type.addItem(display, userData=tid)
            page = FunctionConfigWidget(cls, self)
            self._config_pages.append(page)
            self.stack.addWidget(page)

        layout.addRow("Function type:", self.func_type)
        layout.addRow("Config:", self.stack)
        self.func_type.currentIndexChanged.connect(self.stack.setCurrentIndex)

        # OK / Cancel
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def get_pair(self) -> Pair | None:
        gesture = self.gesture_combo.currentText()
        if not gesture or not self.gesture_combo.isEnabled():
            return None
        page = self._config_pages[self.func_type.currentIndex()]
        fn = page.build_function()
        return Pair(gesture, fn)
