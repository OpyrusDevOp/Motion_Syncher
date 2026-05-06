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

    TYPE_ID = "audio"
    DISPLAY_NAME = "Play Audio"
    DESCRIPTION = "Play, stop, or toggle a music file"

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
        self.action = action  # "play" | "stop" | "toggle"
        self.volume = max(0.0, min(1.0, volume))

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
