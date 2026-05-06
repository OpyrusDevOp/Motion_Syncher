"""
Discovers and registers Function subclasses from user-supplied plugin directories.

Each .py file in the given directory is imported as a module. Any class that:
  - subclasses Function
  - is not Function itself
  - has a non-empty TYPE_ID

is added to the shared registry. Duplicate TYPE_IDs emit a warning and are skipped.
"""

import importlib.util
import sys
from pathlib import Path

from .base import Function
from . import _REGISTRY


def load_user_plugins(dirs: list[str | Path]) -> list[str]:
    """Import every .py file in *dirs* and register Function subclasses found inside.

    Returns the list of TYPE_IDs that were successfully registered.
    """
    registered: list[str] = []

    for directory in dirs:
        dirpath = Path(directory)
        if not dirpath.is_dir():
            continue
        for py_file in sorted(dirpath.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = f"_motionsyncher_plugin_{py_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)  # type: ignore[union-attr]
            except Exception as exc:
                print(f"[PluginLoader] failed to load {py_file.name}: {exc}")
                continue

            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, Function)
                    and obj is not Function
                    and obj.TYPE_ID
                ):
                    tid = obj.TYPE_ID
                    if tid in _REGISTRY:
                        print(f"[PluginLoader] {py_file.name}: TYPE_ID {tid!r} already registered — skipped")
                        continue
                    _REGISTRY[tid] = obj
                    registered.append(tid)

    return registered
