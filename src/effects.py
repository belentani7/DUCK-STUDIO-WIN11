"""
effects.py — DSP effects chain: reverb, delay, distortion, chorus, filter.
Pure Python using numpy. No external dependencies.
"""
import numpy as np
import math
from typing import Optional

class Effect:
    """Base effect class."""
    name = "Effect"
    parameters = {}

    def process(self, data: np.ndarray, sample_rate: int = 44100) -> np.ndarray:
        return data

    def get_info(self) -> dict:
        return {"name": self.name, "parameters": self.parameters}


class Reverb(Effect):
    name = "Reverb"

    def __init__(self, room_size: float = 0.5, damping: float = 0.5,
                 wet: float = 0.3, dry: float = 0.7):
        self.room_size = room_size  # 0.0 - 1.0
        self.damping = damping      # 0.0 - 1.0
        self.wet = wet
        self.dry = dry
        self.parameters = {"room_size": room_size, "damping": damping, "wet": wet, "dry": dry}

    def process(self, data: np.ndarray, sample_rate: int = 44100) -> np.ndarray:
        if len(data) == 0:
            return data
        # Simple Schroeder reverb with comb + allpass filters
        comb_delays = [int(0.0297 * sample_rate), int(0.0371 * sample_rate),
                       int(0.0411 * sample_rate), int(0.0437 * sample_rate)]
        allpass_delays = [int(0.0050 * sample_rate), int(0.0017 * sample_rate)]
        feedback = self.room_size * 0.7
        damping_factor = 1.0 - self.damping
        # Comb filters
        comb_out = np.zeros_like(data, dtype=np.float64)
        for delay in comb_delays:
            buf = np.zeros(delay + len(data), dtype=np.float64)
            for i in range(len(data)):
                buf[i + delay] = data[i].astype(np.float64) + buf[i] * feedback * damping_factor
            comb_out += buf[:len(data)] / len(comb_delays)
        # Allpass filters
        ap_gain = 0.7
        out = comb_out.copy()
        for delay in allpass_delays:
            buf = np.zeros(delay + len(out), dtype=np.float64)
            for i in range(len(out)):
                buf[i + delay] = out[i] + buf[i] * ap_gain
                out[i] = buf[i + delay] * -ap_gain + buf[i + delay]
        # Mix dry/wet
        if data.ndim == 1:
            result = data.astype(np.float64) * self.dry + out * self.wet
        else:
            result = data.astype(np.float64)
            for ch in range(data.shape[1]):
                result[:, ch] = data[:, ch].astype(np.float64) * self.dry + out[:len(data)] * self.wet
        return result.astype(np.float32)


class Delay(Effect):
    name = "Delay"

    def __init__(self, time_ms: float = 250, feedback: float = 0.3,
                 mix: float = 0.3):
        self.time_ms = time_ms
        self.feedback = feedback  # 0.0 - 0.9
        self.mix = mix
        self.parameters = {"time_ms": time_ms, "feedback": feedback, "mix": mix}

    def process(self, data: np.ndarray, sample_rate: int = 44100) -> np.ndarray:
        if len(data) == 0:
            return data
        delay_samples = int(self.time_ms / 1000.0 * sample_rate)
        out = data.copy().astype(np.float64)
        if data.ndim == 1:
            for i in range(delay_samples, len(data)):
                out[i] += out[i - delay_samples] * self.feedback
        else:
            for ch in range(data.shape[1]):
                for i in range(delay_samples, len(data)):
                    out[i, ch] += out[i - delay_samples, ch] * self.feedback
        return (data.astype(np.float64) * (1 - self.mix) + out * self.mix).astype(np.float32)


class Distortion(Effect):
    name = "Distortion"

    def __init__(self, drive: float = 0.5, tone: float = 0.5,
                 level: float = 0.7):
        self.drive = drive  # 0.0 - 1.0
        self.tone = tone
        self.level = level
        self.parameters = {"drive": drive, "tone": tone, "level": level}

    def process(self, data: np.ndarray, sample_rate: int = 44100) -> np.ndarray:
        if len(data) == 0:
            return data
        gain = 1.0 + self.drive * 10
        driven = data * gain
        # Soft clipping (tanh)
        out = np.tanh(driven * 2) / np.tanh(2)
        return (out * self.level).astype(np.float32)


class Compressor(Effect):
    name = "Compressor"

    def __init__(self, threshold: float = -20, ratio: float = 4,
                 attack_ms: float = 10, release_ms: float = 100):
        self.threshold = threshold  # dB
        self.ratio = ratio
        self.attack_ms = attack_ms
        self.release_ms = release_ms
        self.parameters = {"threshold": threshold, "ratio": ratio, "attack_ms": attack_ms, "release_ms": release_ms}

    def process(self, data: np.ndarray, sample_rate: int = 44100) -> np.ndarray:
        if len(data) == 0:
            return data
        threshold_lin = 10 ** (self.threshold / 20)
        attack_coef = math.exp(-1 / (self.attack_ms / 1000 * sample_rate))
        release_coef = math.exp(-1 / (self.release_ms / 1000 * sample_rate))
        out = data.copy().astype(np.float64)
        gain = 1.0
        if data.ndim == 1:
            for i in range(len(data)):
                env = abs(data[i])
                if env > threshold_lin:
                    target_gain = 1.0 / self.ratio + (1 - 1.0/self.ratio) * threshold_lin / max(env, 1e-10)
                else:
                    target_gain = 1.0
                coef = attack_coef if env > threshold_lin else release_coef
                gain = coef * gain + (1 - coef) * target_gain
                out[i] = data[i] * gain
        else:
            for ch in range(data.shape[1]):
                gain = 1.0
                for i in range(len(data)):
                    env = abs(data[i, ch])
                    if env > threshold_lin:
                        target_gain = 1.0/self.ratio + (1-1.0/self.ratio) * threshold_lin / max(env, 1e-10)
                    else:
                        target_gain = 1.0
                    coef = attack_coef if env > threshold_lin else release_coef
                    gain = coef * gain + (1 - coef) * target_gain
                    out[i, ch] = data[i, ch] * gain
        return out.astype(np.float32)


class LowPassFilter(Effect):
    name = "Low-Pass Filter"

    def __init__(self, cutoff: float = 1000, resonance: float = 0.7):
        self.cutoff = cutoff  # Hz
        self.resonance = resonance  # Q factor
        self.parameters = {"cutoff": cutoff, "resonance": resonance}

    def process(self, data: np.ndarray, sample_rate: int = 44100) -> np.ndarray:
        if len(data) == 0:
            return data
        w0 = 2 * math.pi * self.cutoff / sample_rate
        alpha = math.sin(w0) / (2 * self.resonance)
        b0 = (1 - math.cos(w0)) / 2
        b1 = 1 - math.cos(w0)
        b2 = (1 - math.cos(w0)) / 2
        a0 = 1 + alpha
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha
        b = [b0/a0, b1/a0, b2/a0]
        a = [1, a1/a0, a2/a0]
        out = data.copy().astype(np.float64)
        if data.ndim == 1:
            y = 0.0
            for i in range(1, len(data)):
                y = b[0]*data[i] + b[1]*data[i-1] + b[2]*(data[i-2] if i>=2 else 0) - a[1]*y - a[2]*0
                out[i] = y
        else:
            for ch in range(data.shape[1]):
                y = 0.0
                for i in range(1, len(data)):
                    y = b[0]*data[i,ch] + b[1]*data[i-1,ch] + b[2]*(data[i-2,ch] if i>=2 else 0) - a[1]*y
                    out[i, ch] = y
        return out.astype(np.float32)


class HighPassFilter(Effect):
    name = "High-Pass Filter"

    def __init__(self, cutoff: float = 2000, resonance: float = 0.7):
        self.cutoff = cutoff
        self.resonance = resonance
        self.parameters = {"cutoff": cutoff, "resonance": resonance}

    def process(self, data: np.ndarray, sample_rate: int = 44100) -> np.ndarray:
        if len(data) == 0:
            return data
        w0 = 2 * math.pi * self.cutoff / sample_rate
        alpha = math.sin(w0) / (2 * self.resonance)
        b0 = (1 + math.cos(w0)) / 2
        b1 = -(1 + math.cos(w0))
        b2 = (1 + math.cos(w0)) / 2
        a0 = 1 + alpha
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha
        b = [b0/a0, b1/a0, b2/a0]
        a = [1, a1/a0, a2/a0]
        out = data.copy().astype(np.float64)
        if data.ndim == 1:
            y = 0.0
            for i in range(1, len(data)):
                y = b[0]*data[i] + b[1]*data[i-1] + b[2]*(data[i-2] if i>=2 else 0) - a[1]*y
                out[i] = y
        else:
            for ch in range(data.shape[1]):
                y = 0.0
                for i in range(1, len(data)):
                    y = b[0]*data[i,ch] + b[1]*data[i-1,ch] + b[2]*(data[i-2,ch] if i>=2 else 0) - a[1]*y
                    out[i, ch] = y
        return out.astype(np.float32)


# ─── Effect registry ───
EFFECT_REGISTRY = {
    "reverb": Reverb,
    "delay": Delay,
    "distortion": Distortion,
    "compressor": Compressor,
    "lowpass": LowPassFilter,
    "highpass": HighPassFilter,
}

def list_effects() -> list:
    return list(EFFECT_REGISTRY.keys())

def create_effect(name: str, **params) -> Optional[Effect]:
    cls = EFFECT_REGISTRY.get(name)
    if cls:
        return cls(**params)
    return None
