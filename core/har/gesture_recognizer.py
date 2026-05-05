import time
from dataclasses import dataclass, field
import numpy as np
from .dtw import dtw_distance


@dataclass
class GestureTemplate:
    name: str
    sequences: list[np.ndarray] = field(default_factory=list)

    def best_distance(self, query: np.ndarray) -> float:
        return min(dtw_distance(query, t) for t in self.sequences)


class GestureRecognizer:
    def __init__(self, threshold: float = 0.30, cooldown_seconds: float = 1.5):
        self.threshold = threshold
        self.cooldown_seconds = cooldown_seconds

        self._templates: dict[str, GestureTemplate] = {}
        self._last_trigger: float = 0.0

    # ------------------------------------------------------------------
    # Template management
    # ------------------------------------------------------------------

    def add_template(self, name: str, sequence: np.ndarray) -> None:
        if name not in self._templates:
            self._templates[name] = GestureTemplate(name=name)
        self._templates[name].sequences.append(sequence.copy())

    def remove_template(self, name: str) -> None:
        self._templates.pop(name, None)

    def clear(self) -> None:
        self._templates.clear()

    def list_gestures(self) -> list[str]:
        return list(self._templates.keys())

    def get_template_count(self, name: str) -> int:
        if name in self._templates:
            return len(self._templates[name].sequences)
        return 0

    # ------------------------------------------------------------------
    # Recognition
    # ------------------------------------------------------------------

    def recognize(self, sequence: np.ndarray) -> tuple[str | None, float]:
        """
        Compare sequence against all templates.
        Returns (best_name, distance) if below threshold and cooldown elapsed,
        otherwise (None, best_distance_found).
        """
        if not self._templates:
            return None, float("inf")

        now = time.monotonic()
        in_cooldown = (now - self._last_trigger) < self.cooldown_seconds

        best_name: str | None = None
        best_dist = float("inf")

        for name, template in self._templates.items():
            d = template.best_distance(sequence)
            if d < best_dist:
                best_dist = d
                best_name = name

        if best_dist <= self.threshold and not in_cooldown:
            self._last_trigger = now
            return best_name, best_dist

        return None, best_dist
