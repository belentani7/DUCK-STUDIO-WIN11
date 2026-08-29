"""
huggingface.py — HuggingFace AI model integration for DuckStudio.
Provides: text-to-speech, audio generation, music generation, audio analysis.
Uses transformers/diffusers (lazy import) + HuggingFace Inference API as fallback.
"""
import os
import json
import urllib.request
import urllib.error
import wave
import struct
import math
import tempfile
from typing import Optional, Any

# ─── HuggingFace model catalog for music/audio ───
HF_AUDIO_MODELS = {
    "tts": {
        "facebook/mms-tts-eng": "Multilingual TTS — English (lightweight)",
        "facebook/mms-tts-por": "Multilingual TTS — Portuguese",
        "facebook/mms-tts-spa": "Multilingual TTS — Spanish",
        "microsoft/speecht5_tts": "SpeechT5 TTS — high quality",
        "suno/bark": "Bark — expressive TTS + music + sound effects",
        "coqui/XTTS-v2": "Coqui XTTS — multilingual voice cloning",
    },
    "asr": {
        "openai/whisper-large-v3": "Whisper v3 — best ASR, multilingual",
        "openai/whisper-medium": "Whisper medium — balanced",
        "openai/whisper-small": "Whisper small — fast",
        "facebook/wav2vec2-large-960h": "Wav2Vec2 — English ASR",
    },
    "music_gen": {
        "facebook/musicgen-small": "MusicGen — 300M, pop/ambient music",
        "facebook/musicgen-medium": "MusicGen — 1.5B, better quality",
        "facebook/musicgen-large": "MusicGen — 3.3B, highest quality",
        "facebook/musicgen-melody": "MusicGen Melody — conditioned on melody",
        "facebook/audiogen": "AudioGen — sound effects, ambience",
    },
    "audio_classification": {
        "MIT/ast-finetuned-audioset-10-10-0.4593": "Audio Spectrogram Transformer",
        "facebook/wav2vec2-base-10k-voxpopuli-ft": "Language classification",
    },
    "audio_to_audio": {
        "JorisCos/DCCRN": "Deep Complex Convolution Recurrent Network — denoising",
        "openhpi/voicefixer": "VoiceFixer — restore degraded audio",
    },
}

class HuggingFaceClient:
    """HuggingFace API + local model integration."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY", "")
        self.api_base = "https://api-inference.huggingface.co/models"
        self._local_models: dict = {}

    def set_token(self, token: str):
        self.token = token

    def has_token(self) -> bool:
        return bool(self.token)

    # ─── Remote Inference API ───
    def infer_remote(self, model: str, data: bytes, content_type: str = "audio/wav") -> dict:
        """Call HuggingFace Inference API for a model."""
        if not self.has_token():
            return {"error": "No HF token set. Get one at https://huggingface.co/settings/tokens"}
        url = f"{self.api_base}/{model}"
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Content-Type", content_type)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = resp.read()
                ct = resp.headers.get("Content-Type", "")
                if "audio" in ct or "application/octet-stream" in ct:
                    return {"audio": body, "content_type": ct}
                else:
                    return json.loads(body)
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}"}
        except Exception as e:
            return {"error": str(e)}

    # ─── Text-to-Speech ───
    def text_to_speech(self, text: str, model: str = "facebook/mms-tts-eng",
                       language: str = "en") -> dict:
        """Generate speech from text via HuggingFace TTS model."""
        data = json.dumps({"inputs": text}).encode('utf-8')
        return self.infer_remote(model, data, "application/json")

    # ─── Music Generation ───
    def generate_music(self, prompt: str, model: str = "facebook/musicgen-small",
                      duration_seconds: float = 10.0) -> dict:
        """Generate music from a text prompt via MusicGen."""
        payload = {
            "inputs": prompt,
            "parameters": {
                "duration": duration_seconds,
                "sampling_rate": 32000,
            }
        }
        data = json.dumps(payload).encode('utf-8')
        return self.infer_remote(model, data, "application/json")

    # ─── Audio Effects Generation ───
    def generate_sfx(self, prompt: str, model: str = "facebook/audiogen",
                     duration_seconds: float = 5.0) -> dict:
        """Generate sound effects from text."""
        payload = {
            "inputs": prompt,
            "parameters": {"duration": duration_seconds}
        }
        data = json.dumps(payload).encode('utf-8')
        return self.infer_remote(model, data, "application/json")

    # ─── Speech Recognition (ASR) ───
    def transcribe_audio(self, audio_path: str, model: str = "openai/whisper-large-v3") -> dict:
        """Transcribe audio file via Whisper."""
        if not os.path.exists(audio_path):
            return {"error": f"File not found: {audio_path}"}
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
        return self.infer_remote(model, audio_data, "audio/wav")

    # ─── Local synthesis fallback (no GPU/internet needed) ───
    def local_tone(self, frequency: float = 440.0, duration: float = 2.0,
                   sample_rate: int = 44100, amplitude: float = 0.5) -> str:
        """Generate a pure tone locally (no external model). Returns WAV file path."""
        num_samples = int(duration * sample_rate)
        # Generate sine wave samples
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            # Apply gentle envelope (attack/decay)
            env = min(1.0, min(i / (sample_rate * 0.01), (num_samples - i) / (sample_rate * 0.01)))
            value = int(amplitude * env * 32767 * math.sin(2 * math.pi * frequency * t))
            samples.append(struct.pack('<h', value))
        # Write WAV
        filepath = os.path.join(tempfile.gettempdir(), "duck_tone.wav")
        with wave.open(filepath, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b''.join(samples))
        return filepath

    def local_chord(self, frequencies: list, duration: float = 2.0,
                    sample_rate: int = 44100, amplitude: float = 0.3) -> str:
        """Generate a chord (multiple frequencies) locally."""
        num_samples = int(duration * sample_rate)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            env = min(1.0, min(i / (sample_rate * 0.01), (num_samples - i) / (sample_rate * 0.01)))
            total = sum(amplitude * math.sin(2 * math.pi * f * t) for f in frequencies)
            total = max(-1.0, min(1.0, total))
            value = int(total * env * 32767)
            samples.append(struct.pack('<h', value))
        filepath = os.path.join(tempfile.gettempdir(), "duck_chord.wav")
        with wave.open(filepath, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b''.join(samples))
        return filepath

    def local_drum_pattern(self, bpm: int = 120, bars: int = 4,
                           pattern: str = "four-on-the-floor") -> str:
        """Generate a drum pattern locally using synthesis."""
        sample_rate = 44100
        beat_duration = 60.0 / bpm  # seconds per beat
        total_duration = beat_duration * 4 * bars  # 4/4 time
        num_samples = int(total_duration * sample_rate)
        # Kick: low sine burst, Snare: noise burst, Hat: high noise
        samples = bytearray(num_samples * 2)  # 16-bit mono
        def write_sample(idx, value):
            if 0 <= idx < num_samples:
                offset = idx * 2
                struct.pack_into('<h', samples, offset, max(-32768, min(32767, int(value))))
        def kick(pos, length=2000):
            for j in range(length):
                env = (1 - j / length) ** 2
                freq = 80 + 40 * (1 - j / length)
                val = env * 0.8 * math.sin(2 * math.pi * freq * j / sample_rate) * 32767
                write_sample(pos + j, val)
        def snare(pos, length=4000):
            for j in range(length):
                env = (1 - j / length) ** 1.5
                noise = (j % 7 - 3) * 0.3
                tone = math.sin(2 * math.pi * 200 * j / sample_rate) * 0.3
                val = env * (noise + tone) * 0.5 * 32767
                write_sample(pos + j, val)
        def hat(pos, length=1000):
            for j in range(length):
                env = (1 - j / length) ** 3
                noise = (j % 5 - 2) * 0.4
                val = env * noise * 0.3 * 32767
                write_sample(pos + j, val)
        # Generate pattern
        beat_samples = int(beat_duration * sample_rate)
        for bar in range(bars):
            for beat in range(4):
                pos = (bar * 4 + beat) * beat_samples
                if pattern == "four-on-the-floor":
                    kick(pos)
                    if beat % 2 == 1:
                        snare(pos)
                    hat(pos)
                    hat(pos + beat_samples // 2)
                elif pattern == "breakbeat":
                    if beat == 0 or beat == 2:
                        kick(pos)
                    if beat == 1:
                        snare(pos)
                    hat(pos + beat_samples // 4)
                elif pattern == "trap":
                    kick(pos)
                    if beat % 4 == 2:
                        snare(pos + beat_samples // 2)
                    for h in range(4):
                        hat(pos + h * beat_samples // 4, 500)
        filepath = os.path.join(tempfile.gettempdir(), "duck_drum_pattern.wav")
        with wave.open(filepath, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(bytes(samples))
        return filepath

    def local_sweep(self, start_freq: float = 20.0, end_freq: float = 20000.0,
                     duration: float = 3.0, sample_rate: int = 44100) -> str:
        """Generate a frequency sweep (useful for testing/analysis)."""
        num_samples = int(duration * sample_rate)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            progress = i / num_samples
            freq = start_freq * (end_freq / start_freq) ** progress
            env = min(1.0, min(i / (sample_rate * 0.05), (num_samples - i) / (sample_rate * 0.05)))
            val = int(0.5 * env * 32767 * math.sin(2 * math.pi * freq * t))
            samples.append(struct.pack('<h', val))
        filepath = os.path.join(tempfile.gettempdir(), "duck_sweep.wav")
        with wave.open(filepath, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b''.join(samples))
        return filepath

    # ─── Local whisper (offline) ───
    def local_transcribe(self, audio_path: str) -> dict:
        """Attempt local transcription using transformers if available."""
        try:
            import importlib
            torch = importlib.import_module('torch')
            torchaudio = importlib.import_module('torchaudio')
            transformers = importlib.import_module('transformers')
            # This requires torch + transformers installed
            processor = transformers.WhisperProcessor.from_pretrained("openai/whisper-small")
            model = transformers.WhisperForConditionalGeneration.from_pretrained("openai/whisper-small")
            wav_data, sr = torchaudio.load(audio_path)
            if sr != 16000:
                wav_data = torchaudio.functional.resample(wav_data, sr, 16000)
            input_features = processor(wav_data.squeeze().numpy(), sampling_rate=16000, return_tensors="pt").input_features
            predicted_ids = model.generate(input_features)
            text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
            return {"text": text, "engine": "whisper-local"}
        except ImportError:
            return {"error": "Local transcription requires torch + transformers. Install: pip install torch torchaudio transformers", "engine": "none"}
        except Exception as e:
            return {"error": str(e), "engine": "error"}

    # ─── List models ───
    def list_models(self, category: str = "all") -> dict:
        if category == "all":
            return HF_AUDIO_MODELS
        return HF_AUDIO_MODELS.get(category, {})
