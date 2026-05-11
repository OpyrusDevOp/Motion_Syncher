# runtime_hooks/set_env.py
#
# Executed by PyInstaller's bootloader before any application code runs.
# Redirects cache/config directories that YOLO and torch write to at
# runtime — the frozen archive itself may be read-only or on a
# temporary filesystem.

import os
import sys
import tempfile


def _user_data_dir(app: str) -> str:
    """Return a platform-appropriate, writable user-data directory."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, app)


APP = "Motion Syncher"

# ── Ultralytics / YOLO ───────────────────────────────────────────────────────
# YOLO writes settings.yaml, downloaded model weights, and run logs here.
if not os.environ.get("YOLO_CONFIG_DIR"):
    os.environ["YOLO_CONFIG_DIR"] = os.path.join(_user_data_dir(APP), "yolo")

# ── PyTorch JIT / inductor cache ─────────────────────────────────────────────
# torch.compile() and some ultralytics paths write compiled kernels here.
# The default ($HOME/.cache/torch) is fine, but explicitly setting it
# prevents accidental writes into a read-only _MEIPASS location.
if not os.environ.get("TORCHINDUCTOR_CACHE_DIR"):
    os.environ["TORCHINDUCTOR_CACHE_DIR"] = os.path.join(
        tempfile.gettempdir(), f"{APP.lower()}_torch_inductor"
    )

# ── Qt platform plugin path ───────────────────────────────────────────────────
# PySide6 locates its platform plugins relative to the executable.
# PyInstaller places them at <_MEIPASS>/PySide6/Qt/plugins/platforms, which
# PySide6 finds automatically, but set the variable explicitly as a fallback.
if getattr(sys, "frozen", False) and not os.environ.get("QT_PLUGIN_PATH"):
    candidate = os.path.join(sys._MEIPASS, "PySide6", "Qt", "plugins")  # type: ignore[attr-defined]
    if os.path.isdir(candidate):
        os.environ["QT_PLUGIN_PATH"] = candidate

# ── ROCm / HIP (Linux only) ───────────────────────────────────────────────────
# When the app was built against a ROCm-flavoured torch, the HIP runtime
# libraries are bundled inside <_MEIPASS>/torch/lib/.  The bootloader
# already prepends _MEIPASS to LD_LIBRARY_PATH, so no extra action is
# needed for library loading.
#
# HSA_OVERRIDE_GFX_VERSION lets users run on GPUs whose ISA is supported by
# the ROCm build but not listed in the device table (e.g. gfx803 / RX 480).
# Set it only if the user has not already overridden it themselves.
#
# Example: export HSA_OVERRIDE_GFX_VERSION=9.0.0  (for RDNA1 as gfx900)
# We do NOT set a default here because the correct value is hardware-specific.
