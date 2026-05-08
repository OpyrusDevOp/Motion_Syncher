import json
import pickle
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QLabel,
    QComboBox,
    QToolButton,
    QToolBar,
    QProgressBar,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtCore import Qt, QTimer, QSettings, QStandardPaths

from core.camera.webcam import WebcamCamera
from core.camera import oak as oak_module
from core.choreography.engine import ChoreographyEngine, EngineMode
from core.choreography.models import Choreography, Pair
from core.functions import function_from_dict, load_user_plugins
from core.functions.console_write import output_queue
from gui.camera_thread import CameraThread
from gui.widgets.camera_preview import CameraPreviewWidget
from gui.widgets.action_library import ActionLibraryWidget
from gui.widgets.choreography_editor import ChoreographyEditorWidget
from gui.widgets.quick_arm import QuickArmWidget

# Stored in each QComboBox item's UserRole
_ROLE = Qt.ItemDataRole.UserRole


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Motion Syncher")
        self.setMinimumSize(1280, 720)

        self.camera_thread = CameraThread()
        self.engine = ChoreographyEngine(self)
        self._load_plugins()

        # Debounced autosave: fires 1 s after the last change
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(1000)
        self._save_timer.timeout.connect(self._autosave)

        self._build_ui()
        self._connect_signals()
        self._start_console_flush()
        self._restore_state()
        self._autoload()

    # ------------------------------------------------------------------
    # Plugin loading
    # ------------------------------------------------------------------

    def _load_plugins(self) -> None:
        plugins_dir = Path(__file__).parent.parent / "plugins"
        found = load_user_plugins([plugins_dir])
        if found:
            print(f"[Plugins] registered: {found}")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # --- Main toolbar ---
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)

        self.act_start = QAction("▶  Start", self)
        self.act_stop = QAction("⏹  Stop", self)
        self.act_reset = QAction("↺  Reset", self)
        self.act_reload = QAction("⟳  Reload", self)
        self.act_reload.setToolTip("Reload gestures and choreography from disk")
        tb.addAction(self.act_start)
        tb.addAction(self.act_stop)
        tb.addSeparator()
        tb.addAction(self.act_reset)
        tb.addAction(self.act_reload)
        tb.addSeparator()

        # Camera selector with refresh button
        tb.addWidget(QLabel("  Camera: "))
        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(220)
        self.camera_combo.setToolTip(
            "Select a camera source.\n"
            "OAK devices appear here automatically when depthai is installed."
        )
        tb.addWidget(self.camera_combo)

        self._refresh_cam_btn = QToolButton()
        self._refresh_cam_btn.setText("⟳")
        self._refresh_cam_btn.setToolTip("Re-scan for cameras and OAK devices")
        self._refresh_cam_btn.clicked.connect(self._populate_camera_combo)
        tb.addWidget(self._refresh_cam_btn)

        self._populate_camera_combo()

        # Live indicator — right-aligned via spacer
        spacer = QWidget()
        spacer.setMinimumWidth(20)
        tb.addWidget(spacer)
        self.live_lbl = QLabel("● STOPPED")
        self.live_lbl.setStyleSheet(
            "color: #c0392b; font-weight: bold; padding-right: 8px;"
        )
        tb.addWidget(self.live_lbl)

        # --- Quick Arm toolbar ---
        qa_tb = QToolBar("Quick Arm")
        qa_tb.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, qa_tb)
        self.quick_arm = QuickArmWidget()
        qa_tb.addWidget(self.quick_arm)

        # --- Central splitter: [camera | choreography | side panel] ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        # Left: camera preview
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(4, 4, 4, 4)

        self.preview = CameraPreviewWidget()
        left_lay.addWidget(self.preview, stretch=1)

        energy_row = QHBoxLayout()
        energy_row.addWidget(QLabel("Motion:"))
        self.energy_bar = QProgressBar()
        self.energy_bar.setRange(0, 100)
        self.energy_bar.setTextVisible(False)
        self.energy_bar.setMaximumHeight(10)
        energy_row.addWidget(self.energy_bar)
        left_lay.addLayout(energy_row)

        self.gesture_lbl = QLabel("Detected: —")
        self.gesture_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gesture_lbl.setStyleSheet("font-size: 14px; padding: 4px;")
        left_lay.addWidget(self.gesture_lbl)

        splitter.addWidget(left)

        # Center: choreography editor
        self.chor_editor = ChoreographyEditorWidget()
        splitter.addWidget(self.chor_editor)

        # Right: tabs
        right_tabs = QTabWidget()
        self.action_lib = ActionLibraryWidget(self.camera_thread)
        right_tabs.addTab(self.action_lib, "Actions")

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("Console output appears here...")
        right_tabs.addTab(self.console, "Console")

        splitter.addWidget(right_tabs)
        splitter.setSizes([400, 500, 380])

        # Status bar
        self.step_lbl = QLabel("Step: —")
        self.statusBar().addPermanentWidget(self.step_lbl)
        self.statusBar().showMessage("Ready — press Start to begin detection")

        self._build_menu()

    def _build_menu(self):
        menu = self.menuBar()

        file_m = menu.addMenu("File")
        file_m.addAction("Save Project...", self._save_project, "Ctrl+S")
        file_m.addAction("Load Project...", self._load_project, "Ctrl+O")

        engine_m = menu.addMenu("Engine Mode")
        mode_group = QActionGroup(self)
        mode_group.setExclusive(True)
        for label, mode in [
            ("Sequential", EngineMode.SEQUENTIAL),
            ("Free", EngineMode.FREE),
            ("Both", EngineMode.BOTH),
        ]:
            act = QAction(label, self, checkable=True)
            act.triggered.connect(lambda checked, m=mode: self.engine.set_mode(m))
            mode_group.addAction(act)
            engine_m.addAction(act)
        mode_group.actions()[0].setChecked(True)

    # ------------------------------------------------------------------
    # Camera combo population
    # ------------------------------------------------------------------

    def _populate_camera_combo(self) -> None:
        """
        Rebuild the camera combo box:
          - Webcam 0–3 (always present)
          - Any OAK devices detected via depthai (when installed)

        Each item carries a dict in UserRole:
            {"type": "webcam", "index": int}
            {"type": "oak",    "mx_id": str | None}
        """
        prev_data = self.camera_combo.currentData(_ROLE)  # preserve selection
        self.camera_combo.clear()

        # -- Webcams --
        for i in range(4):
            self.camera_combo.addItem(f"Webcam {i}", {"type": "webcam", "index": i})

        # -- OAK devices --
        oak_devices = oak_module.list_devices()
        if not oak_module.is_available():
            # depthai not installed — add a disabled placeholder so users know
            self.camera_combo.addItem(
                "OAK (install depthai)", {"type": "oak_unavailable"}
            )
            idx = self.camera_combo.count() - 1
            # Make the entry visually greyed out and non-selectable
            model = self.camera_combo.model()
            from PySide6.QtGui import QStandardItem

            item = model.item(idx)
            if item:
                from PySide6.QtCore import Qt as _Qt

                item.setFlags(item.flags() & ~_Qt.ItemFlag.ItemIsEnabled)
        else:
            if oak_devices:
                for dev in oak_devices:
                    label = dev["label"]
                    self.camera_combo.addItem(
                        f"⬡ {label}",
                        {"type": "oak", "mx_id": dev["mx_id"]},
                    )
            # Always offer "OAK (auto)" as a fallback for single-device setups
            self.camera_combo.addItem(
                "⬡ OAK (auto-detect)",
                {"type": "oak", "mx_id": None},
            )

        # Restore previous selection if it still exists
        if prev_data:
            for i in range(self.camera_combo.count()):
                if self.camera_combo.itemData(i, _ROLE) == prev_data:
                    self.camera_combo.setCurrentIndex(i)
                    break

        n_oak = len(oak_devices)
        if oak_module.is_available():
            tip = (
                f"{n_oak} OAK device(s) found"
                if n_oak
                else "No OAK devices found (auto-detect available)"
            )
        else:
            tip = "depthai not installed — OAK support unavailable"
        self.statusBar().showMessage(tip, 4000)

    def _make_camera(self):
        """Instantiate the correct Camera subclass from the current combo selection."""
        data = self.camera_combo.currentData(_ROLE) or {}
        cam_type = data.get("type", "webcam")

        if cam_type == "webcam":
            return WebcamCamera(data.get("index", 0))

        if cam_type == "oak":
            if not oak_module.is_available():
                QMessageBox.warning(
                    self,
                    "OAK not available",
                    "depthai is not installed.\n\n"
                    "Install it with:\n    pip install depthai",
                )
                return None
            from core.camera.oak import OAKCamera

            return OAKCamera(mx_id=data.get("mx_id"))

        if cam_type == "oak_unavailable":
            QMessageBox.information(
                self,
                "OAK support unavailable",
                "Install depthai to use Luxonis OAK cameras:\n\n"
                "    pip install depthai\n\nThen restart the app.",
            )
            return None

        return WebcamCamera(0)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self):
        self.camera_thread.frame_ready.connect(self.preview.update_frame)
        self.camera_thread.gesture_detected.connect(self._on_gesture_detected)
        self.camera_thread.motion_energy_updated.connect(self._on_energy)

        self.engine.function_triggered.connect(self._on_function_triggered)
        self.engine.step_changed.connect(self._on_step_changed)
        self.engine.choreography_done.connect(self._on_choreography_done)

        self.chor_editor.choreography_changed.connect(self._sync_choreography)
        self.chor_editor.choreography_changed.connect(self._schedule_autosave)
        self.action_lib.gesture_list_changed.connect(self._update_gesture_list)
        self.action_lib.gesture_list_changed.connect(self._schedule_autosave)

        self.act_start.triggered.connect(self._start_camera)
        self.act_stop.triggered.connect(self._stop_camera)
        self.act_reset.triggered.connect(self._reset)
        self.act_reload.triggered.connect(self._manual_reload)

        self.quick_arm.armed.connect(self._on_quick_armed)
        self.quick_arm.disarmed.connect(self._on_quick_disarmed)

    # ------------------------------------------------------------------
    # Camera
    # ------------------------------------------------------------------

    def _start_camera(self):
        if self.camera_thread.isRunning():
            self.camera_thread.stop()

        camera = self._make_camera()
        if camera is None:
            return  # user was already warned via a dialog

        self.camera_thread.set_camera(camera)
        self.camera_thread.start()
        self.live_lbl.setText("● LIVE")
        self.live_lbl.setStyleSheet(
            "color: #27ae60; font-weight: bold; padding-right: 8px;"
        )
        self.statusBar().showMessage(f"{camera.name} started")

    def _stop_camera(self):
        self.camera_thread.stop()
        self.live_lbl.setText("● STOPPED")
        self.live_lbl.setStyleSheet(
            "color: #c0392b; font-weight: bold; padding-right: 8px;"
        )
        self.statusBar().showMessage("Camera stopped")

    # ------------------------------------------------------------------
    # Gesture / engine handlers
    # ------------------------------------------------------------------

    def _on_gesture_detected(self, name: str, dist: float):
        self.gesture_lbl.setText(f"Detected: <b>{name}</b>  (d={dist:.3f})")
        self.engine.on_gesture(name)

    def _on_energy(self, energy: float):
        self.energy_bar.setValue(min(100, int(energy * 1500)))

    def _on_function_triggered(self, gesture: str, func_name: str):
        self.statusBar().showMessage(f"▶  {func_name}  ←  {gesture}")

    def _on_step_changed(self, step: int):
        total = len(self.chor_editor.get_choreography().pairs)
        self.step_lbl.setText(f"Step: {step}/{total}")
        self.chor_editor.highlight_step(step)

    def _on_choreography_done(self):
        self.chor_editor.clear_highlight()
        self.step_lbl.setText("Done")
        self.statusBar().showMessage("Choreography complete")

    def _reset(self):
        self.engine.reset()
        self.chor_editor.highlight_step(0)
        self.statusBar().showMessage("Reset to step 1")

    def _sync_choreography(self):
        self.engine.set_choreography(self.chor_editor.get_choreography())

    def _update_gesture_list(self):
        gestures = self.camera_thread.recognizer.list_gestures()
        self.chor_editor.set_available_gestures(gestures)
        self.quick_arm.update_gestures(gestures)

    # ------------------------------------------------------------------
    # Quick Arm
    # ------------------------------------------------------------------

    def _on_quick_armed(self, gesture: str, fn: object):
        self.engine.set_free_bindings({gesture: fn})
        self.engine.set_mode(EngineMode.BOTH)
        self.statusBar().showMessage(f"Quick arm: {gesture} → {fn.name}")

    def _on_quick_disarmed(self):
        self.engine.set_free_bindings({})
        self.engine.set_mode(EngineMode.SEQUENTIAL)
        self.statusBar().showMessage("Quick arm disarmed")

    # ------------------------------------------------------------------
    # Console
    # ------------------------------------------------------------------

    def _start_console_flush(self):
        self._flush_timer = QTimer(self)
        self._flush_timer.timeout.connect(self._flush_console)
        self._flush_timer.start(100)

    def _flush_console(self):
        while not output_queue.empty():
            self.console.append(output_queue.get_nowait())

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def _save_project(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "Motion Syncher Project (*.msync.json)"
        )
        if not path:
            return
        path = Path(path)

        chor = self.chor_editor.get_choreography()
        project = {
            "name": chor.name,
            "loop": chor.loop,
            "pairs": [
                {"gesture": p.gesture, "function": p.function.to_dict()}
                for p in chor.pairs
            ],
        }
        path.write_text(json.dumps(project, indent=2))

        tpl_path = path.with_suffix("").with_suffix(".templates.pkl")
        templates_data = {
            name: tpl.sequences
            for name, tpl in self.camera_thread.recognizer._templates.items()
        }
        tpl_path.write_bytes(pickle.dumps(templates_data))
        self.statusBar().showMessage(f"Saved to {path.name}")

    def _load_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Project", "", "Motion Syncher Project (*.msync.json)"
        )
        if not path:
            return
        path = Path(path)

        try:
            project = json.loads(path.read_text())
        except Exception as exc:
            QMessageBox.critical(self, "Load error", str(exc))
            return

        tpl_path = path.with_suffix("").with_suffix(".templates.pkl")
        if tpl_path.exists():
            templates_data: dict = pickle.loads(tpl_path.read_bytes())
            rec = self.camera_thread.recognizer
            rec.clear()
            for name, sequences in templates_data.items():
                for seq in sequences:
                    rec.add_template(name, seq)
            self._update_gesture_list()

        pairs = [
            Pair(p["gesture"], function_from_dict(p["function"]))
            for p in project.get("pairs", [])
        ]
        chor = Choreography(
            pairs=pairs, loop=project.get("loop", False), name=project.get("name", "")
        )
        self.chor_editor.load_choreography(chor)
        self.engine.set_choreography(chor)
        self.statusBar().showMessage(f"Loaded {path.name}")

    # ------------------------------------------------------------------
    # Persistent storage
    # ------------------------------------------------------------------

    def _schedule_autosave(self) -> None:
        self._save_timer.start()

    def _manual_reload(self) -> None:
        self._autoload()
        self.statusBar().showMessage("Reloaded from disk", 3000)

    def _auto_data_dir(self) -> Path:
        base = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        )
        p = Path(base) / "default"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _autosave(self) -> None:
        d = self._auto_data_dir()
        chor = self.chor_editor.get_choreography()
        project = {
            "name": chor.name,
            "loop": chor.loop,
            "pairs": [
                {"gesture": p.gesture, "function": p.function.to_dict()}
                for p in chor.pairs
            ],
        }
        (d / "project.json").write_text(json.dumps(project, indent=2))

        templates_data = {
            name: tpl.sequences
            for name, tpl in self.camera_thread.recognizer._templates.items()
        }
        (d / "templates.pkl").write_bytes(pickle.dumps(templates_data))
        self.statusBar().showMessage("Saved", 2000)

    def _autoload(self) -> None:
        d = self._auto_data_dir()
        proj_file = d / "project.json"
        tpl_file = d / "templates.pkl"

        if tpl_file.exists():
            templates_data: dict = pickle.loads(tpl_file.read_bytes())
            rec = self.camera_thread.recognizer
            rec.clear()
            for name, sequences in templates_data.items():
                for seq in sequences:
                    rec.add_template(name, seq)

        self._update_gesture_list()
        self.action_lib._refresh_list()

        if proj_file.exists():
            try:
                project = json.loads(proj_file.read_text())
            except Exception:
                return
            pairs = [
                Pair(p["gesture"], function_from_dict(p["function"]))
                for p in project.get("pairs", [])
            ]
            chor = Choreography(
                pairs=pairs,
                loop=project.get("loop", False),
                name=project.get("name", ""),
            )
            self.chor_editor.load_choreography(chor)
            self.engine.set_choreography(chor)

    def _save_state(self) -> None:
        s = QSettings()
        s.setValue("window/geometry", self.saveGeometry())
        s.setValue("camera/combo_data", self.camera_combo.currentData(_ROLE))
        rec = self.action_lib.recognition_settings()
        s.setValue("recognition/threshold", rec["threshold"])
        s.setValue("recognition/cooldown", rec["cooldown"])
        s.setValue("recognition/motion", rec["motion"])
        s.setValue("performance/skip_frames", rec["skip_frames"])
        s.setValue("performance/imgsz", rec["imgsz"])

    def _restore_state(self) -> None:
        s = QSettings()
        geom = s.value("window/geometry")
        if geom:
            self.restoreGeometry(geom)

        # Restore camera selection by matching stored data dict
        saved_data = s.value("camera/combo_data")
        if saved_data:
            for i in range(self.camera_combo.count()):
                if self.camera_combo.itemData(i, _ROLE) == saved_data:
                    self.camera_combo.setCurrentIndex(i)
                    break
        else:
            # Legacy: old save used camera/index (int) for webcams
            cam = s.value("camera/index", 0, type=int)
            for i in range(self.camera_combo.count()):
                d = self.camera_combo.itemData(i, _ROLE) or {}
                if d.get("type") == "webcam" and d.get("index") == cam:
                    self.camera_combo.setCurrentIndex(i)
                    break

        rec = {
            "threshold": s.value("recognition/threshold", 0.30, type=float),
            "cooldown": s.value("recognition/cooldown", 1.5, type=float),
            "motion": s.value("recognition/motion", 0.02, type=float),
            "skip_frames": s.value("performance/skip_frames", 2, type=int),
            "imgsz": s.value("performance/imgsz", 320, type=int),
        }
        self.action_lib.apply_recognition_settings(rec)

    # ------------------------------------------------------------------

    def closeEvent(self, event):
        self.camera_thread.stop()
        self._autosave()
        self._save_state()
        super().closeEvent(event)
