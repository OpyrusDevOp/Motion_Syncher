# Motion Syncher
<img width="1876" height="990" alt="2026-05-06-165159_hyprshot" src="https://github.com/user-attachments/assets/1536d55b-970c-48be-910f-c0c478d943fd" />

A desktop application that maps recognized human body gestures to triggered actions — play audio, run shell commands, send keystrokes, or print to a console. Designed for **live shows and spectacles**, with a choreography sequencer that advances step-by-step as performers execute gestures on stage.

---

## Features

- **Dynamic gesture recognition** via YOLO-pose skeleton detection + DTW (Dynamic Time Warping)
- **Motion energy segmentation** — gestures are detected at natural boundaries (when the performer goes still), no fixed-window cutting
- **Choreography engine** — an ordered, repeatable list of (gesture → action) pairs; supports Sequential, Free, and Both modes
- **Quick Arm** — bind a single gesture to an action instantly from the toolbar, without building a full choreography
- **Triggerable functions**: shell command, audio playback, keystroke, console write
- **Live calibration feedback** — every detected segment reports its DTW distance so you can tune the threshold in real time
- **Persistent storage** — gestures and choreographies are auto-saved on exit and restored on next launch
- **Phase B ready** — OAK camera stub in place for Luxonis OAK-D-POE / OAK-1 integration (real 3D skeleton, on-device inference)

---

## Requirements

- Python 3.10+
- Webcam (Phase A) — Luxonis OAK-D-POE or OAK-1 planned for Phase B

```
PySide6
opencv-python
ultralytics       # YOLO-pose, model downloaded automatically on first run
numpy
pynput
pygame
```

---

## Installation

```bash
git clone <repo-url>
cd Motion_Syncher
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

The YOLO pose model (`yolov8n-pose.pt`, ~6 MB) is downloaded automatically on first launch.

---

## Usage

### 1 — Record gestures

1. Open the **Actions** tab on the right panel.
2. Type a gesture name (e.g. `wave`, `arms_cross`, `jump`).
3. Click **Record**, perform the gesture, then hold still. The segmenter detects when you finish.
4. Click **+ Add Take** to record more examples for the same gesture — improves recognition robustness.

> **Calibration tip:** After recording, perform the gesture and watch **Last segment: d=X.XXX**. Set the DTW threshold just above the highest distance you see. Unrelated movements should score clearly higher.

### 2 — Build a choreography

1. Open the **Choreography** panel.
2. Click **+ Add** to create a step: pick a gesture and associate an action (shell command, audio file, keystroke, or console text).
3. Reorder steps with **▲ / ▼**, enable **Loop** if needed.
4. Click **▶ Start** to begin detection. The active step is highlighted in green; completed steps dim out.

### 3 — Quick Arm (one-off trigger)

Use the **Quick Arm** bar at the bottom of the window to bind a single gesture to an action without touching the choreography. Toggle **Arm** to activate — the engine enters Both mode so the choreography still advances normally alongside it.

### Engine modes

| Mode | Behavior |
|---|---|
| **Sequential** | Waits for the exact gesture at the current step; advances only on match |
| **Free** | Any gesture fires its bound action immediately |
| **Both** | Free bindings fire instantly; choreography advances in parallel |

---

## Project structure

```
core/
  camera/          # Camera abstraction (Webcam + OAK stub)
  har/             # Pose detection, normalization, segmentation, DTW, recognizer
  functions/       # Triggerable actions (audio, shell, keystroke, console)
  choreography/    # Data models + engine
gui/
  widgets/         # Camera preview, choreography editor, action library, quick arm
  camera_thread.py # QThread: camera → pose → segment → recognize → emit
  main_window.py   # Top-level window, save/load, state persistence
main.py
```

---

## Roadmap

- **Phase B — OAK cameras**: replace MediaPipe 2D landmarks with real metric 3D skeleton from OAK-D-POE depth data; run pose model on-device (MyriadX VPU) for zero-CPU inference
- **Multi-person tracking**: assign gestures to specific performers by body position
- **LSTM classifier**: optional upgrade from DTW for larger gesture sets
- **OSC / MIDI output**: direct integration with lighting and sound consoles
- **C++ port**: Qt6 + depthai-core + ONNX Runtime for production performance
