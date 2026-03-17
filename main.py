#!/usr/bin/env python3
"""
whisper-hotkey — Push-to-talk STT local
Maintiens Shift droit (⇧) → parle → relâche → texte collé au curseur
"""

import os
import sys
import wave
import tempfile
import threading
import subprocess
import numpy as np
import sounddevice as sd
import AppKit
from pynput import keyboard
from pynput.keyboard import Controller as KbController, Key

# Enregistre le process comme une vraie app GUI (sans icône Dock)
# → donne accès au window server + Accessibility
_app = AppKit.NSApplication.sharedApplication()
_app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

# ── Config ───────────────────────────────────────────────────────────────────
SAMPLE_RATE  = 16000
CHANNELS     = 1
MODEL        = os.path.expanduser(
    "~/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo"
    "/snapshots/beea265c324f07ba1e347f3c8a97aec454056a86"
)  # chemin local, aucun réseau
LANGUAGE     = "fr"
MIN_DURATION = 0.4   # secondes min pour déclencher la transcription
SOUND_START  = "/System/Library/Sounds/Tink.aiff"
SOUND_DONE   = "/System/Library/Sounds/Pop.aiff"

# ── State ─────────────────────────────────────────────────────────────────────
_pressed     = False
_recording   = False
_frames      = []
_lock        = threading.Lock()
_stream      = None
_model_ready = threading.Event()
_whisper_model = None


# ── Preload model en background au démarrage ──────────────────────────────────
def _preload_model():
    import mlx_whisper
    # warm-up sur audio silencieux
    f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(f.name, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
        wf.writeframes(np.zeros(8000, dtype=np.int16).tobytes())
    mlx_whisper.transcribe(f.name, path_or_hf_repo=MODEL, language=LANGUAGE, verbose=False)
    os.unlink(f.name)
    _model_ready.set()
    print("✅ Modèle prêt !\n", flush=True)


threading.Thread(target=_preload_model, daemon=True).start()


# ── Audio ─────────────────────────────────────────────────────────────────────
def play(sound):
    subprocess.Popen(["afplay", sound], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def audio_callback(indata, frames, time, status):
    if _recording:
        with _lock:
            _frames.append(indata.copy())


def start_recording():
    global _recording, _frames, _stream
    _frames = []
    _recording = True
    _stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        callback=audio_callback,
    )
    _stream.start()
    play(SOUND_START)
    print("🎙  Enregistrement...", flush=True)


def stop_and_transcribe():
    global _recording, _stream

    _recording = False
    if _stream:
        _stream.stop()
        _stream.close()
        _stream = None

    play(SOUND_DONE)

    with _lock:
        if not _frames:
            return
        audio = np.concatenate(_frames, axis=0)

    if len(audio) / SAMPLE_RATE < MIN_DURATION:
        print("⚠️  Trop court, ignoré.", flush=True)
        return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmpfile = f.name
    with wave.open(tmpfile, "wb") as wf:
        wf.setnchannels(CHANNELS); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
        wf.writeframes((audio * 32767).astype(np.int16).tobytes())

    print("⏳ Transcription...", flush=True)
    try:
        import mlx_whisper
        _model_ready.wait()
        result = mlx_whisper.transcribe(tmpfile, path_or_hf_repo=MODEL, language=LANGUAGE, verbose=False)
        text = result["text"].strip()
    except Exception as e:
        print(f"❌ Erreur : {e}", flush=True)
        return
    finally:
        os.unlink(tmpfile)

    if not text:
        print("⚠️  Rien détecté.", flush=True)
        return

    print(f"📝 {text}\n", flush=True)
    import time
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    time.sleep(0.4)  # laisse le clipboard se stabiliser
    result = subprocess.run(
        ["/opt/homebrew/bin/cliclick", "ku:shift,cmd,alt,ctrl", "kd:cmd", "t:v", "ku:cmd"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("✅ Collé", flush=True)
    else:
        print(f"❌ cliclick échoué : {result.stderr}", flush=True)


# ── Hotkey ────────────────────────────────────────────────────────────────────
def on_press(key):
    global _pressed
    if key == keyboard.Key.shift_r and not _pressed:
        _pressed = True
        threading.Thread(target=start_recording, daemon=True).start()


def on_release(key):
    global _pressed
    if key == keyboard.Key.shift_r and _pressed:
        _pressed = False
        threading.Thread(target=stop_and_transcribe, daemon=True).start()


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🎤 Whisper Hotkey — chargement du modèle en arrière-plan...")
    print("   Maintiens ⇧ droit pour parler  |  Ctrl+C pour quitter\n")
    try:
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
    except KeyboardInterrupt:
        print("\n👋 Bye")
        sys.exit(0)
