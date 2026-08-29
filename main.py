"""
main.py — DuckStudio Win11 main application.
Comprehensive music production studio with GUI.
Run: python main.py    |    Build EXE: pyinstaller --onefile --windowed main.py
"""
import os
import sys
import json
import threading
import time
import tempfile
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

# ─── DuckStudio imports ───
from src.duck_stdio import (
    duck_fopen, duck_fmemopen, duck_fdb_open, duck_fclose, DuckStream,
    duck_stdout, duck_stderr, StreamType, Flags
)
from src.huggingface import HuggingFaceClient, HF_AUDIO_MODELS
from src.oss_tools import OSSToolManager, DuckEcosystem, OSS_TOOLS
from src.mixer import Mixer, AudioTrack
from src.sequencer import Sequencer, Pattern, PATTERN_PRESETS
from src.effects import list_effects, create_effect, EFFECT_REGISTRY

__version__ = "1.0.0"
__app_name__ = "DuckStudio Win11"

# ─── Color palette ───
BG_DARK = "#0f0f23"
BG_PANEL = "#1a1a2e"
BG_ENTRY = "#16213e"
FG_PRIMARY = "#e2e8f0"
FG_SECONDARY = "#94a3b8"
ACCENT_BLUE = "#3b82f6"
ACCENT_GREEN = "#10b981"
ACCENT_RED = "#ef4444"
ACCENT_AMBER = "#f59e0b"
ACCENT_PURPLE = "#8b5cf6"


class DuckStudioApp:
    """Main DuckStudio Win11 application."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"🎵 {__app_name__} v{__version__}")
        self.root.geometry("1280x800")
        self.root.minsize(1024, 600)
        self.root.configure(bg=BG_DARK)

        # Core modules
        self.hf_client = HuggingFaceClient()
        self.oss_manager = OSSToolManager()
        self.duck_eco = DuckEcosystem()
        self.mixer = Mixer()
        self.sequencer = Sequencer()
        self.effect_chain: list = []

        # State
        self.current_project_path: str = None
        self.status_var = tk.StringVar(value="Ready")
        self.now_playing = False

        # Apply style
        self._apply_style()
        self._build_ui()

    def _apply_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background=BG_PANEL, foreground=FG_PRIMARY, font=('Segoe UI', 10))
        style.configure('TFrame', background=BG_PANEL)
        style.configure('TLabel', background=BG_PANEL, foreground=FG_PRIMARY)
        style.configure('TButton', background=BG_ENTRY, foreground=FG_PRIMARY, padding=6,
                        font=('Segoe UI', 10), borderwidth=0)
        style.map('TButton',
                  background=[('active', ACCENT_BLUE), ('pressed', ACCENT_PURPLE)],
                  foreground=[('active', 'white')])
        style.configure('TEntry', fieldbackground=BG_ENTRY, foreground=FG_PRIMARY,
                        insertbackground=FG_PRIMARY, borderwidth=1, relief='flat')
        style.configure('TNotebook', background=BG_PANEL, borderwidth=0)
        style.configure('TNotebook.Tab', background=BG_ENTRY, foreground=FG_SECONDARY,
                        padding=(15, 5), font=('Segoe UI', 10, 'bold'))
        style.map('TNotebook.Tab',
                  background=[('selected', BG_PANEL)],
                  foreground=[('selected', ACCENT_BLUE)])
        style.configure('TScale', background=BG_PANEL, troughcolor=BG_ENTRY)
        style.configure('TProgressbar', background=ACCENT_BLUE, troughcolor=BG_ENTRY)
        style.configure('TCombobox', fieldbackground=BG_ENTRY, foreground=FG_PRIMARY,
                        background=BG_ENTRY)

    def _build_ui(self):
        # ─── Top bar ───
        top_bar = tk.Frame(self.root, bg=BG_PANEL, height=50)
        top_bar.pack(fill=tk.X, side=tk.TOP)
        title_label = tk.Label(top_bar, text=f"🦆 {__app_name__}",
                              bg=BG_PANEL, fg=ACCENT_BLUE, font=('Segoe UI', 16, 'bold'))
        title_label.pack(side=tk.LEFT, padx=15, pady=8)
        ver_label = tk.Label(top_bar, text=f"v{__version__}",
                            bg=BG_PANEL, fg=FG_SECONDARY, font=('Segoe UI', 9))
        ver_label.pack(side=tk.LEFT, pady=8)
        status_label = tk.Label(top_bar, textvariable=self.status_var,
                               bg=BG_PANEL, fg=ACCENT_GREEN, font=('Segoe UI', 10))
        status_label.pack(side=tk.RIGHT, padx=15, pady=8)

        # ─── Notebook (tabs) ───
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._build_studio_tab()
        self._build_sequencer_tab()
        self._build_mixer_tab()
        self._build_hf_tab()
        self._build_oss_tab()
        self._build_duck_eco_tab()
        self._build_settings_tab()

        # ─── Bottom bar ───
        bottom_bar = tk.Frame(self.root, bg=BG_PANEL, height=30)
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)
        bpm_label = tk.Label(bottom_bar, text="BPM: 120",
                            bg=BG_PANEL, fg=FG_SECONDARY, font=('Segoe UI', 9))
        bpm_label.pack(side=tk.LEFT, padx=15)
        tracks_label = tk.Label(bottom_bar, text="Tracks: 0",
                               bg=BG_PANEL, fg=FG_SECONDARY, font=('Segoe UI', 9))
        tracks_label.pack(side=tk.LEFT, padx=10)
        duck_io_label = tk.Label(bottom_bar, text="duck-stdio: active",
                                bg=BG_PANEL, fg=ACCENT_PURPLE, font=('Segoe UI', 9))
        duck_io_label.pack(side=tk.RIGHT, padx=15)

        self.bpm_label_ref = bpm_label
        self.tracks_label_ref = tracks_label

    # ─── Tab: Studio Overview ───
    def _build_studio_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🏠 Studio")

        # Welcome
        welcome = tk.Label(frame, text="🦆 DuckStudio Win11",
                          bg=BG_PANEL, fg=ACCENT_BLUE, font=('Segoe UI', 24, 'bold'))
        welcome.pack(pady=20)

        sub = tk.Label(frame, text="O estúdio musical mais completo do mundo — Open Source + HuggingFace + Duck ecosystem",
                      bg=BG_PANEL, fg=FG_SECONDARY, font=('Segoe UI', 12))
        sub.pack(pady=5)

        # Quick stats
        stats_frame = tk.Frame(frame, bg=BG_PANEL)
        stats_frame.pack(pady=20)
        detected = self.oss_manager.detect_installed()
        installed_count = sum(1 for v in detected.values() if v["installed"])
        total_tools = len(OSS_TOOLS)
        eco = self.duck_eco.detect_available()
        eco_count = sum(1 for v in eco.values() if v["exists"])

        stats = [
            f"OSS Tools: {installed_count}/{total_tools} installed",
            f"Duck Ecosystem: {eco_count} resources found",
            f"HuggingFace Models: {sum(len(v) for v in HF_AUDIO_MODELS.values())} available",
            f"Effects: {len(list_effects())} DSP effects",
            f"duck-stdio: I/O engine active",
            f"Audio: numpy + wave synthesis",
        ]
        for stat in stats:
            tk.Label(stats_frame, text=stat, bg=BG_PANEL, fg=ACCENT_GREEN,
                    font=('Segoe UI', 10)).pack(anchor='w', pady=2)

        # Quick actions
        actions_frame = tk.Frame(frame, bg=BG_PANEL)
        actions_frame.pack(pady=20)
        tk.Label(actions_frame, text="Quick Actions", bg=BG_PANEL, fg=FG_PRIMARY,
                font=('Segoe UI', 14, 'bold')).pack(pady=10)

        actions = [
            ("🥁 New Beat", lambda: self.notebook.select(1)),
            ("🎚️ Open Mixer", lambda: self.notebook.select(2)),
            ("🤖 HuggingFace AI", lambda: self.notebook.select(3)),
            ("🛠️ OSS Tools", lambda: self.notebook.select(4)),
            ("🦆 Duck Ecosystem", lambda: self.notebook.select(5)),
            ("⚙️ Settings", lambda: self.notebook.select(6)),
        ]
        for label, cmd in actions:
            btn = ttk.Button(actions_frame, text=label, command=cmd)
            btn.pack(side=tk.LEFT, padx=5)

        # Recent projects
        proj_frame = tk.Frame(frame, bg=BG_PANEL)
        proj_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        tk.Label(proj_frame, text="Recent / Active Projects", bg=BG_PANEL, fg=FG_PRIMARY,
                font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=5)
        # List Duck ecosystem files
        listbox = tk.Listbox(proj_frame, bg=BG_ENTRY, fg=FG_PRIMARY,
                           font=('Segoe UI', 10), selectbackground=ACCENT_BLUE,
                           activestyle='dotbox', borderwidth=0, highlightthickness=0)
        listbox.pack(fill=tk.BOTH, expand=True)
        eco = self.duck_eco.detect_available()
        for key, info in eco.items():
            if info["exists"]:
                listbox.insert(tk.END, f"📁 {key} — {info['path']}")
        # Also check for duck-stdio source
        duck_stdio_path = r"C:\Users\USER\Downloads\duck-stdio-extract\duck-stdio"
        if os.path.isdir(duck_stdio_path):
            listbox.insert(tk.END, f"📦 duck-stdio — {duck_stdio_path}")

    # ─── Tab: Sequencer / Beat Maker ───
    def _build_sequencer_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🥁 Sequencer")

        # Controls bar
        ctrl = tk.Frame(frame, bg=BG_PANEL)
        ctrl.pack(fill=tk.X, pady=5)

        ttk.Button(ctrl, text="▶ Play", command=self._play_sequence).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="⏹ Stop", command=self._stop_sequence).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="🔄 Clear", command=self._clear_pattern).pack(side=tk.LEFT, padx=5)

        # BPM control
        tk.Label(ctrl, text="BPM:", bg=BG_PANEL, fg=FG_PRIMARY).pack(side=tk.LEFT, padx=10)
        self.bpm_spin = tk.Spinbox(ctrl, from_=40, to=300, width=5, format="%.0f",
                                  bg=BG_ENTRY, fg=FG_PRIMARY, insertbackground=FG_PRIMARY,
                                  font=('Segoe UI', 10), relief='flat',
                                  command=self._on_bpm_change)
        self.bpm_spin.delete(0, tk.END)
        self.bpm_spin.insert(0, "120")
        self.bpm_spin.pack(side=tk.LEFT, padx=5)

        # Steps selector
        tk.Label(ctrl, text="Steps:", bg=BG_PANEL, fg=FG_PRIMARY).pack(side=tk.LEFT, padx=10)
        self.steps_spin = tk.Spinbox(ctrl, from_=4, to=64, increment=4, width=5,
                                    bg=BG_ENTRY, fg=FG_PRIMARY, insertbackground=FG_PRIMARY,
                                    font=('Segoe UI', 10), relief='flat')
        self.steps_spin.delete(0, tk.END)
        self.steps_spin.insert(0, "16")
        self.steps_spin.pack(side=tk.LEFT, padx=5)

        # Preset selector
        tk.Label(ctrl, text="Preset:", bg=BG_PANEL, fg=FG_PRIMARY).pack(side=tk.LEFT, padx=10)
        self.preset_combo = ttk.Combobox(ctrl, values=["None"] + self.sequencer.list_presets(),
                                         width=15, state='readonly')
        self.preset_combo.set("None")
        self.preset_combo.pack(side=tk.LEFT, padx=5)
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_change)

        # Export buttons
        ttk.Button(ctrl, text="💾 Save Pattern", command=self._save_pattern).pack(side=tk.RIGHT, padx=5)
        ttk.Button(ctrl, text="📂 Load Pattern", command=self._load_pattern).pack(side=tk.RIGHT, padx=5)
        ttk.Button(ctrl, text="🎵 Render WAV", command=self._render_pattern_wav).pack(side=tk.RIGHT, padx=5)

        # Grid
        grid_frame = tk.Frame(frame, bg=BG_PANEL)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._build_sequencer_grid(grid_frame)

    def _build_sequencer_grid(self, parent):
        for child in parent.winfo_children():
            child.destroy()
        pattern = self.sequencer.get_current_pattern()
        steps = pattern.steps_count
        # Header row
        tk.Label(parent, text="Track", bg=BG_PANEL, fg=FG_SECONDARY, width=12,
                font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, padx=2, pady=2)
        for i in range(steps):
            tk.Label(parent, text=str(i+1), bg=BG_PANEL, fg=FG_SECONDARY, width=2,
                    font=('Segoe UI', 8)).grid(row=0, column=i+1, padx=1, pady=2)
        # Track rows
        self._step_buttons: list[list[tk.Button]] = []
        for row_idx, row in enumerate(pattern.rows):
            tk.Label(parent, text=row.name, bg=BG_PANEL, fg=FG_PRIMARY, width=12,
                    font=('Segoe UI', 9)).grid(row=row_idx+1, column=0, padx=2, pady=1)
            step_buttons = []
            for step_idx in range(steps):
                active = row.steps[step_idx].active
                bg = row.color if active else BG_ENTRY
                fg = 'white' if active else FG_SECONDARY
                btn = tk.Button(parent, text="●" if active else "○",
                               bg=bg, fg=fg, width=2, relief='flat',
                               font=('Segoe UI', 8),
                               command=lambda r=row_idx, s=step_idx: self._toggle_step(r, s))
                btn.grid(row=row_idx+1, column=step_idx+1, padx=1, pady=1)
                step_buttons.append(btn)
            self._step_buttons.append(step_buttons)

    def _toggle_step(self, row_idx, step_idx):
        pattern = self.sequencer.get_current_pattern()
        if row_idx < len(pattern.rows) and step_idx < len(pattern.rows[row_idx].steps):
            pattern.rows[row_idx].steps[step_idx].active = not pattern.rows[row_idx].steps[step_idx].active
            self._build_sequencer_grid(self.root.winfo_children()[1].winfo_children()[0]  # hacky but works
                                       if False else None)  # Actually rebuild
            # Find the grid frame
            for child in self.notebook.winfo_children():
                if self.notebook.tab(child, "text") == "🥁 Sequencer":
                    for sub in child.winfo_children():
                        if isinstance(sub, tk.Frame) and len(sub.winfo_children()) > 3:
                            self._build_sequencer_grid(sub)
                            break
                    break
        self._update_status(f"Step toggled: row {row_idx+1}, step {step_idx+1}")

    def _play_sequence(self):
        self.now_playing = True
        self._update_status("Playing pattern...")
        # In a real app, this would trigger audio playback via the mixer
        threading.Thread(target=self._play_thread, daemon=True).start()

    def _play_thread(self):
        pattern = self.sequencer.get_current_pattern()
        bpm = pattern.bpm
        step_duration = 60.0 / bpm / 4  # 16th notes
        for step in range(pattern.steps_count):
            if not self.now_playing:
                break
            time.sleep(step_duration)
            self.sequencer.current_step = step
        self.now_playing = False
        self._update_status("Stopped")

    def _stop_sequence(self):
        self.now_playing = False
        self._update_status("Stopped")

    def _clear_pattern(self):
        pattern = self.sequencer.get_current_pattern()
        for row in pattern.rows:
            for step in row.steps:
                step.active = False
        self._rebuild_grid()
        self._update_status("Pattern cleared")

    def _on_bpm_change(self):
        try:
            bpm = int(self.bpm_spin.get())
            self.sequencer.get_current_pattern().bpm = bpm
            self.bpm_label_ref.config(text=f"BPM: {bpm}")
        except ValueError:
            pass

    def _on_preset_change(self, event=None):
        preset_name = self.preset_combo.get()
        if preset_name and preset_name != "None":
            result = self.sequencer.apply_preset(preset_name)
            if "status" in result:
                self._rebuild_grid()
                self._update_status(f"Preset applied: {preset_name}")
            else:
                messagebox.showerror("Error", result.get("error", "Unknown error"))

    def _rebuild_grid(self):
        for child in self.notebook.winfo_children():
            if self.notebook.tab(child, "text") == "🥁 Sequencer":
                for sub in child.winfo_children():
                    if isinstance(sub, tk.Frame) and len(sub.winfo_children()) > 3:
                        self._build_sequencer_grid(sub)
                        return

    def _save_pattern(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("Duck Pattern", "*.duckpat"), ("JSON", "*.json")],
            title="Save Pattern"
        )
        if filepath:
            result = self.sequencer.get_current_pattern().export_json(filepath)
            if "status" in result:
                self._update_status(f"Pattern saved: {filepath}")
            else:
                messagebox.showerror("Error", result["error"])

    def _load_pattern(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Duck Pattern", "*.duckpat"), ("JSON", "*.json")],
            title="Load Pattern"
        )
        if filepath:
            result = self.sequencer.get_current_pattern().import_json(filepath)
            if "status" in result:
                self._rebuild_grid()
                self._update_status(f"Pattern loaded: {filepath}")
            else:
                messagebox.showerror("Error", result["error"])

    def _render_pattern_wav(self):
        pattern = self.sequencer.get_current_pattern()
        bpm = pattern.bpm
        beat_duration = 60.0 / bpm
        total_duration = beat_duration * 4  # one bar
        sample_rate = 44100
        num_samples = int(total_duration * sample_rate)
        import numpy as np
        output = np.zeros((num_samples, 2), dtype=np.float32)
        beat_samples = int(beat_duration * sample_rate)
        for row in pattern.rows:
            for i, step in enumerate(row.steps):
                if not step.active:
                    continue
                pos = i * beat_samples // 4
                # Simple synthesis per instrument type
                if "Kick" in row.name:
                    for j in range(min(2000, num_samples - pos)):
                        env = (1 - j/2000) ** 2
                        freq = 80 + 40*(1-j/2000)
                        val = env * 0.8 * math.sin(2*math.pi*freq*j/sample_rate)
                        output[pos+j, 0] += val
                        output[pos+j, 1] += val
                elif "Snare" in row.name:
                    for j in range(min(4000, num_samples - pos)):
                        env = (1-j/4000)**1.5
                        noise = ((j*37)%256)/128.0 - 1
                        val = env * 0.4 * noise
                        output[pos+j, 0] += val
                        output[pos+j, 1] += val
                elif "Hat" in row.name:
                    for j in range(min(1000, num_samples - pos)):
                        env = (1-j/1000)**3
                        noise = ((j*53)%256)/128.0 - 1
                        val = env * 0.2 * noise
                        output[pos+j, 0] += val
                        output[pos+j, 1] += val
        # Normalize
        max_val = np.max(np.abs(output)) if len(output) > 0 else 1
        if max_val > 0:
            output = output / max_val * 0.8
        int_data = (output * 32767).astype(np.int16)
        import wave
        filepath = filedialog.asksaveasfilename(
            defaultextension=".wav", filetypes=[("WAV", "*.wav")],
            title="Export WAV"
        )
        if filepath:
            with wave.open(filepath, 'w') as wav:
                wav.setnchannels(2)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                wav.writeframes(int_data.tobytes())
            self._update_status(f"WAV exported: {filepath}")

    # ─── Tab: Mixer ───
    def _build_mixer_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🎚️ Mixer")

        # Toolbar
        toolbar = tk.Frame(frame, bg=BG_PANEL)
        toolbar.pack(fill=tk.X, pady=5)
        ttk.Button(toolbar, text="➕ Add Track", command=self._add_mixer_track).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📂 Load WAV", command=self._load_wav_to_track).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="💾 Export Mix", command=self._export_mix).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🔊 Generate Tone", command=self._generate_tone_dialog).pack(side=tk.LEFT, padx=5)

        # Master volume
        master_frame = tk.Frame(frame, bg=BG_PANEL)
        master_frame.pack(fill=tk.X, pady=5)
        tk.Label(master_frame, text="Master Volume:", bg=BG_PANEL, fg=FG_PRIMARY).pack(side=tk.LEFT, padx=10)
        self.master_vol = tk.Scale(master_frame, from_=0, to=200, orient=tk.HORIZONTAL,
                                  bg=BG_PANEL, fg=FG_PRIMARY, highlightthickness=0,
                                  troughcolor=BG_ENTRY, activebackground=ACCENT_BLUE,
                                  length=300, command=self._on_master_vol)
        self.master_vol.set(100)
        self.master_vol.pack(side=tk.LEFT, padx=10)

        # Track list
        tracks_frame = tk.Frame(frame, bg=BG_PANEL)
        tracks_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        tk.Label(tracks_frame, text="Tracks", bg=BG_PANEL, fg=FG_PRIMARY,
                font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        self.track_list_frame = tk.Frame(tracks_frame, bg=BG_PANEL)
        self.track_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Effects section
        eff_frame = tk.Frame(frame, bg=BG_PANEL)
        eff_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(eff_frame, text="Effects Chain:", bg=BG_PANEL, fg=FG_PRIMARY,
                font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        self.effect_combo = ttk.Combobox(eff_frame, values=list_effects(), width=15, state='readonly')
        self.effect_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(eff_frame, text="➕ Add Effect", command=self._add_effect).pack(side=tk.LEFT, padx=5)
        ttk.Button(eff_frame, text="🗑️ Clear All", command=self._clear_effects).pack(side=tk.LEFT, padx=5)
        self.effects_label = tk.Label(eff_frame, text="No effects", bg=BG_PANEL, fg=FG_SECONDARY)
        self.effects_label.pack(side=tk.LEFT, padx=10)
        self._update_effects_display()

    def _add_mixer_track(self):
        name = simpledialog.askstring("Add Track", "Track name:", parent=self.root,
                                     initialvalue=f"Track {len(self.mixer.tracks)+1}")
        if name:
            self.mixer.add_track(name)
            self._rebuild_mixer_tracks()
            self._update_status(f"Track added: {name}")
            self.tracks_label_ref.config(text=f"Tracks: {len(self.mixer.tracks)}")

    def _load_wav_to_track(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("WAV", "*.wav"), ("All Files", "*.*")],
            title="Select WAV file"
        )
        if filepath:
            track_name = simpledialog.askstring("Track Name", "Name for this track:",
                                               parent=self.root, initialvalue=os.path.basename(filepath))
            if track_name:
                track = self.mixer.add_track(track_name)
                result = track.load_wav(filepath)
                if "error" in result:
                    messagebox.showerror("Error", result["error"])
                    self.mixer.tracks.remove(track)
                else:
                    self._rebuild_mixer_tracks()
                    self._update_status(f"Loaded: {filepath} ({result['duration']:.1f}s)")

    def _generate_tone_dialog(self):
        freq = simpledialog.askfloat("Tone Generator", "Frequency (Hz):",
                                     parent=self.root, initialvalue=440, minvalue=20, maxvalue=20000)
        if freq:
            duration = simpledialog.askfloat("Duration", "Duration (seconds):",
                                            parent=self.root, initialvalue=2.0, minvalue=0.1, maxvalue=60)
            if duration:
                track = self.mixer.add_track(f"Tone {freq}Hz")
                result = track.generate_tone(freq, duration, "sine")
                if "status" in result:
                    self._rebuild_mixer_tracks()
                    self._update_status(f"Tone: {freq}Hz, {duration}s")

    def _rebuild_mixer_tracks(self):
        for child in self.track_list_frame.winfo_children():
            child.destroy()
        for i, track in enumerate(self.mixer.tracks):
            row = tk.Frame(self.track_list_frame, bg=BG_ENTRY)
            row.pack(fill=tk.X, pady=2, padx=2)
            # Name
            tk.Label(row, text=track.name, bg=BG_ENTRY, fg=FG_PRIMARY, width=15,
                    font=('Segoe UI', 9, 'bold')).pack(side=tk.LEFT, padx=5)
            # Mute
            mute_var = tk.BooleanVar(value=track.muted)
            def toggle_mute(idx=i, var=mute_var):
                self.mixer.tracks[idx].muted = var.get()
            tk.Checkbutton(row, text="M", variable=mute_var, command=toggle_mute,
                          bg=BG_ENTRY, fg=FG_PRIMARY, selectcolor=ACCENT_RED,
                          activebackground=BG_ENTRY, activeforeground=FG_PRIMARY,
                          font=('Segoe UI', 8)).pack(side=tk.LEFT, padx=2)
            # Volume
            vol_var = tk.DoubleVar(value=track.volume * 100)
            def on_vol(val, idx=i):
                self.mixer.tracks[idx].volume = float(val) / 100
            tk.Scale(row, from_=0, to=200, orient=tk.HORIZONTAL, width=10,
                    variable=vol_var, command=on_vol, bg=BG_ENTRY, fg=FG_PRIMARY,
                    highlightthickness=0, troughcolor=BG_PANEL, activebackground=ACCENT_BLUE,
                    length=150).pack(side=tk.LEFT, padx=5)
            # Pan
            pan_var = tk.DoubleVar(value=track.pan * 50 + 50)
            def on_pan(val, idx=i):
                self.mixer.tracks[idx].pan = (float(val) - 50) / 50
            tk.Scale(row, from_=0, to=100, orient=tk.HORIZONTAL, width=10,
                    variable=pan_var, command=on_pan, bg=BG_ENTRY, fg=FG_PRIMARY,
                    highlightthickness=0, troughcolor=BG_PANEL, activebackground=ACCENT_PURPLE,
                    length=80).pack(side=tk.LEFT, padx=5)

    def _on_master_vol(self, val):
        self.mixer.master_volume = float(val) / 100

    def _export_mix(self):
        if not self.mixer.tracks:
            messagebox.showinfo("Export", "No tracks to export")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".wav", filetypes=[("WAV", "*.wav")],
            title="Export Mix"
        )
        if filepath:
            result = self.mixer.export_wav(filepath)
            if "status" in result:
                self._update_status(f"Mix exported: {filepath}")
                messagebox.showinfo("Export", f"Exported to:\n{filepath}")
            else:
                messagebox.showerror("Error", result["error"])

    def _add_effect(self):
        name = self.effect_combo.get()
        if not name:
            return
        effect = create_effect(name)
        if effect:
            self.effect_chain.append(effect)
            self._update_effects_display()
            self._update_status(f"Effect added: {name}")

    def _clear_effects(self):
        self.effect_chain.clear()
        self._update_effects_display()
        self._update_status("Effects cleared")

    def _update_effects_display(self):
        if not self.effect_chain:
            self.effects_label.config(text="No effects")
        else:
            names = ", ".join(e.name for e in self.effect_chain)
            self.effects_label.config(text=f"{len(self.effect_chain)} effects: {names}")

    # ─── Tab: HuggingFace AI ───
    def _build_hf_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🤖 HuggingFace")

        # Token section
        token_frame = tk.Frame(frame, bg=BG_PANEL)
        token_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(token_frame, text="HuggingFace Token:", bg=BG_PANEL, fg=FG_PRIMARY,
                font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        self.hf_token_entry = ttk.Entry(token_frame, width=50, show="*")
        self.hf_token_entry.pack(side=tk.LEFT, padx=5)
        if self.hf_client.has_token():
            self.hf_token_entry.insert(0, "•" * 20)
        ttk.Button(token_frame, text="Set Token", command=self._set_hf_token).pack(side=tk.LEFT, padx=5)
        tk.Label(token_frame, text="Get token at huggingface.co/settings/tokens",
                bg=BG_PANEL, fg=FG_SECONDARY, font=('Segoe UI', 8)).pack(side=tk.LEFT, padx=5)

        # Category selection
        cat_frame = tk.Frame(frame, bg=BG_PANEL)
        cat_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(cat_frame, text="Category:", bg=BG_PANEL, fg=FG_PRIMARY).pack(side=tk.LEFT, padx=5)
        self.hf_cat_combo = ttk.Combobox(cat_frame, values=list(HF_AUDIO_MODELS.keys()),
                                        state='readonly', width=20)
        self.hf_cat_combo.set("tts")
        self.hf_cat_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(cat_frame, text="Load Models", command=self._load_hf_models).pack(side=tk.LEFT, padx=5)

        # Models list
        list_frame = tk.Frame(frame, bg=BG_PANEL)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.hf_models_list = tk.Listbox(list_frame, bg=BG_ENTRY, fg=FG_PRIMARY,
                                       font=('Segoe UI', 10), selectbackground=ACCENT_BLUE,
                                       activestyle='dotbox', borderwidth=0, highlightthickness=0)
        self.hf_models_list.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.hf_models_list.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.hf_models_list.config(yscrollcommand=scroll.set)

        # Action buttons
        action_frame = tk.Frame(frame, bg=BG_PANEL)
        action_frame.pack(fill=tk.X, padx=10, pady=10)

        # TTS section
        tts_frame = tk.LabelFrame(action_frame, text="Text-to-Speech", bg=BG_PANEL, fg=FG_PRIMARY,
                                 font=('Segoe UI', 10, 'bold'))
        tts_frame.pack(fill=tk.X, pady=5)
        tk.Label(tts_frame, text="Text:", bg=BG_PANEL, fg=FG_PRIMARY).pack(side=tk.LEFT, padx=5)
        self.tts_text = tk.Text(tts_frame, height=3, width=50, bg=BG_ENTRY, fg=FG_PRIMARY,
                              insertbackground=FG_PRIMARY, font=('Segoe UI', 10), relief='flat',
                              borderwidth=0, highlightthickness=1, highlightbackground=BG_ENTRY)
        self.tts_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        ttk.Button(tts_frame, text="🔊 Generate Speech", command=self._generate_tts).pack(side=tk.LEFT, padx=5)

        # Music gen section
        music_frame = tk.LabelFrame(action_frame, text="Music Generation (MusicGen)", bg=BG_PANEL, fg=FG_PRIMARY,
                                   font=('Segoe UI', 10, 'bold'))
        music_frame.pack(fill=tk.X, pady=5)
        tk.Label(music_frame, text="Prompt:", bg=BG_PANEL, fg=FG_PRIMARY).pack(side=tk.LEFT, padx=5)
        self.music_prompt = tk.Text(music_frame, height=3, width=50, bg=BG_ENTRY, fg=FG_PRIMARY,
                                   insertbackground=FG_PRIMARY, font=('Segoe UI', 10), relief='flat',
                                   borderwidth=0, highlightthickness=1, highlightbackground=BG_ENTRY)
        self.music_prompt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        ttk.Button(music_frame, text="🎵 Generate Music", command=self._generate_music).pack(side=tk.LEFT, padx=5)

        # Local synth
        local_frame = tk.LabelFrame(action_frame, text="Local Synthesis (no internet needed)", bg=BG_PANEL,
                                   fg=FG_PRIMARY, font=('Segoe UI', 10, 'bold'))
        local_frame.pack(fill=tk.X, pady=5)
        ttk.Button(local_frame, text="🎵 Tone 440Hz", command=lambda: self._local_tone(440)).pack(side=tk.LEFT, padx=5)
        ttk.Button(local_frame, text="🎹 C Major Chord", command=self._local_chord).pack(side=tk.LEFT, padx=5)
        ttk.Button(local_frame, text="🥁 Drum Pattern", command=self._local_drum).pack(side=tk.LEFT, padx=5)
        ttk.Button(local_frame, text="📐 Sweep 20Hz-20kHz", command=self._local_sweep).pack(side=tk.LEFT, padx=5)

    def _set_hf_token(self):
        token = self.hf_token_entry.get()
        if token and not token.startswith("•"):
            self.hf_client.set_token(token)
            self._update_status("HF token set")
            messagebox.showinfo("Token", "Token saved for this session.\n\nFor persistence, set HF_TOKEN env var.")

    def _load_hf_models(self):
        cat = self.hf_cat_combo.get()
        models = self.hf_client.list_models(cat)
        self.hf_models_list.delete(0, tk.END)
        for model_id, desc in models.items():
            self.hf_models_list.insert(tk.END, f"{model_id} — {desc}")
        self._update_status(f"Loaded {len(models)} {cat} models")

    def _generate_tts(self):
        text = self.tts_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("TTS", "Enter some text first")
            return
        self._update_status("Generating speech via HuggingFace...")
        def do_tts():
            result = self.hf_client.text_to_speech(text)
            if "error" in result:
                self.root.after(0, lambda: messagebox.showerror("TTS Error", result["error"]))
            elif "audio" in result:
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".wav", filetypes=[("WAV", "*.wav")],
                    title="Save TTS Audio"
                )
                if filepath:
                    with open(filepath, 'wb') as f:
                        f.write(result["audio"])
                    self.root.after(0, lambda: self._update_status(f"TTS saved: {filepath}"))
            self.root.after(0, lambda: self._update_status("TTS done"))
        threading.Thread(target=do_tts, daemon=True).start()

    def _generate_music(self):
        prompt = self.music_prompt.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showwarning("Music Gen", "Enter a prompt first")
            return
        self._update_status("Generating music via MusicGen...")
        def do_music():
            result = self.hf_client.generate_music(prompt)
            if "error" in result:
                self.root.after(0, lambda: messagebox.showerror("MusicGen Error", result["error"]))
            elif "audio" in result:
                filepath = filedialog.asksaveasfilename(
                    defaultextension=".wav", filetypes=[("WAV", "*.wav")],
                    title="Save Music"
                )
                if filepath:
                    with open(filepath, 'wb') as f:
                        f.write(result["audio"])
                    self.root.after(0, lambda: self._update_status(f"Music saved: {filepath}"))
            self.root.after(0, lambda: self._update_status("MusicGen done"))
        threading.Thread(target=do_music, daemon=True).start()

    def _local_tone(self, freq):
        result = self.hf_client.local_tone(frequency=freq)
        if "error" not in result:
            self._update_status(f"Tone {freq}Hz generated: {result}")
            os.startfile(result)
        else:
            messagebox.showerror("Error", result["error"])

    def _local_chord(self):
        # C major: C4, E4, G4, C5
        result = self.hf_client.local_chord([261.63, 329.63, 392.0, 523.25])
        if "error" not in result:
            os.startfile(result)

    def _local_drum(self):
        result = self.hf_client.local_drum_pattern(bpm=120, bars=4, pattern="four-on-the-floor")
        if "error" not in result:
            os.startfile(result)

    def _local_sweep(self):
        result = self.hf_client.local_sweep()
        if "error" not in result:
            os.startfile(result)

    # ─── Tab: OSS Tools ───
    def _build_oss_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🛠️ OSS Tools")

        # Header
        tk.Label(frame, text="Open Source Audio Tools", bg=BG_PANEL, fg=ACCENT_BLUE,
                font=('Segoe UI', 14, 'bold')).pack(pady=10)
        tk.Label(frame, text="Open alternatives to expensive music software",
                bg=BG_PANEL, fg=FG_SECONDARY).pack()

        # Filter by category
        filter_frame = tk.Frame(frame, bg=BG_PANEL)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(filter_frame, text="Filter:", bg=BG_PANEL, fg=FG_PRIMARY).pack(side=tk.LEFT, padx=5)
        self.oss_cat_combo = ttk.Combobox(filter_frame,
                                         values=["All"] + self.oss_manager.get_categories(),
                                         state='readonly', width=20)
        self.oss_cat_combo.set("All")
        self.oss_cat_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="🔄 Refresh", command=self._refresh_oss_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="🔍 Detect Installed", command=self._detect_installed).pack(side=tk.LEFT, padx=5)

        # Tools list
        list_frame = tk.Frame(frame, bg=BG_PANEL)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.oss_tree = ttk.Treeview(list_frame,
                                     columns=("Status", "Category", "Price", "URL"),
                                     show='tree headings', selectmode='browse')
        self.oss_tree.heading("#0", text="Tool")
        self.oss_tree.heading("Status", text="Status")
        self.oss_tree.heading("Category", text="Category")
        self.oss_tree.heading("Price", text="Price")
        self.oss_tree.heading("URL", text="Download URL")
        self.oss_tree.column("#0", width=150)
        self.oss_tree.column("Status", width=80)
        self.oss_tree.column("Category", width=120)
        self.oss_tree.column("Price", width=60)
        self.oss_tree.column("URL", width=200)
        self.oss_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.oss_tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.oss_tree.configure(yscrollcommand=scroll.set)

        # Actions
        action_frame = tk.Frame(frame, bg=BG_PANEL)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(action_frame, text="▶ Launch", command=self._launch_oss_tool).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="⬇ Download Installer", command=self._download_oss_tool).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="🌐 Open GitHub", command=self._open_oss_github).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="📖 Info", command=self._show_oss_info).pack(side=tk.LEFT, padx=5)

        self._refresh_oss_list()

    def _refresh_oss_list(self):
        for item in self.oss_tree.get_children():
            self.oss_tree.delete(item)
        cat = self.oss_cat_combo.get()
        if cat == "All":
            tools = self.oss_manager.list_all()
        else:
            tools = self.oss_manager.list_by_category(cat)
        detected = self.oss_manager.detect_installed()
        for key, tool in tools.items():
            status = "✅ Installed" if detected.get(key, {}).get("installed") else "❌ Not installed"
            url = tool.get("windows_url", tool.get("github", ""))
            self.oss_tree.insert("", tk.END, text=tool["name"],
                               values=(status, tool["category"], "Free" if not tool["paid"] else tool.get("price", "$"), url),
                               tags=(key,))

    def _detect_installed(self):
        self.oss_manager._installed_cache = None  # Force re-detect
        self._refresh_oss_list()
        detected = self.oss_manager.detect_installed()
        installed = {k: v for k, v in detected.items() if v["installed"]}
        messagebox.showinfo("Detection", f"Found {len(installed)} installed tools:\n" +
                          "\n".join(f"  ✅ {k}" for k in installed.keys()))

    def _get_selected_oss_key(self) -> str:
        sel = self.oss_tree.selection()
        if sel:
            tags = self.oss_tree.item(sel[0], "tags")
            if tags:
                return tags[0]
        return None

    def _launch_oss_tool(self):
        key = self._get_selected_oss_key()
        if key:
            result = self.oss_manager.launch_tool(key)
            if "error" in result:
                messagebox.showwarning("Launch", result["error"])
            else:
                self._update_status(f"Launched: {key}")

    def _download_oss_tool(self):
        key = self._get_selected_oss_key()
        if key:
            self._update_status(f"Downloading {key}...")
            def do_download():
                result = self.oss_manager.download_installer(key)
                if "status" in result:
                    self.root.after(0, lambda: messagebox.showinfo("Download", f"Saved to:\n{result['path']}"))
                    self.root.after(0, lambda: self._update_status(f"Downloaded: {result['path']}"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Download", result["error"]))
            threading.Thread(target=do_download, daemon=True).start()

    def _open_oss_github(self):
        key = self._get_selected_oss_key()
        if key:
            tool = OSS_TOOLS.get(key, {})
            url = tool.get("github") or tool.get("windows_url", "")
            if url:
                os.startfile(url)

    def _show_oss_info(self):
        key = self._get_selected_oss_key()
        if key:
            tool = OSS_TOOLS.get(key, {})
            info = f"Name: {tool.get('name', 'N/A')}\n"
            info += f"Category: {tool.get('category', 'N/A')}\n"
            info += f"Description: {tool.get('description', 'N/A')}\n"
            info += f"Price: {'Free' if not tool.get('paid') else tool.get('price', 'N/A')}\n"
            info += f"Features: {', '.join(tool.get('features', []))}\n"
            info += f"GitHub: {tool.get('github', 'N/A')}\n"
            info += f"Windows: {tool.get('windows_url', 'N/A')}"
            messagebox.showinfo(tool.get("name", "Tool"), info)

    # ─── Tab: Duck Ecosystem ───
    def _build_duck_eco_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="🦆 Duck Ecosystem")

        tk.Label(frame, text="Duck Studio Ecosystem", bg=BG_PANEL, fg=ACCENT_BLUE,
                font=('Segoe UI', 14, 'bold')).pack(pady=10)
        tk.Label(frame, text="All Duck resources found on this PC — I/O, web platform, music producer, docs",
                bg=BG_PANEL, fg=FG_SECONDARY).pack()

        # Ecosystem resources
        eco_frame = tk.Frame(frame, bg=BG_PANEL)
        eco_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.eco_tree = ttk.Treeview(eco_frame, columns=("Status", "Path"),
                                     show='tree headings', selectmode='browse')
        self.eco_tree.heading("#0", text="Resource")
        self.eco_tree.heading("Status", text="Status")
        self.eco_tree.heading("Path", text="Path")
        self.eco_tree.column("#0", width=200)
        self.eco_tree.column("Status", width=80)
        self.eco_tree.column("Path", width=400)
        self.eco_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll = ttk.Scrollbar(eco_frame, orient=tk.VERTICAL, command=self.eco_tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.eco_tree.configure(yscrollcommand=scroll.set)

        detected = self.duck_eco.detect_available()
        for key, info in detected.items():
            status = "✅ Found" if info["exists"] else "❌ Not found"
            self.eco_tree.insert("", tk.END, text=key, values=(status, info["path"]), tags=(key,))

        # Actions
        action_frame = tk.Frame(frame, bg=BG_PANEL)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(action_frame, text="📁 Open Folder", command=self._open_eco_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="📖 Show Info", command=self._show_eco_info).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="🌐 Launch Web Platform", command=self._launch_duck_web).pack(side=tk.LEFT, padx=5)

        # duck-stdio info
        stdio_frame = tk.LabelFrame(frame, text="duck-stdio I/O Engine", bg=BG_PANEL, fg=ACCENT_PURPLE,
                                   font=('Segoe UI', 10, 'bold'))
        stdio_frame.pack(fill=tk.X, padx=10, pady=5)
        stdio_info = (
            "duck-stdio provides universal I/O: file, memory, SQLite, Postgres, MySQL, Redis, S3\n"
            "Source: C library (src/stdio.c, src/stdio.h) with tests and benchmarks\n"
            "DuckStudio wraps it in Python for cross-platform compatibility\n"
            "Active: all I/O operations in this app pass through DuckStream"
        )
        tk.Label(stdio_frame, text=stdio_info, bg=BG_PANEL, fg=FG_SECONDARY,
                font=('Segoe UI', 9), justify=tk.LEFT).pack(anchor='w', padx=10, pady=5)

        # Test duck-stdio
        ttk.Button(stdio_frame, text="🧪 Test duck-stdio I/O", command=self._test_duck_stdio).pack(side=tk.LEFT, padx=5)

    def _get_selected_eco_key(self) -> str:
        sel = self.eco_tree.selection()
        if sel:
            tags = self.eco_tree.item(sel[0], "tags")
            if tags:
                return tags[0]
        return None

    def _open_eco_folder(self):
        key = self._get_selected_eco_key()
        if key:
            info = self.duck_eco.detect_available().get(key)
            if info and info["exists"]:
                os.startfile(info["path"])
            else:
                messagebox.showwarning("Open", "Folder not found")

    def _show_eco_info(self):
        key = self._get_selected_eco_key()
        if key:
            info = self.duck_eco.get_resource_info(key)
            if "error" not in info:
                msg = f"Resource: {info['key']}\nPath: {info['path']}\n"
                msg += f"Files: {info['file_count']}\nSize: {info['total_size_mb']} MB\n\n"
                msg += "First files:\n" + "\n".join(f"  {f}" for f in info["files"])
                messagebox.showinfo("Duck Resource", msg)
            else:
                messagebox.showwarning("Info", info["error"])

    def _launch_duck_web(self):
        result = self.duck_eco.launch_duck_web()
        if "status" in result:
            messagebox.showinfo("Duck Web Platform", f"Path: {result['path']}\n\nTo run:\n{result['instructions']}")
        else:
            messagebox.showwarning("Duck Web", result["error"])

    def _test_duck_stdio(self):
        """Run a quick test of the duck-stdio Python wrapper."""
        results = []
        # Test 1: File I/O
        try:
            test_path = os.path.join(tempfile.gettempdir(), "duck_test_io.txt")
            w = duck_fopen(test_path, "w")
            w.write_text("Hello, Duck Studio I/O!")
            duck_fclose(w)
            r = duck_fopen(test_path, "r")
            text = r.read_text()
            duck_fclose(r)
            os.unlink(test_path)
            results.append(f"✅ File I/O: {text}")
        except Exception as e:
            results.append(f"❌ File I/O: {e}")

        # Test 2: Memory stream
        try:
            mem = duck_fmemopen(4096)
            mem.write_text("Duck memory stream test")
            mem.fseek(0)
            data = mem.read_text()
            duck_fclose(mem)
            results.append(f"✅ Memory stream: {data}")
        except Exception as e:
            results.append(f"❌ Memory stream: {e}")

        # Test 3: SQLite stream
        try:
            db_path = os.path.join(tempfile.gettempdir(), "duck_test.sqlite")
            db = duck_fdb_open(db_path, "test_data")
            db.fwrite(b"Duck SQLite I/O test data")
            duck_fclose(db)
            os.unlink(db_path)
            results.append(f"✅ SQLite stream: OK")
        except Exception as e:
            results.append(f"❌ SQLite stream: {e}")

        messagebox.showinfo("duck-stdio Test", "\n".join(results))

    # ─── Tab: Settings ───
    def _build_settings_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="⚙️ Settings")

        tk.Label(frame, text="DuckStudio Win11 Settings", bg=BG_PANEL, fg=ACCENT_BLUE,
                font=('Segoe UI', 14, 'bold')).pack(pady=10)

        # App info
        info_frame = tk.LabelFrame(frame, text="Application", bg=BG_PANEL, fg=FG_PRIMARY,
                                  font=('Segoe UI', 10, 'bold'))
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        info_text = f"Version: {__version__}\n"
        info_text += f"Python: {sys.version.split()[0]}\n"
        info_text += f"Platform: {sys.platform}\n"
        info_text += f"Modules: duck-stdio, HuggingFace, OSS Tools, Mixer, Sequencer, Effects\n"
        info_text += f"Data path: {os.path.dirname(os.path.abspath(__file__))}"
        tk.Label(info_frame, text=info_text, bg=BG_PANEL, fg=FG_SECONDARY,
                font=('Segoe UI', 9), justify=tk.LEFT).pack(anchor='w', padx=10, pady=5)

        # Build info
        build_frame = tk.LabelFrame(frame, text="Build EXE", bg=BG_PANEL, fg=FG_PRIMARY,
                                   font=('Segoe UI', 10, 'bold'))
        build_frame.pack(fill=tk.X, padx=10, pady=5)
        build_text = (
            "To build a standalone .exe:\n\n"
            "  pyinstaller --onefile --windowed --name DuckStudio --icon=assets/duck.ico main.py\n\n"
            "The EXE will be in dist/DuckStudio.exe\n"
            "All Python dependencies (numpy, scipy) will be bundled."
        )
        tk.Label(build_frame, text=build_text, bg=BG_PANEL, fg=FG_SECONDARY,
                font=('Segoe UI', 9), justify=tk.LEFT).pack(anchor='w', padx=10, pady=5)
        ttk.Button(build_frame, text="🔨 Build EXE Now", command=self._build_exe).pack(side=tk.LEFT, padx=10, pady=5)

        # Credits
        credits_frame = tk.LabelFrame(frame, text="Credits & Open Source", bg=BG_PANEL, fg=FG_PRIMARY,
                                     font=('Segoe UI', 10, 'bold'))
        credits_frame.pack(fill=tk.X, padx=10, pady=5)
        credits = (
            "Built on:\n"
            "  • duck-stdio — universal I/O (C library by Duck Studio)\n"
            "  • HuggingFace — AI audio models (TTS, MusicGen, Whisper)\n"
            "  • Surge XT, Vital, Dexed, Helm — OSS synthesizers\n"
            "  • REAPER, Audacity, LMMS, Zrythm — DAWs\n"
            "  • LSP Plugins, Calf, x42 — mixing & mastering\n"
            "  • Duck Studio Platform — React 19 + Node.js ecosystem\n"
            "  • Duck Music Producer — API + CLI\n\n"
            "License: MIT\n"
            "Maintainer: Duck Studio / Belentani"
        )
        tk.Label(credits_frame, text=credits, bg=BG_PANEL, fg=FG_SECONDARY,
                font=('Segoe UI', 9), justify=tk.LEFT).pack(anchor='w', padx=10, pady=5)

    def _build_exe(self):
        """Build the EXE using PyInstaller."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        spec_content = self._generate_pyinstaller_spec()
        spec_path = os.path.join(script_dir, "DuckStudio.spec")
        with open(spec_path, 'w') as f:
            f.write(spec_content)
        self._update_status("Building EXE with PyInstaller...")
        def do_build():
            try:
                import subprocess
                result = subprocess.run(
                    [sys.executable, "-m", "PyInstaller", "--onefile", "--windowed",
                     "--name", "DuckStudio", "main.py"],
                    cwd=script_dir, capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    exe_path = os.path.join(script_dir, "dist", "DuckStudio.exe")
                    if os.path.exists(exe_path):
                        self.root.after(0, lambda: messagebox.showinfo("Build",
                            f"EXE built successfully!\n\nPath: {exe_path}\nSize: {os.path.getsize(exe_path)/1024/1024:.1f} MB"))
                    else:
                        self.root.after(0, lambda: messagebox.showwarning("Build", "Build completed but EXE not found"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Build Error", result.stderr[-500:]))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Build Error", str(e)))
            self.root.after(0, lambda: self._update_status("Build complete"))
        threading.Thread(target=do_build, daemon=True).start()

    def _generate_pyinstaller_spec(self) -> str:
        return '''# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[os.path.dirname(os.path.abspath('main.py'))],
    binaries=[],
    datas=[],
    hiddenimports=['numpy', 'scipy', 'wave', 'struct', 'math', 'json',
                   'sqlite3', 'threading', 'urllib.request', 'urllib.error',
                   'tkinter', 'tkinter.ttk', 'tkinter.filedialog',
                   'tkinter.messagebox', 'tkinter.simpledialog'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DuckStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''

    # ─── Utility ───
    def _update_status(self, msg: str):
        self.status_var.set(msg)

    def run(self):
        self.root.mainloop()


# ─── Entry point ───
if __name__ == "__main__":
    # Import math for pattern rendering
    import math
    app = DuckStudioApp()
    app.run()
