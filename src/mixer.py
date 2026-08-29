"""
mixer.py — Digital audio mixing engine.
Provides multi-track mixing, EQ, compression, reverb, volume, pan, and export.
Uses numpy for DSP. Pure Python, no external dependencies beyond numpy.
"""
import os
import wave
import struct
import math
import tempfile
from typing import Optional, Any
import numpy as np

class AudioTrack:
    """A single audio track in the mixer."""

    def __init__(self, name: str, sample_rate: int = 44100, channels: int = 2):
        self.name = name
        self.sample_rate = sample_rate
        self.channels = channels
        self.samples: np.ndarray = np.zeros((0, channels), dtype=np.float32)
        self.volume: float = 1.0  # 0.0 to 2.0
        self.pan: float = 0.0     # -1.0 (left) to 1.0 (right)
        self.muted: bool = False
        self.solo: bool = False
        self.color: str = "#3b82f6"
        self._effects: list = []
        # EQ bands
        self.eq_low_gain: float = 0.0   # dB
        self.eq_mid_gain: float = 0.0
        self.eq_high_gain: float = 0.0

    def load_wav(self, filepath: str) -> dict:
        """Load a WAV file into this track."""
        try:
            with wave.open(filepath, 'rb') as wav:
                self.sample_rate = wav.getframerate()
                n_channels = wav.getnchannels()
                sampwidth = wav.getsampwidth()
                n_frames = wav.getnframes()
                raw = wav.readframes(n_frames)
            if sampwidth == 2:
                data = np.frombuffer(raw, dtype=np.int16)
            elif sampwidth == 1:
                data = np.frombuffer(raw, dtype=np.uint8).astype(np.int16) - 128
            elif sampwidth == 4:
                data = np.frombuffer(raw, dtype=np.int32)
            else:
                return {"error": f"Unsupported sample width: {sampwidth}"}
            # Reshape for channels
            if n_channels > 1:
                data = data.reshape(-1, n_channels)
            else:
                data = data.reshape(-1, 1)
            # Convert to float32 normalized
            self.samples = data.astype(np.float32) / 32768.0
            self.channels = n_channels
            return {"status": "loaded", "samples": len(self.samples), "duration": len(self.samples) / self.sample_rate}
        except Exception as e:
            return {"error": str(e)}

    def generate_tone(self, frequency: float = 440.0, duration: float = 2.0,
                      wave_type: str = "sine") -> dict:
        """Generate a tone and load it into this track."""
        num_samples = int(duration * self.sample_rate)
        t = np.linspace(0, duration, num_samples, endpoint=False, dtype=np.float32)
        if wave_type == "sine":
            data = np.sin(2 * np.pi * frequency * t)
        elif wave_type == "square":
            data = np.sign(np.sin(2 * np.pi * frequency * t))
        elif wave_type == "saw":
            data = 2 * (t * frequency - np.floor(0.5 + t * frequency))
        elif wave_type == "triangle":
            data = 2 * np.abs(2 * (t * frequency - np.floor(0.5 + t * frequency))) - 1
        elif wave_type == "noise":
            data = np.random.uniform(-1, 1, num_samples).astype(np.float32)
        else:
            data = np.sin(2 * np.pi * frequency * t)
        self.samples = data.reshape(-1, 1)
        self.channels = 1
        return {"status": "generated", "samples": num_samples, "duration": duration}

    def apply_volume_pan(self) -> np.ndarray:
        """Return samples with volume and pan applied."""
        if self.muted or len(self.samples) == 0:
            return np.zeros_like(self.samples)
        out = self.samples * self.volume
        if self.channels >= 2:
            left_gain = (1.0 - max(0.0, self.pan)) * self.volume
            right_gain = (1.0 + min(0.0, self.pan)) * self.volume
            out[:, 0] = self.samples[:, 0] * left_gain
            out[:, 1] = self.samples[:, 1] * right_gain
        return out

    def apply_eq(self, data: np.ndarray) -> np.ndarray:
        """Apply 3-band EQ (low/mid/high)."""
        if len(data) == 0:
            return data
        sr = self.sample_rate
        # Simple biquad-based EQ
        def biquad_peak(data, freq, gain_db, q=0.707):
            if gain_db == 0:
                return data
            A = 10 ** (gain_db / 40)
            w0 = 2 * np.pi * freq / sr
            alpha = np.sin(w0) / (2 * q)
            b0 = 1 + alpha * A
            b1 = -2 * np.cos(w0)
            b2 = 1 - alpha * A
            a0 = 1 + alpha / A
            a1 = -2 * np.cos(w0)
            a2 = 1 - alpha / A
            b = np.array([b0, b1, b2]) / a0
            a = np.array([1, a1 / a0, a2 / a0])
            # Apply IIR filter
            if data.ndim == 1:
                return _iir_filter(data, b, a)
            else:
                for ch in range(data.shape[1]):
                    data[:, ch] = _iir_filter(data[:, ch], b, a)
                return data
        data = data.copy()
        if self.eq_low_gain != 0:
            data = biquad_peak(data, 200, self.eq_low_gain)
        if self.eq_mid_gain != 0:
            data = biquad_peak(data, 1000, self.eq_mid_gain)
        if self.eq_high_gain != 0:
            data = biquad_peak(data, 5000, self.eq_high_gain)
        return data

    def add_effect(self, effect_type: str, params: dict = None):
        self._effects.append({"type": effect_type, "params": params or {}})

    def remove_effect(self, index: int):
        if 0 <= index < len(self._effects):
            self._effects.pop(index)

    def get_info(self) -> dict:
        return {
            "name": self.name,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "duration": len(self.samples) / self.sample_rate if self.sample_rate else 0,
            "sample_count": len(self.samples),
            "volume": self.volume,
            "pan": self.pan,
            "muted": self.muted,
            "solo": self.solo,
            "effects": self._effects,
        }


def _iir_filter(x, b, a):
    """Simple IIR filter implementation."""
    y = np.zeros_like(x)
    for i in range(len(x)):
        y[i] = b[0] * x[i]
        if i >= 1:
            y[i] += b[1] * x[i-1] - a[1] * y[i-1]
        if i >= 2:
            y[i] += b[2] * x[i-2] - a[2] * y[i-2]
    return y


class Mixer:
    """Multi-track audio mixer."""

    def __init__(self, sample_rate: int = 44100):
        self.tracks: list[AudioTrack] = []
        self.sample_rate = sample_rate
        self.master_volume: float = 1.0

    def add_track(self, name: str) -> AudioTrack:
        track = AudioTrack(name, self.sample_rate)
        self.tracks.append(track)
        return track

    def remove_track(self, index: int):
        if 0 <= index < len(self.tracks):
            self.tracks.pop(index)

    def get_track(self, index: int) -> Optional[AudioTrack]:
        if 0 <= index < len(self.tracks):
            return self.tracks[index]
        return None

    def mix(self) -> np.ndarray:
        """Mix all tracks into a single output."""
        # Determine if any track is soloed
        any_solo = any(t.solo for t in self.tracks)
        # Find max length
        max_len = max((len(t.samples) for t in self.tracks if not t.muted), default=0)
        if max_len == 0:
            return np.zeros((0, 2), dtype=np.float32)
        output = np.zeros((max_len, 2), dtype=np.float32)
        for track in self.tracks:
            if track.muted or (any_solo and not track.solo):
                continue
            processed = track.apply_volume_pan()
            processed = track.apply_eq(processed)
            # Convert to stereo if needed
            if processed.shape[1] == 1:
                processed = np.repeat(processed, 2, axis=1)
            elif processed.shape[1] == 1:
                processed = np.column_stack([processed[:, 0], processed[:, 0]])
            # Mix in
            length = min(len(processed), max_len)
            output[:length] += processed[:length]
        # Apply master volume with soft clipping
        output = output * self.master_volume
        output = np.clip(output, -1.0, 1.0)
        return output

    def export_wav(self, filepath: str) -> dict:
        """Export the mixed output as a WAV file."""
        mixed = self.mix()
        if len(mixed) == 0:
            return {"error": "No audio to export"}
        int_data = (mixed * 32767).astype(np.int16)
        try:
            with wave.open(filepath, 'w') as wav:
                wav.setnchannels(2)
                wav.setsampwidth(2)
                wav.setframerate(self.sample_rate)
                wav.writeframes(int_data.tobytes())
            return {"status": "exported", "path": filepath, "duration": len(mixed) / self.sample_rate}
        except Exception as e:
            return {"error": str(e)}

    def get_status(self) -> dict:
        return {
            "sample_rate": self.sample_rate,
            "track_count": len(self.tracks),
            "master_volume": self.master_volume,
            "tracks": [t.get_info() for t in self.tracks],
        }
