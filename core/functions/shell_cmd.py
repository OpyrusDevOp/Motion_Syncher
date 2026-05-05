import subprocess
from .base import Function


class ShellFunction(Function):
    def __init__(self, command: str):
        self.command = command

    @property
    def name(self) -> str:
        preview = self.command[:40] + ("…" if len(self.command) > 40 else "")
        return f"Shell: {preview}"

    def execute(self) -> None:
        if not self.command.strip():
            return
        subprocess.Popen(self.command, shell=True)

    def to_dict(self) -> dict:
        return {"type": "shell", "command": self.command}

    @classmethod
    def from_dict(cls, data: dict) -> "ShellFunction":
        return cls(data["command"])
