# 🦆 DuckStudio Win11 — El Estudio Musical Más Completo del Mundo

**Versión:** 1.0.0  
**EXE:** `dist/DuckStudio.exe` (25.3 MB standalone)  
**Sistema:** Windows 11 (también Windows 10)  

---

## 📦 Qué es DuckStudio Win11

DuckStudio Win11 une en una sola aplicación:

1. **duck-stdio** — Motor I/O universal (file, memory, SQLite, Postgres, Redis, S3) — el código C del tarball `duck-stdio-complete (1).tar.gz`, reimplantado en Python
2. **HuggingFace AI** — 19 modelos: TTS, ASR (Whisper), MusicGen, AudioGen, clasificación de audio
3. **OSS Tools** — 12 herramientas open source: REAPER, Surge XT, Vital, Dexed, Helm, Hydrogen, LSP, Calf, Audacity, x42, Zrythm, LMMS
4. **Mixer** — Mezclador multi-pista con EQ 3 bandas, volumen, pan, export WAV
5. **Sequencer** — Step sequencer con 6 presets (four-on-the-floor, trap, breakbeat, boom-bap, DnB, reggaeton)
6. **Effects** — Reverb, Delay, Distortion, Compressor, Low-pass, High-pass (DSP puro Python + numpy)
7. **Duck Ecosystem** — Integra los 6 recursos Duck ya existentes en el PC

---

## 🚀 Ejecutar

### Opción 1: EXE (recomendado)
```
Doble clic en dist/DuckStudio.exe
```

### Opción 2: Python
```bash
cd C:\Users\USER\Documents\DUCK-STUDIO-WIN11
python main.py
```

---

## 🔨 Construir EXE

```bash
python -m PyInstaller --onefile --windowed --name DuckStudio main.py
```

El EXE se genera en `dist/DuckStudio.exe`.

---

## 🎵 Pestañas de la aplicación

| Tab | Función |
|-----|---------|
| 🏠 Studio | Overview, estadísticas, accesos rápidos |
| 🥁 Sequencer | Step sequencer con grid, presets, export WAV |
| 🎚️ Mixer | Multi-track mixing, EQ, volumen, pan, efectos |
| 🤖 HuggingFace | TTS, MusicGen, AudioGen, Whisper, síntesis local |
| 🛠️ OSS Tools | 12 herramientas OSS con detección y descarga |
| 🦆 Duck Ecosystem | 6 recursos Duck del PC, test duck-stdio I/O |
| ⚙️ Settings | Info, build EXE, créditos |

---

## 🧩 Módulos

### duck-stdio (Python)
- `duck_fopen(path, mode)` — File I/O
- `duck_fmemopen(size, data)` — Memory buffer
- `duck_fdb_open(db_path, table)` — SQLite stream
- `duck_fclose(stream)` — Close
- Thread-safe con locks
- Contadores bytes_read / bytes_written

### HuggingFace
- `text_to_speech(text, model)` — TTS
- `generate_music(prompt, model, duration)` — MusicGen
- `generate_sfx(prompt, model, duration)` — AudioGen
- `transcribe_audio(path, model)` — Whisper ASR
- `local_tone(freq, duration)` — Síntesis local (sin internet)
- `local_chord(frequencies, duration)` — Acordes
- `local_drum_pattern(bpm, bars, pattern)` — Drum patterns
- `local_sweep(start, end, duration)` — Frequency sweep

### OSS Tools (12)
| Herramienta | Categoría | Alternativa a |
|-------------|-----------|--------------|
| REAPER | DAW | FL Studio, Pro Tools |
| Zrythm | DAW | FL Studio |
| LMMS | DAW | FL Studio |
| Surge XT | Synth | Massive, Serum |
| Vital | Wavetable | Serum |
| Dexed | FM Synth | FM8 |
| Helm | Subtractive | Sylenth |
| Hydrogen | Drums | Superior Drummer |
| LSP Plugins | Mixing | FabFilter |
| Calf | Mixing | Waves |
| Audacity | Editor | (instalado ✅) |
| x42 Meters | Mastering | Ozone |

### Effects (6)
- Reverb (Schroeder, comb+allpass)
- Delay (feedback, mix)
- Distortion (tanh soft-clip)
- Compressor (RMS, attack/release)
- Low-pass (biquad)
- High-pass (biquad)

### Sequencer Presets (6)
- Four-on-the-floor (house, techno)
- Trap (modern hip-hop)
- Breakbeat (jungle, breaks)
- Boom-bap (classic hip-hop)
- Drum & Bass
- Reggaeton

---

## 📁 Estructura del proyecto

```
DUCK-STUDIO-WIN11/
├── main.py              # GUI principal (Tkinter, 7 pestañas)
├── src/
│   ├── __init__.py
│   ├── duck_stdio.py     # I/O universal (file, memory, SQLite)
│   ├── huggingface.py    # HF AI integration (19 modelos)
│   ├── oss_tools.py      # 12 OSS tools + Duck ecosystem
│   ├── mixer.py          # Multi-track mixer + EQ
│   ├── sequencer.py      # Step sequencer + presets
│   └── effects.py        # DSP effects (6)
├── dist/
│   └── DuckStudio.exe    # ← EXE standalone (25.3 MB)
├── build/                # PyInstaller build artifacts
├── README.md
└── DuckStudio.spec       # PyInstaller spec
```

---

## 🔗 Recursos Duck integrados

| Recurso | Ruta |
|---------|------|
| duck-stdio source | `Downloads\duck-stdio-extract\duck-stdio` |
| DUCK ULTIMO | `Downloads\DUCK_ULTIMO_EXTRACTED` |
| Duck Studio Platform | `Downloads\DUCK_ULTIMO_EXTRACTED` (React 19 + Node.js) |
| Duck Studio Signed | `Downloads\DUCK_STUDIO_SIGNED_EXTRACT` |
| Duck Music Producer | `Documents\DUCK-MUSIC-PRODUCER-v1.0.0` |
| Duck A Gema 1 Lab | `Documents\DUCK-A-GEMA-1-LAB` |
| Duck Studio Local Win11 | `Documents\DUCK-STUDIO-LOCAL-WIN11` |

---

## 🤖 HuggingFace — cómo usar

1. Ve a https://huggingface.co/settings/tokens
2. Crea un token (gratuito)
3. En DuckStudio → pestaña HuggingFace → pega el token
4. Selecciona categoría (tts, asr, music_gen, etc.)
5. Carga modelos
6. Usa TTS (texto→voz), MusicGen (texto→música), o síntesis local

**Modelos destacados:**
- `facebook/musicgen-small` — Generación de música (300M)
- `openai/whisper-large-v3` — Transcripción multilingüe
- `suno/bark` — TTS expresivo + efectos
- `facebook/mms-tts-eng/por/spa` — TTS multilingüe

---

## 📝 Licencia

MIT — Infraestructura cedida al Duck Studio por Belentani

---

**Construido con:** Python 3.14, numpy, scipy, PyInstaller, Tkinter  
**EXE:** 25.3 MB standalone — sin dependencias externas  
**Fecha:** 2026-08-28
