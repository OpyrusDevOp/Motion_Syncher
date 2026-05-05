import queue as _queue
from .base import Function

# Thread-safe queue; the GUI polls this with a QTimer
output_queue: _queue.Queue[str] = _queue.Queue()


class ConsoleWriteFunction(Function):
    def __init__(self, text: str):
        self.text = text

    @property
    def name(self) -> str:
        preview = self.text[:30] + ("…" if len(self.text) > 30 else "")
        return f"Console: {preview!r}"

    def execute(self) -> None:
        output_queue.put(self.text)

    def to_dict(self) -> dict:
        return {"type": "console", "text": self.text}

    @classmethod
    def from_dict(cls, data: dict) -> "ConsoleWriteFunction":
        return cls(data["text"])
