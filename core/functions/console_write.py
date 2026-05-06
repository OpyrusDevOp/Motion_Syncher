import queue as _queue
from .base import Function

# Thread-safe queue; the GUI polls this with a QTimer
output_queue: _queue.Queue[str] = _queue.Queue()


class ConsoleWriteFunction(Function):
    TYPE_ID = "console"
    DISPLAY_NAME = "Console Write"
    DESCRIPTION = "Push a text message to the in-app console output"

    @classmethod
    def config_schema(cls) -> list[dict]:
        return [
            {"key": "text", "label": "Text", "type": "text",
             "placeholder": "Message to display", "default": ""},
        ]

    def __init__(self, text: str = ""):
        self.text = text

    @property
    def name(self) -> str:
        preview = self.text[:30] + ("…" if len(self.text) > 30 else "")
        return f"Console: {preview!r}"

    def execute(self) -> None:
        output_queue.put(self.text)
