"""
oss_tools.py — Discover, launch, and manage Open-Source audio tools on Windows.
Surge XT, Vital, Dexed, Helm, Hydrogen, LSP Plugins, Calf, REAPER, Audacity.
Also integrates with the existing Duck Studio ecosystem files on this PC.
"""
import os
import sys
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional, Any

# ─── OSS Tool Registry ───
OSS_TOOLS = {
    "reaper": {
        "name": "REAPER",
        "category": "DAW",
        "description": "Professional DAW — semi-open ($60 perpetual license)",
        "windows_url": "https://www.reaper.fm/files/reaper706_x64-install.exe",
        "linux_url": "https://www.reaper.fm/files/7.x/reaper706_linux_x86_64.tar.xz",
        "mac_url": "https://www.reaper.fm/files/reaper706_dmg.dmg",
        "features": ["MIDI", "Audio recording", "Mixing", "Mastering", "VST/VST3", "LV2", "JS FX"],
        "paid": True,
        "price": "$60",
    },
    "surge_xt": {
        "name": "Surge XT",
        "category": "Synthesizer",
        "description": "Hybrid synthesizer — wavetable, FM, subtrative. Full OSS (GPL3).",
        "windows_url": "https://github.com/surge-synthesizer/releases/releases/download/1.3.6/Surge-XT-1.3.6-win64.exe",
        "github": "https://github.com/surge-synthesizer/surge",
        "features": ["Wavetable", "FM", "Subtractive", "Modulation", "MPE", "VST3", "LV2"],
        "paid": False,
    },
    "vital": {
        "name": "Vital",
        "category": "Wavetable Synth",
        "description": "Spectral warping wavetable synth. Free tier with 25 presets.",
        "windows_url": "https://account.vital.audio/download/vital-win64",
        "github": "https://github.com/matttt/vital",
        "features": ["Wavetable", "Spectral", "Effects", "TTWT bifilter", "VST3"],
        "paid": False,
    },
    "dexed": {
        "name": "Dexed",
        "category": "FM Synth",
        "description": "DX7 II emulator. OSS. VST3/LV2/Standalone.",
        "github": "https://github.com/asb2m10/dexed",
        "windows_url": "https://github.com/asb2m10/dexed/releases/download/v0.9.6/Dexed-0.9.6-win64.exe",
        "features": ["FM synthesis", "DX7 presets", "VST3", "LV2", "Standalone"],
        "paid": False,
    },
    "helm": {
        "name": "Helm",
        "category": "Subtractive Synth",
        "description": "Polyphonic subtractive synth by Matt Tytel. OSS.",
        "github": "https://github.com/mtytel/helm",
        "windows_url": "https://tytel.org/helm/helm-win64.exe",
        "features": ["Subtractive", "Polyphonic", "VST3", "LV2", "Standalone"],
        "paid": False,
    },
    "hydrogen": {
        "name": "Hydrogen",
        "category": "Drum Machine",
        "description": "Advanced drum machine and pattern sequencer. OSS (GPL2).",
        "github": "https://github.com/hydrogen-music/hydrogen",
        "windows_url": "https://github.com/hydrogen-music/hydrogen/releases/download/1.2.3/hydrogen-1.2.3-x86_64.exe",
        "features": ["Pattern sequencer", "Sample layering", "MIDI", "Jack transport", "LADSPA"],
        "paid": False,
    },
    "lsp_plugins": {
        "name": "LSP Plugins",
        "category": "Mixing & Mastering",
        "description": "Linux Studio Plugins — EQ, compressor, limiter, reverb, analyzer. OSS.",
        "github": "https://github.com/lsp-plugins/lsp-plugins",
        "windows_url": "https://github.com/lsp-plugins/lsp-plugins/releases/download/1.2.12/lsp-plugins-1.2.12-win64.exe",
        "features": ["Parametric EQ", "Compressor", "Limiter", "Reverb", "Spectrum analyzer", "Loudness meter"],
        "paid": False,
    },
    "calf": {
        "name": "Calf Studio Gear",
        "category": "Mixing",
        "description": "Studio gear plugins — EQ, compressor, reverb, filter, saturation. OSS.",
        "github": "https://github.com/calf-studio-gear/calf",
        "features": ["EQ", "Compressor", "Reverb", "Multi-flanger", "Vocoder", "Phaser"],
        "paid": False,
    },
    "audacity": {
        "name": "Audacity",
        "category": "Audio Editor",
        "description": "Multi-track audio editor. OSS (GPL2). Already installed on this PC.",
        "github": "https://github.com/audacity/audacity",
        "windows_url": "https://github.com/audacity/audacity/releases/download/Audacity-3.7.8/audacity-win-3.7.8-x64.exe",
        "features": ["Multi-track", "Effects", "Recording", "Export MP3/WAV/FLAC", "LADSPA", "LV2", "Nyquist"],
        "paid": False,
        "installed": True,
        "installed_path": r"C:\Program Files\Audacity",
    },
    "x42_meters": {
        "name": "x42 Meters",
        "category": "Mastering",
        "description": "LUFS/EBU R128 loudness meter and K-metering. OSS.",
        "github": "https://github.com/x42/meters.lv2",
        "features": ["LUFS metering", "EBU R128", "K-metering", "True peak"],
        "paid": False,
    },
    "zrythm": {
        "name": "Zrythm",
        "category": "DAW",
        "description": "Fully featured DAW — MIDI, audio, automation. OSS (AGPL3).",
        "github": "https://github.com/zrythm/zrythm",
        "windows_url": "https://www.zrythm.org/downloads/zrythm-installer-windows.exe",
        "features": ["MIDI", "Audio", "Automation", "VST3", "LV2", "Plugin hosting"],
        "paid": False,
    },
    "lmms": {
        "name": "LMMS",
        "category": "DAW",
        "description": "Free open-source DAW — beat making, synth, sampling. OSS (GPL2).",
        "github": "https://github.com/LMMS/lmms",
        "windows_url": "https://github.com/LMMS/lmms/releases/download/v1.2.2/lmms-1.2.2-win64.exe",
        "features": ["Beat/bassline editor", "Piano roll", "Built-in synths", "VST support", "SF2 player"],
        "paid": False,
    },
}

class OSSToolManager:
    """Manage discovery, installation, and launch of OSS audio tools."""

    def __init__(self):
        self.tools = OSS_TOOLS
        self._installed_cache: Optional[dict] = None

    def list_all(self) -> dict:
        return self.tools

    def list_by_category(self, category: str) -> dict:
        return {k: v for k, v in self.tools.items() if v["category"] == category}

    def get_categories(self) -> list:
        return sorted(set(v["category"] for v in self.tools.values()))

    def detect_installed(self) -> dict:
        """Detect which tools are installed on this Windows system."""
        if self._installed_cache is not None:
            return self._installed_cache
        results = {}
        # Check common install paths
        search_paths = [
            os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"), ""),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"), ""),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), ""),
        ]
        exe_names = {
            "reaper": ["reaper.exe"],
            "audacity": ["audacity.exe"],
            "hydrogen": ["hydrogen.exe"],
            "lmms": ["lmms.exe"],
            "surge_xt": ["Surge XT.exe", "SurgeXT.exe"],
            "vital": ["Vital.exe"],
            "dexed": ["Dexed.exe"],
            "helm": ["Helm.exe"],
            "zrythm": ["zrythm.exe"],
        }
        for tool_key, exes in exe_names.items():
            found = False
            path = None
            for search_path in search_paths:
                for exe in exes:
                    full = os.path.join(search_path, exe)
                    if os.path.exists(full):
                        found = True
                        path = full
                        break
                if found:
                    break
            # Also check if it's already marked as installed
            if not found and self.tools.get(tool_key, {}).get("installed"):
                found = True
                path = self.tools[tool_key].get("installed_path", "unknown")
            results[tool_key] = {"installed": found, "path": path}
        self._installed_cache = results
        return results

    def launch_tool(self, tool_key: str) -> dict:
        """Launch a tool if it's installed."""
        detected = self.detect_installed()
        if tool_key not in detected or not detected[tool_key]["installed"]:
            return {"error": f"{tool_key} not installed. Path: {self.tools[tool_key]['windows_url']}"}
        path = detected[tool_key]["path"]
        if path and os.path.exists(path):
            try:
                subprocess.Popen([path])
                return {"status": "launched", "tool": tool_key, "path": path}
            except Exception as e:
                return {"error": f"Failed to launch: {e}"}
        return {"error": "Executable not found"}

    def download_installer(self, tool_key: str, dest_dir: str = None) -> dict:
        """Download the installer for a tool."""
        if tool_key not in self.tools:
            return {"error": f"Unknown tool: {tool_key}"}
        tool = self.tools[tool_key]
        url = tool.get("windows_url")
        if not url:
            return {"error": "No Windows download URL available"}
        if dest_dir is None:
            dest_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        filename = url.split("/")[-1]
        dest_path = os.path.join(dest_dir, filename)
        try:
            urllib.request.urlretrieve(url, dest_path)
            return {"status": "downloaded", "path": dest_path, "tool": tool_key}
        except Exception as e:
            return {"error": f"Download failed: {e}"}

    def open_in_browser(self, url: str) -> dict:
        """Open a URL in the default browser."""
        try:
            os.startfile(url)
            return {"status": "opened", "url": url}
        except Exception as e:
            return {"error": str(e)}


# ─── Duck Ecosystem Integration ───
DUCK_ECOSYSTEM_PATHS = {
    "duck_ultimo": r"C:\Users\USER\Downloads\DUCK_ULTIMO_EXTRACTED",
    "duck_studio_signed": r"C:\Users\USER\Downloads\DUCK_STUDIO_SIGNED_EXTRACT",
    "duck_stdio": r"C:\Users\USER\Downloads\duck-stdio-extract\duck-stdio",
    "duck_music_producer": r"C:\Users\USER\Documents\DUCK-MUSIC-PRODUCER-v1.0.0",
    "duck_a_gema": r"C:\Users\USER\Documents\DUCK-A-GEMA-1-LAB",
    "duck_studio_local_win11": r"C:\Users\USER\Documents\DUCK-STUDIO-LOCAL-WIN11",
}

class DuckEcosystem:
    """Interface to the existing Duck Studio ecosystem on this PC."""

    def __init__(self):
        self.paths = DUCK_ECOSYSTEM_PATHS

    def detect_available(self) -> dict:
        """Check which Duck resources exist."""
        results = {}
        for key, path in self.paths.items():
            results[key] = {
                "exists": os.path.isdir(path),
                "path": path,
            }
        return results

    def get_resource_info(self, resource_key: str) -> dict:
        """Get info about a specific Duck resource."""
        path = self.paths.get(resource_key)
        if not path or not os.path.isdir(path):
            return {"error": "Resource not found"}
        files = os.listdir(path)
        size = 0
        for f in files:
            fp = os.path.join(path, f)
            if os.path.isfile(fp):
                size += os.path.getsize(fp)
        return {
            "key": resource_key,
            "path": path,
            "file_count": len(files),
            "total_size_bytes": size,
            "total_size_mb": round(size / (1024*1024), 2),
            "files": files[:20],
        }

    def launch_duck_web(self) -> dict:
        """Try to launch the Duck Studio web platform (React/Node)."""
        duck_path = self.paths.get("duck_ultimo")
        if not duck_path or not os.path.isdir(duck_path):
            return {"error": "Duck Studio platform not found"}
        # Check if node/pnpm is available
        pnpm = shutil.which("pnpm") or shutil.which("npx")
        npm = shutil.which("npm")
        if not (pnm or npm):
            return {"error": "Node.js not found in PATH"}
        return {
            "status": "available",
            "path": duck_path,
            "instructions": f"cd {duck_path} && pnpm install && pnpm dev",
        }

    def launch_duck_music_api(self) -> dict:
        """Try to launch the DUCK MUSIC PRODUCER API."""
        duck_mp = self.paths.get("duck_music_producer")
        if not duck_mp or not os.path.isdir(duck_mp):
            return {"error": "Duck Music Producer not found"}
        return {
            "status": "available",
            "path": duck_mp,
            "instructions": f"cd {duck_mp} && pnpm install && pnpm duck:build",
        }
