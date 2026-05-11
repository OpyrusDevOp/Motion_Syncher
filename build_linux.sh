#!/usr/bin/env bash
# build_linux.sh — Motion Syncher Linux builder
# ─────────────────────────────────────────────
# Usage:
#   ./build_linux.sh cuda [CUDA_TAG]     e.g.  ./build_linux.sh cuda cu124
#   ./build_linux.sh rocm [ROCM_TAG]     e.g.  ./build_linux.sh rocm rocm6.2
#   ./build_linux.sh cpu
#
# CUDA_TAG  defaults to cu130  (CUDA 12.4)
# ROCM_TAG  defaults to rocm7.2
#
# The script installs the requested torch variant into the active venv (or the
# system Python if no venv is active), then runs PyInstaller.
# Output lands in  dist/MotionSyncher-linux-<backend>/
#
# System packages required at BUILD time (install via your distro's package manager):
#   python3-dev  gcc  g++  patchelf  libgl1  libglib2.0-0
#
# System packages required at RUNTIME on the end-user machine:
#   libEGL1  libGL1  libglib2.0-0  libxcb-*    (Qt / OpenGL)
#   libusb-1.0-0                                (OAK / depthai)
#   mpv | ffplay | cvlc                         (audio playback)
#   pynput needs X11 or Wayland + evdev:
#     libx11-6  libxtst6  python3-evdev  (or) libwayland-client0

set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GRN='\033[0;32m'; YEL='\033[1;33m'; BLU='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${BLU}[build]${NC} $*"; }
ok()    { echo -e "${GRN}[build]${NC} $*"; }
warn()  { echo -e "${YEL}[build]${NC} $*"; }
die()   { echo -e "${RED}[build] ERROR:${NC} $*" >&2; exit 1; }

# ── Arguments ─────────────────────────────────────────────────────────────────
BACKEND="${1:-}"
case "$BACKEND" in
    cuda|rocm|cpu) ;;
    *) die "Usage: $0 cuda [cu124] | rocm [rocm6.2] | cpu" ;;
esac

# ── Torch index URLs ──────────────────────────────────────────────────────────
# Edit these lines to pin a different CUDA / ROCm release.
DEFAULT_CUDA_TAG="cu130"
DEFAULT_ROCM_TAG="rocm7.2"

CUDA_TAG="${2:-$DEFAULT_CUDA_TAG}"
ROCM_TAG="${2:-$DEFAULT_ROCM_TAG}"

PYTORCH_BASE="https://download.pytorch.org/whl"

case "$BACKEND" in
    cuda) TORCH_INDEX="${PYTORCH_BASE}/${CUDA_TAG}" ;;
    rocm) TORCH_INDEX="${PYTORCH_BASE}/${ROCM_TAG}" ;;
    cpu)  TORCH_INDEX="${PYTORCH_BASE}/cpu"          ;;
esac

info "Backend : $BACKEND"
[[ "$BACKEND" == "cuda" ]] && info "CUDA tag: $CUDA_TAG"
[[ "$BACKEND" == "rocm" ]] && info "ROCm tag: $ROCM_TAG"
info "Index   : $TORCH_INDEX"

# ── Sanity checks ─────────────────────────────────────────────────────────────
command -v python3 >/dev/null || die "python3 not found"
command -v pip     >/dev/null || die "pip not found"

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python  : $PY_VER"

# Minimum Python 3.10
python3 -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'" \
    || die "Python 3.10+ required (got $PY_VER)"

# Warn if no venv is active
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    warn "No virtual environment detected.  It is strongly recommended to"
    warn "build inside a dedicated venv:  python3 -m venv .venv && source .venv/bin/activate"
    read -rp "Continue anyway? [y/N] " yn
    [[ "${yn,,}" == "y" ]] || exit 1
fi

# ── ROCm GPU sanity check ─────────────────────────────────────────────────────
if [[ "$BACKEND" == "rocm" ]]; then
    if [[ ! -e /dev/kfd ]]; then
        warn "/dev/kfd not found — the ROCm kernel driver may not be loaded."
        warn "The build will succeed, but GPU inference won't work on this machine."
    fi
    if ! command -v rocm-smi &>/dev/null; then
        warn "rocm-smi not found — cannot verify GPU compatibility."
    else
        info "ROCm devices:"
        rocm-smi --showproductname 2>/dev/null | sed 's/^/         /' || true
    fi
fi

# ── CUDA GPU sanity check ─────────────────────────────────────────────────────
if [[ "$BACKEND" == "cuda" ]]; then
    if command -v nvidia-smi &>/dev/null; then
        info "CUDA devices:"
        nvidia-smi --query-gpu=name,driver_version,memory.total \
                   --format=csv,noheader 2>/dev/null | sed 's/^/         /' || true
    else
        warn "nvidia-smi not found — cannot verify CUDA GPU."
    fi
fi

# ── Install / upgrade build tools ─────────────────────────────────────────────
info "Installing build tools …"
pip install --quiet --upgrade pip wheel
pip install --quiet "pyinstaller>=6.10" "pyinstaller-hooks-contrib>=2025.0"

# ── Install correct torch variant ─────────────────────────────────────────────
info "Installing torch + torchvision from $TORCH_INDEX …"
pip install --quiet \
    torch \
    torchvision \
    --index-url "$TORCH_INDEX"

# Verify the installed torch can see the expected backend
if [[ "$BACKEND" == "cuda" ]]; then
    python3 -c "
import torch
if not torch.cuda.is_available():
    print('WARNING: torch.cuda.is_available() = False')
    print('         The build will still work; CUDA inference requires a compatible GPU at runtime.')
else:
    print(f'torch CUDA OK  — version {torch.version.cuda}')
" || true
fi

if [[ "$BACKEND" == "rocm" ]]; then
    python3 -c "
import torch
v = getattr(torch.version, 'hip', None)
if v:
    print(f'torch ROCm/HIP OK — {v}')
else:
    print('WARNING: torch does not report a HIP version — verify the ROCm wheel was installed.')
" || true
fi

# ── Install remaining requirements ────────────────────────────────────────────
info "Installing application requirements …"
pip install --quiet \
    "PySide6>=6.6" \
    "opencv-python>=4.8" \
    "ultralytics>=8.2" \
    "numpy>=1.24" \
    "pynput>=1.7.6"

# Optional: depthai for OAK camera support
if python3 -c "import depthai" 2>/dev/null; then
    ok "depthai already installed — OAK camera support included in build."
else
    warn "depthai not installed — OAK camera support will be DISABLED."
    warn "Install with:  pip install depthai"
    warn "Then re-run this script to include OAK support."
fi

# ── Run PyInstaller ───────────────────────────────────────────────────────────
# ── Ensure required directories exist ───────────────────────────────────────
# PyInstaller reads these paths from the spec; a missing directory causes a
# hard crash (FileNotFoundError) rather than a graceful warning.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for dir in hooks runtime_hooks; do
    if [[ ! -d "$SCRIPT_DIR/$dir" ]]; then
        warn "Creating missing directory: $dir/"
        mkdir -p "$SCRIPT_DIR/$dir"
    fi
done
# Placeholder so hooks/ is never empty (git does not track empty dirs)
touch "$SCRIPT_DIR/hooks/.gitkeep"

info "Running PyInstaller …"
export BUILD_BACKEND="$BACKEND"

python3 -m PyInstaller \
    --noconfirm \
    --clean \
    "$SCRIPT_DIR/motionsyncher.spec"

# ── Post-build report ─────────────────────────────────────────────────────────
DIST_DIR="dist/MotionSyncher-linux-${BACKEND}"

if [[ -d "$DIST_DIR" ]]; then
    info "Deduplicating identical files (symlink restoration) …"
    python3 -c "
import os, hashlib
from collections import defaultdict

def get_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(8192*4):
            h.update(chunk)
    return h.hexdigest()

dist_dir = '$DIST_DIR'
size_map = defaultdict(list)
for root, _, files in os.walk(dist_dir):
    for f in files:
        path = os.path.join(root, f)
        if os.path.isfile(path) and not os.path.islink(path):
            size_map[os.path.getsize(path)].append(path)

saved_bytes = 0
for size, paths in size_map.items():
    if len(paths) < 2 or size == 0: continue
    hash_map = defaultdict(list)
    for p in paths:
        hash_map[get_hash(p)].append(p)
    for h, p_list in hash_map.items():
        if len(p_list) > 1:
            target = p_list[0]
            for p in p_list[1:]:
                os.remove(p)
                os.link(target, p)
                saved_bytes += size
print(f'  Saved {saved_bytes / (1024**3):.2f} GB by hardlinking identical files.')
"

    ARCHIVE_NAME="MotionSyncher-linux-${BACKEND}.tar.xz"
    info "Compressing to dist/$ARCHIVE_NAME (this may take a few minutes) …"
    (cd dist && tar -cJf "$ARCHIVE_NAME" "MotionSyncher-linux-${BACKEND}")

    EXE_PATH="$DIST_DIR/MotionSyncher-linux-${BACKEND}"
    SIZE=$(du -sh "$DIST_DIR" 2>/dev/null | cut -f1)
    ARCHIVE_SIZE=$(du -sh "dist/$ARCHIVE_NAME" 2>/dev/null | cut -f1)
    
    ok "Build complete!"
    ok "  Directory : $DIST_DIR  ($SIZE)"
    ok "  Archive   : dist/$ARCHIVE_NAME  ($ARCHIVE_SIZE)"
    ok "  Executable: $EXE_PATH"
    echo
    info "Runtime system dependencies the end-user must have installed:"
    info "  sudo apt install libgl1 libegl1 libglib2.0-0 libxcb-xinerama0 \\"
    info "                   libxcb-cursor0 libusb-1.0-0 \\"
    info "                   mpv  # or ffplay / cvlc for audio"
    if [[ "$BACKEND" == "rocm" ]]; then
        echo
        warn "ROCm note: for GPUs not in the default device table, the user may need:"
        warn "  export HSA_OVERRIDE_GFX_VERSION=9.0.0   # adjust to their GPU's GFX version"
        warn "  $EXE_PATH"
    fi
else
    die "Expected output directory not found: $DIST_DIR"
fi
