# build_windows.ps1 - Motion Syncher Windows builder
# -------------------------------------------------------------
# Usage (from a Developer PowerShell or plain PowerShell):
#   .\build_windows.ps1 cuda [cu124]
#   .\build_windows.ps1 cpu
#
# CudaTag defaults to cu130 (CUDA 13.0).
# Output lands in  dist\MotionSyncher-windows-<backend>\
#
# Requirements:
#   Python 3.10+ (from python.org - NOT the Microsoft Store version)
#   Visual C++ Redistributable 2019+ (usually already present)
#   A venv is strongly recommended:
#     python -m venv .venv; .venv\Scripts\Activate.ps1

[CmdletBinding()]
param (
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("cuda", "cpu")]
    [string]$Backend,

    [Parameter(Mandatory = $false, Position = 1)]
    [string]$CudaTag = "cu130"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# -- Colour helpers ------------------------------------------------------------
function Info  { param($msg) Write-Host "[build] $msg" -ForegroundColor Cyan    }
function Ok    { param($msg) Write-Host "[build] $msg" -ForegroundColor Green   }
function Warn  { param($msg) Write-Host "[build] $msg" -ForegroundColor Yellow  }
function Fail  { param($msg) Write-Host "[build] ERROR: $msg" -ForegroundColor Red; exit 1 }

# -- Torch index URLs ----------------------------------------------------------
# Edit CudaTag parameter default (above) to pin a different CUDA release.
# Available tags: cu118, cu121, cu124, cu126, ...
$PyTorchBase = "https://download.pytorch.org/whl"
$TorchIndex  = if ($Backend -eq "cuda") { "$PyTorchBase/$CudaTag" } else { "$PyTorchBase/cpu" }

Info "Backend : $Backend"
if ($Backend -eq "cuda") { Info "CUDA tag: $CudaTag" }
Info "Index   : $TorchIndex"

# -- Sanity checks -------------------------------------------------------------
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Fail "python not found in PATH. Install from https://python.org"
}
if (-not (Get-Command pip -ErrorAction SilentlyContinue)) {
    Fail "pip not found in PATH."
}

$PyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Info "Python  : $PyVer"
python -c "import sys; assert sys.version_info >= (3,10), 'need 3.10+'" 2>$null
if ($LASTEXITCODE -ne 0) { Fail "Python 3.10+ required (got $PyVer)" }

# Warn if no venv
if (-not $env:VIRTUAL_ENV) {
    Warn "No virtual environment detected."
    Warn "Recommended:  python -m venv .venv; .venv\Scripts\Activate.ps1"
    $yn = Read-Host "Continue without a venv? [y/N]"
    if ($yn -notmatch "^[yY]$") { exit 1 }
}

# -- CUDA GPU check ------------------------------------------------------------
if ($Backend -eq "cuda") {
    if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
        Info "CUDA devices:"
        $nvidiaOutput = nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader 2>$null
        if ($nvidiaOutput) {
            $nvidiaOutput | ForEach-Object { Info "  $_" }
        }
    } else {
        Warn "nvidia-smi not found - cannot verify CUDA GPU."
    }
}

# -- Install / upgrade build tools ---------------------------------------------
Info "Upgrading pip + build tools ..."
python -m pip install --quiet --upgrade pip wheel
python -m pip install --quiet "pyinstaller>=6.10" "pyinstaller-hooks-contrib>=2025.0"

# -- Install correct torch variant ---------------------------------------------
Info "Installing torch + torchvision from $TorchIndex ..."
python -m pip install --quiet torch torchvision --index-url $TorchIndex

# Verify CUDA availability
if ($Backend -eq "cuda") {
    $torchCheck = @"
import torch
if torch.cuda.is_available():
    print(f'torch CUDA OK - {torch.version.cuda}')
else:
    print('WARNING: torch.cuda.is_available() = False')
    print('         The build succeeds; CUDA inference needs a compatible GPU at runtime.')
"@
    python -c $torchCheck 2>$null
}

# -- Install remaining requirements --------------------------------------------
Info "Installing application requirements ..."
python -m pip install --quiet `
    "PySide6>=6.6" `
    "opencv-python>=4.8" `
    "ultralytics>=8.2" `
    "numpy>=1.24" `
    "pynput>=1.7.6"

# Optional: depthai
$hasDepthai = python -c "import depthai; print('yes')" 2>$null
if ($hasDepthai -eq "yes") {
    Ok "depthai installed - OAK camera support included."
} else {
    Warn "depthai not installed - OAK camera support DISABLED."
    Warn "Install with:  pip install depthai  then re-run."
}

# -- Run PyInstaller -----------------------------------------------------------
# -- Ensure required directories exist ---------------------------------------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
foreach ($dir in @("hooks", "runtime_hooks")) {
    $full = Join-Path $ScriptDir $dir
    if (-not (Test-Path $full)) {
        Warn "Creating missing directory: $dir\"
        New-Item -ItemType Directory -Path $full | Out-Null
    }
}
# Placeholder so hooks\ is never empty (git does not track empty dirs)
New-Item -ItemType File -Force -Path (Join-Path $ScriptDir "hooks\.gitkeep") | Out-Null

Info "Running PyInstaller ..."
$env:BUILD_BACKEND = $Backend
$SpecFile = Join-Path $ScriptDir "motionsyncher.spec"
python -m PyInstaller --noconfirm --clean $SpecFile
if ($LASTEXITCODE -ne 0) { Fail "PyInstaller exited with code $LASTEXITCODE" }

# -- Post-build report ---------------------------------------------------------
$DistDir = "dist\MotionSyncher-windows-$Backend"
$ExePath  = "$DistDir\MotionSyncher-windows-$Backend.exe"

if (Test-Path $DistDir) {
    $ArchiveName = "MotionSyncher-windows-$Backend.zip"
    $ArchivePath = "dist\$ArchiveName"
    Info "Compressing to $ArchivePath (this may take a few minutes) ..."
    if (Test-Path $ArchivePath) { Remove-Item $ArchivePath -Force }
    Compress-Archive -Path $DistDir -DestinationPath $ArchivePath -CompressionLevel Optimal

    $SizeMB = [math]::Round((Get-ChildItem $DistDir -Recurse | Measure-Object Length -Sum).Sum / 1MB, 0)
    $ArchiveSizeMB = [math]::Round((Get-Item $ArchivePath).Length / 1MB, 0)
    
    Ok "Build complete!"
    Ok "  Directory : $DistDir  (~${SizeMB} MB)"
    Ok "  Archive   : $ArchivePath  (~${ArchiveSizeMB} MB)"
    Ok "  Executable: $ExePath"
    Write-Host ""
    Info "The user needs Visual C++ Redistributable 2019+ on their machine:"
    Info "  https://aka.ms/vs/17/release/vc_redist.x64.exe"
    Info "Audio playback requires mpv, ffplay, or cvlc in PATH."
} else {
    Fail "Expected output not found: $DistDir"
}