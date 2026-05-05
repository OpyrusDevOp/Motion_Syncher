from .base import Function

# Lazily imported so pynput is optional at import time
_keyboard_ctrl = None


def _get_keyboard():
    global _keyboard_ctrl
    if _keyboard_ctrl is None:
        from pynput.keyboard import Controller
        _keyboard_ctrl = Controller()
    return _keyboard_ctrl


def _parse_key(token: str):
    from pynput.keyboard import Key
    _KEY_MAP = {
        "ctrl": Key.ctrl, "alt": Key.alt, "shift": Key.shift,
        "super": Key.cmd, "cmd": Key.cmd, "win": Key.cmd,
        "space": Key.space, "enter": Key.enter, "return": Key.enter,
        "esc": Key.esc, "escape": Key.esc, "tab": Key.tab,
        "backspace": Key.backspace, "delete": Key.delete,
        "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
        "home": Key.home, "end": Key.end,
        "page_up": Key.page_up, "page_down": Key.page_down,
        "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
        "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
        "f9": Key.f9, "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
        "media_play_pause": Key.media_play_pause,
        "media_next": Key.media_next,
        "media_previous": Key.media_previous,
        "media_volume_up": Key.media_volume_up,
        "media_volume_down": Key.media_volume_down,
        "media_volume_mute": Key.media_volume_mute,
    }
    t = token.strip().lower()
    return _KEY_MAP.get(t, t if len(t) == 1 else None)


class KeystrokeFunction(Function):
    """Send a key sequence such as 'ctrl+c', 'space', 'media_play_pause'."""

    def __init__(self, key_sequence: str):
        self.key_sequence = key_sequence

    @property
    def name(self) -> str:
        return f"Key: {self.key_sequence}"

    def execute(self) -> None:
        if not self.key_sequence.strip():
            return
        kb = _get_keyboard()
        parts = [p.strip() for p in self.key_sequence.split("+")]
        keys = [_parse_key(p) for p in parts]
        keys = [k for k in keys if k is not None]
        if not keys:
            return

        modifiers = keys[:-1]
        main_key = keys[-1]

        for mod in modifiers:
            kb.press(mod)
        kb.tap(main_key)
        for mod in reversed(modifiers):
            kb.release(mod)

    def to_dict(self) -> dict:
        return {"type": "keystroke", "key_sequence": self.key_sequence}

    @classmethod
    def from_dict(cls, data: dict) -> "KeystrokeFunction":
        return cls(data["key_sequence"])
