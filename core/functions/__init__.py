from .base import Function
from .audio import AudioFunction
from .shell_cmd import ShellFunction
from .keystroke import KeystrokeFunction
from .console_write import ConsoleWriteFunction

_REGISTRY: dict[str, type[Function]] = {
    "audio": AudioFunction,
    "shell": ShellFunction,
    "keystroke": KeystrokeFunction,
    "console": ConsoleWriteFunction,
}

def function_from_dict(data: dict) -> Function:
    cls = _REGISTRY.get(data["type"])
    if cls is None:
        raise ValueError(f"Unknown function type: {data['type']!r}")
    return cls.from_dict(data)
