from enum import Enum, auto

from PySide6.QtCore import QObject, Signal

from core.choreography.models import Choreography
from core.functions.base import Function


class EngineMode(Enum):
    SEQUENTIAL = auto()
    FREE = auto()
    BOTH = auto()


class ChoreographyEngine(QObject):
    """
    Receives confirmed gesture names and fires the associated functions.

    SEQUENTIAL: advances step-by-step through the choreography list.
    FREE:       any gesture fires its bound function immediately.
    BOTH:       free bindings always fire; sequential advances in parallel.
    """

    function_triggered = Signal(str, str)   # gesture_name, function.name
    step_changed = Signal(int)              # new step index (0-based)
    choreography_done = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._choreography: Choreography | None = None
        self._step = 0
        self._mode = EngineMode.SEQUENTIAL
        self._free_bindings: dict[str, Function] = {}

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def set_choreography(self, chor: Choreography) -> None:
        self._choreography = chor
        self._step = 0
        self.step_changed.emit(0)

    def set_mode(self, mode: EngineMode) -> None:
        self._mode = mode

    def set_free_bindings(self, bindings: dict[str, Function]) -> None:
        self._free_bindings = bindings

    def reset(self) -> None:
        self._step = 0
        self.step_changed.emit(0)

    @property
    def current_step(self) -> int:
        return self._step

    # ------------------------------------------------------------------
    # Runtime
    # ------------------------------------------------------------------

    def on_gesture(self, gesture_name: str) -> None:
        if self._mode in (EngineMode.FREE, EngineMode.BOTH):
            fn = self._free_bindings.get(gesture_name)
            if fn:
                fn.execute()
                self.function_triggered.emit(gesture_name, fn.name)

        if self._mode in (EngineMode.SEQUENTIAL, EngineMode.BOTH):
            chor = self._choreography
            if not chor or not chor.pairs or self._step >= len(chor.pairs):
                return
            pair = chor.pairs[self._step]
            if pair.gesture != gesture_name:
                return
            pair.function.execute()
            self.function_triggered.emit(gesture_name, pair.function.name)
            self._step += 1

            if self._step >= len(chor.pairs):
                if chor.loop:
                    self._step = 0
                else:
                    self.choreography_done.emit()

            self.step_changed.emit(self._step)
