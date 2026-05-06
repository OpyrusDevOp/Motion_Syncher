from __future__ import annotations

import os
import shutil
import signal
import subprocess
from pathlib import Path

from .base import Function

# First available player wins; checked once at import time
_PLAYER: str | None = next(
    (p for p in ("mpv", "ffplay", "cvlc") if shutil.which(p)),
    None,
)

_PLAYER_FLAGS: dict[str, list[str]] = {
    "mpv":    ["--really-quiet", "--no-video"],
    "ffplay": ["-nodisp", "-autoexit", "-loglevel", "quiet"],
    "cvlc":   ["--intf", "dummy", "--play-and-exit"],
}


def _volume_args(player: str, volume: float) -> list[str]:
    v = int(volume * 100)
    if player == "mpv":
        return [f"--volume={v}"]
    if player == "ffplay":
        return ["-volume", str(v)]
    return []


class AudioFunction(Function):
    """Play / stop / toggle a music file via mpv / ffplay / cvlc."""

    TYPE_ID      = "audio"
    DISPLAY_NAME = "Play Audio"
    DESCRIPTION  = "Play, stop, or toggle a music file"

    @classmethod
    def config_schema(cls) -> list[dict]:
        return [
            {"key": "file_path", "label": "Audio file", "type": "file",
             "filter": "Audio (*.mp3 *.wav *.ogg *.flac *.m4a *.aac)", "default": ""},
            {"key": "action", "label": "Action", "type": "select",
             "options": ["play", "stop", "toggle"], "default": "play"},
            {"key": "volume", "label": "Volume", "type": "float",
             "min": 0.0, "max": 1.0, "step": 0.05, "default": 1.0},
        ]

    def __init__(self, file_path: str = "", action: str = "play", volume: float = 1.0):
        self.file_path = file_path
        self.action    = action   # "play" | "stop" | "toggle"
        self.volume    = max(0.0, min(1.0, volume))
        self._process: subprocess.Popen | None = None
        self._paused: bool = False

    @property
    def name(self) -> str:
        stem = Path(self.file_path).stem if self.file_path else "—"
        return f"Audio [{self.action}]: {stem}"

    def execute(self) -> None:
        if self.action == "stop":
            self._stop()
        elif self.action == "toggle":
            self._toggle()
        else:
            self._play()

    # ------------------------------------------------------------------

    def _play(self) -> None:
        self._stop()
        if _PLAYER is None:
            print("[AudioFunction] no player found — install mpv, ffplay, or cvlc")
            return
        if not self.file_path or not Path(self.file_path).exists():
            print(f"[AudioFunction] file not found: {self.file_path!r}")
            return
        cmd = (
            [_PLAYER]
            + _PLAYER_FLAGS.get(_PLAYER, [])
            + _volume_args(_PLAYER, self.volume)
            + [self.file_path]
        )
        self._process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._paused = False

    def _stop(self) -> None:
        if self._process and self._process.poll() is None:
            self._process.terminate()
        self._process = None
        self._paused  = False

    def _toggle(self) -> None:
        if self._process is None or self._process.poll() is not None:
            self._play()
        elif self._paused:
            os.kill(self._process.pid, signal.SIGCONT)
            self._paused = False
        else:
            os.kill(self._process.pid, signal.SIGSTOP)
            self._paused = True
