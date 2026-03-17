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
import time
import numpy as np
import sounddevice as sd
import rumps
import AppKit
from pynput import keyboard
from pynput.keyboard import Controller as KbController, Key

# Enregistre le process comme une vraie app GUI (sans icône Dock)
_app_ns = AppKit.NSApplication.sharedApplication()
_app_ns.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

# ── Config ───────────────────────────────────────────────────────────────────
SAMPLE_RATE   = 16000
CHANNELS      = 1
MODEL         = os.path.expanduser(
    "~/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo"
    "/snapshots/beea265c324f07ba1e347f3c8a97aec454056a86"
)
LANGUAGE      = "fr"
MIN_DURATION  = 0.4
MAX_DURATION  = 60.0   # stop auto après 60s
SOUND_START   = "/System/Library/Sounds/Tink.aiff"
SOUND_DONE    = "/System/Library/Sounds/Pop.aiff"

# ── State ─────────────────────────────────────────────────────────────────────
_pressed      = False
_recording    = False
_frames       = []
_lock         = threading.Lock()
_stream       = None
_model_ready  = threading.Event()
_app_ref      = None   # référence à l'app rumps


# ── Preload model ─────────────────────────────────────────────────────────────
def _preload_model():
    import mlx_whisper
    f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(f.name, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
        wf.writeframes(np.zeros(8000, dtype=np.int16).tobytes())
    mlx_whisper.transcribe(f.name, path_or_hf_repo=MODEL, language=LANGUAGE, verbose=False)
    os.unlink(f.name)
    _model_ready.set()
    if _app_ref:
        _app_ref.title = "🎤"
    print("✅ Modèle prêt !\n", flush=True)

threading.Thread(target=_preload_model, daemon=True).start()


# ── Audio ─────────────────────────────────────────────────────────────────────
def play(sound):
    subprocess.Popen(["afplay", sound], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def audio_callback(indata, frames, time_info, status):
    if _recording:
        with _lock:
            _frames.append(indata.copy())


def start_recording():
    global _recording, _frames, _stream
    _frames = []
    _recording = True
    _stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=CHANNELS,
        dtype="float32", callback=audio_callback,
    )
    _stream.start()
    play(SOUND_START)
    if _app_ref:
        _app_ref.title = "🔴"
    print("🎙  Enregistrement...", flush=True)

    # Timeout de sécurité
    def _timeout():
        time.sleep(MAX_DURATION)
        if _recording:
            print("⚠️  Timeout, arrêt auto.", flush=True)
            stop_and_transcribe()
    threading.Thread(target=_timeout, daemon=True).start()


def stop_and_transcribe():
    global _recording, _stream, _pressed

    if not _recording:
        return
    _recording = False
    _pressed = False

    if _stream:
        _stream.stop()
        _stream.close()
        _stream = None

    play(SOUND_DONE)
    if _app_ref:
        _app_ref.title = "⏳"

    with _lock:
        if not _frames:
            if _app_ref:
                _app_ref.title = "🎤"
            return
        audio = np.concatenate(_frames, axis=0)

    if len(audio) / SAMPLE_RATE < MIN_DURATION:
        print("⚠️  Trop court, ignoré.", flush=True)
        if _app_ref:
            _app_ref.title = "🎤"
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
        result = mlx_whisper.transcribe(
            tmpfile, path_or_hf_repo=MODEL, language=LANGUAGE, verbose=False)
        text = result["text"].strip()
    except Exception as e:
        print(f"❌ Erreur transcription : {e}", flush=True)
        if _app_ref:
            _app_ref.title = "🎤"
        return
    finally:
        os.unlink(tmpfile)

    if not text:
        print("⚠️  Rien détecté.", flush=True)
        if _app_ref:
            _app_ref.title = "🎤"
        return

    print(f"📝 {text}\n", flush=True)
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    time.sleep(0.3)
    helper = os.path.join(os.path.dirname(__file__), "paste-helper")
    result = subprocess.run([helper], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Collé", flush=True)
    else:
        print(f"❌ paste-helper : {result.stderr}", flush=True)

    if _app_ref:
        _app_ref.title = "🎤"


# ── Hotkey listener (avec auto-restart) ───────────────────────────────────────
def _start_listener():
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

    while True:
        try:
            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                listener.join()
        except Exception as e:
            print(f"⚠️  Listener planté ({e}), redémarrage...", flush=True)
            time.sleep(1)

threading.Thread(target=_start_listener, daemon=True).start()


# ── Menu bar app ──────────────────────────────────────────────────────────────
class WhisperApp(rumps.App):
    def __init__(self):
        super().__init__("⏳", quit_button="Quitter")

    @rumps.clicked("Redémarrer le listener")
    def restart(self, _):
        global _pressed, _recording
        _pressed = False
        _recording = False
        print("🔄 Restart manuel", flush=True)

if __name__ == "__main__":
    print("🎤 Whisper Hotkey — chargement du modèle...", flush=True)
    app = WhisperApp()
    _app_ref = app
    app.run()
