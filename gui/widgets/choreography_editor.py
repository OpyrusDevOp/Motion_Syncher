from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QCheckBox, QLabel, QDialog,
)
from PySide6.QtCore import Signal, Qt

from PySide6.QtGui import QColor

from core.choreography.models import Choreography, Pair


class ChoreographyEditorWidget(QWidget):
    choreography_changed = Signal()
    reload_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pairs: list[Pair] = []
        self._available_gestures: list[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        header = QHBoxLayout()
        header.addWidget(QLabel("<b>Choreography</b>"))
        header.addStretch()
        self.reload_btn = QPushButton("⟳")
        self.reload_btn.setFixedWidth(28)
        self.reload_btn.setToolTip("Reload choreography from disk")
        self.reload_btn.clicked.connect(self.reload_requested.emit)
        header.addWidget(self.reload_btn)
        self.loop_check = QCheckBox("Loop")
        self.loop_check.stateChanged.connect(lambda _: self.choreography_changed.emit())
        header.addWidget(self.loop_check)
        layout.addLayout(header)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.add_btn    = QPushButton("+ Add")
        self.edit_btn   = QPushButton("Edit")
        self.remove_btn = QPushButton("Remove")
        self.up_btn     = QPushButton("▲")
        self.down_btn   = QPushButton("▼")
        for b in (self.add_btn, self.edit_btn, self.remove_btn, self.up_btn, self.down_btn):
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

        self.add_btn.clicked.connect(self._add_step)
        self.edit_btn.clicked.connect(self._edit_step)
        self.remove_btn.clicked.connect(self._remove_step)
        self.up_btn.clicked.connect(self._move_up)
        self.down_btn.clicked.connect(self._move_down)
        self.list_widget.itemDoubleClicked.connect(lambda _: self._edit_step())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_available_gestures(self, gestures: list[str]) -> None:
        self._available_gestures = gestures

    def get_choreography(self) -> Choreography:
        return Choreography(pairs=list(self._pairs), loop=self.loop_check.isChecked())

    def load_choreography(self, chor: Choreography) -> None:
        self._pairs = list(chor.pairs)
        self.loop_check.setChecked(chor.loop)
        self._refresh()

    def highlight_step(self, step: int) -> None:
        """Color the active step green; grey-out completed ones."""
        done_color = QColor("#2a2a2a")
        active_color = QColor("#1a5c1a")
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if i < step:
                item.setBackground(done_color)
            elif i == step:
                item.setBackground(active_color)
                self.list_widget.scrollToItem(item)
            else:
                item.setBackground(QColor("transparent"))

    def clear_highlight(self) -> None:
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setBackground(QColor("transparent"))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _add_step(self):
        from gui.widgets.pair_dialog import PairDialog
        dlg = PairDialog(self._available_gestures, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            pair = dlg.get_pair()
            if pair:
                self._pairs.append(pair)
                self._refresh()
                self.choreography_changed.emit()

    def _edit_step(self):
        row = self.list_widget.currentRow()
        if not (0 <= row < len(self._pairs)):
            return
        from gui.widgets.pair_dialog import PairDialog
        dlg = PairDialog(self._available_gestures, self)
        dlg.load_pair(self._pairs[row])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            pair = dlg.get_pair()
            if pair:
                self._pairs[row] = pair
                self._refresh()
                self.list_widget.setCurrentRow(row)
                self.choreography_changed.emit()

    def _remove_step(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self._pairs):
            self._pairs.pop(row)
            self._refresh()
            self.choreography_changed.emit()

    def _move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            self._pairs[row - 1], self._pairs[row] = self._pairs[row], self._pairs[row - 1]
            self._refresh()
            self.list_widget.setCurrentRow(row - 1)
            self.choreography_changed.emit()

    def _move_down(self):
        row = self.list_widget.currentRow()
        if row < len(self._pairs) - 1:
            self._pairs[row], self._pairs[row + 1] = self._pairs[row + 1], self._pairs[row]
            self._refresh()
            self.list_widget.setCurrentRow(row + 1)
            self.choreography_changed.emit()

    def _refresh(self):
        self.list_widget.clear()
        for i, pair in enumerate(self._pairs):
            self.list_widget.addItem(f"{i + 1}.  {pair}")
