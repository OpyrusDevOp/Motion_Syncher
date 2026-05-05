from pathlib import Path
from .base import Function

_mixer_ready = False


def _ensure_mixer() -> bool:
    global _mixer_ready
    if _mixer_ready:
        return True
    try:
        import pygame
        pygame.mixer.init()
        _mixer_ready = True
        return True
    except Exception as e:
        print(f"[AudioFunction] mixer init failed: {e}")
        return False


class AudioFunction(Function):
    """Play / stop / toggle a music file via pygame.mixer."""

    def __init__(self, file_path: str, volume: float = 1.0, action: str = "play"):
        self.file_path = file_path
        self.volume = max(0.0, min(1.0, volume))
        self.action = action  # "play" | "stop" | "toggle"

    @property
    def name(self) -> str:
        stem = Path(self.file_path).stem if self.file_path else "—"
        return f"Audio [{self.action}]: {stem}"

    def execute(self) -> None:
        if not _ensure_mixer():
            return
        import pygame

        if self.action == "stop":
            pygame.mixer.music.stop()
            return
        if self.action == "toggle":
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()
            return
        # play
        if not self.file_path or not Path(self.file_path).exists():
            print(f"[AudioFunction] file not found: {self.file_path!r}")
            return
        pygame.mixer.music.load(self.file_path)
        pygame.mixer.music.set_volume(self.volume)
        pygame.mixer.music.play()

    def to_dict(self) -> dict:
        return {
            "type": "audio",
            "file_path": self.file_path,
            "volume": self.volume,
            "action": self.action,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AudioFunction":
        return cls(data["file_path"], data.get("volume", 1.0), data.get("action", "play"))
