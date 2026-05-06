"""
Example plugin: desktop notification.

Drop this file (or any *.py) in the plugins/ folder and Motion Syncher will
pick it up automatically at startup.  See plugins/HOWTO.md for the full guide.
"""

import subprocess
from core.functions.base import Function


class DesktopNotifyFunction(Function):
    TYPE_ID      = "desktop_notify"
    DISPLAY_NAME = "Desktop Notification"
    DESCRIPTION  = "Show a desktop notification (uses notify-send on Linux)"

    @classmethod
    def config_schema(cls) -> list[dict]:
        return [
            {"key": "title",   "label": "Title",   "type": "text",
             "placeholder": "Motion Syncher", "default": "Motion Syncher"},
            {"key": "message", "label": "Message", "type": "text",
             "placeholder": "Gesture triggered!", "default": "Gesture triggered!"},
        ]

    def __init__(self, title: str = "Motion Syncher", message: str = "Gesture triggered!"):
        self.title   = title
        self.message = message

    @property
    def name(self) -> str:
        return f"Notify: {self.title!r}"

    def execute(self) -> None:
        subprocess.Popen(["notify-send", self.title, self.message])
