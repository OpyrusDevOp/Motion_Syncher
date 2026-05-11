# -*- mode: python ; coding: utf-8 -*-
# motionsyncher.spec
#
# Build via the provided shell / PowerShell scripts — do NOT invoke
# pyinstaller directly.  The scripts set BUILD_BACKEND before calling
# pyinstaller, which this spec reads to name the output directory.
#
# Supported backends
#   cuda   — NVIDIA GPU  (Windows + Linux)
#   rocm   — AMD GPU     (Linux only)
#   cpu    — CPU-only    (Windows + Linux)
#
# Output (always --onedir):
#   dist/MotionSyncher-<os>-<backend>/MotionSyncher[.exe]
#
# Notes
# ─────
# • UPX is intentionally disabled: it corrupts torch's CUDA/ROCm shared
#   libraries and triggers false-positive AV detections on Windows.
# • The plugins/ directory is copied into the bundle so end-users can drop
#   additional .py plugins there without rebuilding.
# • Hook coverage (pyinstaller-hooks-contrib 2026.5):
#     torch       ✓  (collects all .so/.dll, nvidia-* hidden imports, MKL)
#     ultralytics ✓  (collects .yaml configs, enables pyz+py mode)
#     cv2         ✓
#     pynput      ✓
#     depthai     ✗  → provided by hooks/hook-depthai.py

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

# ── Parameters injected by build scripts ─────────────────────────────────────
BACKEND  = os.environ.get("BUILD_BACKEND", "cpu")   # cuda | rocm | cpu
PLATFORM = "windows" if sys.platform == "win32" else "linux"

print(f"[spec] platform={PLATFORM}  backend={BACKEND}  python={sys.version}")

# ── Path helper ───────────────────────────────────────────────────────────────
# SPECPATH is injected by PyInstaller and always points to the directory that
# contains this .spec file — independent of where `pyinstaller` was invoked.
# Use it for every file-system reference so the build is invocation-location
# agnostic.
_HERE = Path(SPECPATH)  # noqa: F821  (SPECPATH is a PyInstaller built-in)

def _p(*parts: str) -> str:
    """Absolute path rooted at the spec file's directory."""
    return str(_HERE.joinpath(*parts))

# ── Helper: silent collect_all ────────────────────────────────────────────────
def _collect(pkg: str):
    try:
        d, b, h = collect_all(pkg)
        print(f"[spec]   {pkg}: {len(d)} data, {len(b)} bin, {len(h)} hidden")
        return d, b, h
    except Exception as exc:
        print(f"[spec]   {pkg}: SKIPPED ({exc})")
        return [], [], []

print("[spec] collecting packages …")

# Packages with upstream hooks — collect_all() still supplements them
pyside6_d, pyside6_b, pyside6_h = _collect("PySide6")
numpy_d,   numpy_b,   numpy_h   = _collect("numpy")

# Optional: depthai (OAK cameras — Phase B)
oak_d, oak_b, oak_h = _collect("depthai")

# Optional: torchvision (some ultralytics ops need it)
tv_d, tv_b, tv_h = _collect("torchvision")

# ── Aggregate ─────────────────────────────────────────────────────────────────
all_datas = (
    pyside6_d + numpy_d + oak_d + tv_d
    # Bundle the plugins directory so users can add .py plugins post-install.
    # Path resolution in gui/main_window.py:
    #   Path(__file__).parent.parent / "plugins"
    # In a frozen --onedir build __file__ == <_MEIPASS>/gui/main_window.pyc,
    # so parent.parent == <_MEIPASS> == the directory next to the executable.
    + [(_p("plugins"), "plugins")]
)

all_binaries = pyside6_b + numpy_b + oak_b + tv_b

all_hiddenimports = (
    pyside6_h + numpy_h + oak_h + tv_h
    + collect_submodules("core")    # core.camera, core.har, core.choreography, core.functions
    + collect_submodules("gui")     # gui.widgets.*
    + [
        # Standard-library modules used via dynamic import / string-based loading
        "importlib.util",
        "importlib.machinery",
        "queue",
        "pickle",
        "json",
        "pathlib",
        "subprocess",
        "signal",
        "threading",
        # pynput platform backends (the hook adds the right one per OS;
        # listing both is harmless — the unused one simply won't import)
        "pynput.keyboard._xorg",
        "pynput.mouse._xorg",
        "pynput.keyboard._win32",
        "pynput.mouse._win32",
        "pynput.keyboard._darwin",
        "pynput.mouse._darwin",
        # ultralytics internals accessed at prediction time
        "ultralytics.nn.tasks",
        "ultralytics.nn.modules",
        "ultralytics.nn.modules.block",
        "ultralytics.nn.modules.conv",
        "ultralytics.nn.modules.head",
        "ultralytics.utils.ops",
        "ultralytics.utils.checks",
        # torch internals sometimes missed on first import scan
        "torch.distributions",
        "torch.testing",
    ]
)

# ── Excludes — trim packages that are definitely unused ──────────────────────
# Be conservative: only exclude things with zero chance of being needed.
excludes = [
    "tkinter", "_tkinter",
    "matplotlib",
    "scipy",
    "pandas",
    "IPython", "ipykernel", "jupyter_client", "notebook",
    "sphinx",
    "pytest", "py.test",
    # We don't export ONNX models at runtime
    "onnx",
    "onnxscript",
    # Exclude unused heavy PySide6 modules
    "PySide6.QtWebEngine",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtNetwork",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtXml",
    "PySide6.Qt3D",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    # Exclude PyTorch submodules not needed for inference
    "triton",
    "tensorboard",
    "torch.utils.tensorboard",
]

# ── Runtime hooks ─────────────────────────────────────────────────────────────
# Guard with existence check so a missing file degrades to a warning instead
# of crashing the build.
_rthook = _HERE / "runtime_hooks" / "set_env.py"
if _rthook.exists():
    _runtime_hooks = [str(_rthook)]
else:
    print(
        f"[spec] WARNING: runtime hook not found at {_rthook}\n"
        "       Create runtime_hooks/set_env.py or the YOLO/Qt env vars won't\n"
        "       be configured in the frozen app.  Build continues without it."
    )
    _runtime_hooks = []

# ── Analysis ──────────────────────────────────────────────────────────────────
block_cipher = None

a = Analysis(
    [_p("main.py")],
    pathex=[str(_HERE)],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    # hooks/ contains hook-depthai.py; upstream hooks are found automatically
    # by pyinstaller-hooks-contrib without listing their directory here.
    hookspath=[_p("hooks")],
    hooksconfig={},
    runtime_hooks=_runtime_hooks,
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ── Filter bloat and prevent patchelf corruption ──────────────────────────────
# patchelf inflates massive ROCm/CUDA .so files by gigabytes. Since torch wheels
# already have correct RPATHs, we move them from binaries to datas so PyInstaller
# copies them unmodified. We also strip C++ headers and test suites.
def optimize_bundle(binaries, datas):
    new_binaries = []
    new_datas = []
    
    # 1. Move torch binaries to datas to avoid patchelf
    for dest, src, type_ in binaries:
        dest_norm = dest.replace("\\", "/")
        if "torch" in dest_norm and dest_norm.endswith(".so"):
            new_datas.append((dest, src, "DATA"))
        else:
            new_binaries.append((dest, src, type_))
            
    # 2. Filter out bloat from datas
    for dest, src, type_ in datas:
        dest_norm = dest.replace("\\", "/")
        if "/include/" in dest_norm or "/test/" in dest_norm:
            continue
        if dest_norm.endswith(".a") or dest_norm.endswith(".pdb"):
            continue
        new_datas.append((dest, src, type_))
        
    # 3. Deduplicate (datas can sometimes get duplicate entries)
    unique_datas = {}
    for dest, src, type_ in new_datas:
        unique_datas[dest] = (dest, src, type_)
        
    return new_binaries, list(unique_datas.values())

a.binaries, a.datas = optimize_bundle(a.binaries, a.datas)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Output naming ─────────────────────────────────────────────────────────────
exe_name = f"MotionSyncher-{PLATFORM}-{BACKEND}"

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # --onedir: binaries go into COLLECT, not the exe
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,             # stripping breaks torch on Linux
    upx=False,               # UPX corrupts torch CUDA/ROCm .so files — keep OFF
    console=True,            # set False for a release build with no terminal
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,               # replace with "assets/icon.ico" (Win) / ".icns" (Mac)
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=exe_name,
)
