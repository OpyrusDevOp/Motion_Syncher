from dataclasses import dataclass, field
from core.functions.base import Function


@dataclass
class Pair:
    gesture: str
    function: Function

    def __str__(self) -> str:
        return f"{self.gesture}  →  {self.function.name}"


@dataclass
class Choreography:
    pairs: list[Pair] = field(default_factory=list)
    loop: bool = False
    name: str = "Untitled"
