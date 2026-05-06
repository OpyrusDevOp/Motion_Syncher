from .base import Function
from .audio import AudioFunction
from .shell_cmd import ShellFunction
from .keystroke import KeystrokeFunction
from .console_write import ConsoleWriteFunction

_BUILTIN: list[type[Function]] = [
    AudioFunction,
    ShellFunction,
    KeystrokeFunction,
    ConsoleWriteFunction,
]

# TYPE_ID → class; populated at module load, extended by load_user_plugins()
_REGISTRY: dict[str, type[Function]] = {cls.TYPE_ID: cls for cls in _BUILTIN}


def get_registry() -> dict[str, type[Function]]:
    return dict(_REGISTRY)


def load_user_plugins(dirs: list) -> list[str]:
    from .plugin_loader import load_user_plugins as _load
    return _load(dirs)


def function_from_dict(data: dict) -> Function:
    cls = _REGISTRY.get(data["type"])
    if cls is None:
        raise ValueError(f"Unknown function type: {data['type']!r}")
    return cls.from_dict(data)
