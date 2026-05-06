import subprocess
from .base import Function


class ShellFunction(Function):
    TYPE_ID = "shell"
    DISPLAY_NAME = "Shell Command"
    DESCRIPTION = "Run a shell command in the background"

    @classmethod
    def config_schema(cls) -> list[dict]:
        return [
            {"key": "command", "label": "Command", "type": "text",
             "placeholder": "e.g. osascript -e 'set volume 5'", "default": ""},
        ]

    def __init__(self, command: str = ""):
        self.command = command

    @property
    def name(self) -> str:
        preview = self.command[:40] + ("…" if len(self.command) > 40 else "")
        return f"Shell: {preview}"

    def execute(self) -> None:
        if not self.command.strip():
            return
        subprocess.Popen(self.command, shell=True)
