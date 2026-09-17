# -*- coding: utf-8 -*-
"""
Audio Feedback Engine for Gamepad Button Presses and Navigation.
Provides synthesized tactile sounds (Click, Pop, Chime, Beep) and custom MP3/WAV playback.
Plays asynchronously with zero UI latency and without interrupting Anki's card review audio.
"""

import os
import sys
import wave
import struct
import math
from typing import Optional

try:
    from PyQt6.QtWidgets import QApplication
    from aqt import mw
    import aqt.sound
except ImportError:
    QApplication = None
    mw = None
    aqt = None

try:
    from ...utils.config_manager import get_module_config
    from ...utils.audio_player import play_sound_with_volume
except (ImportError, ValueError):
    try:
        from utils.config_manager import get_module_config
        from utils.audio_player import play_sound_with_volume
    except (ImportError, ValueError):
        from utils.config_manager import get_module_config
        play_sound_with_volume = None


def get_gamepad_assets_dir() -> str:
    """Returns absolute path to the addon's assets/sounds directory."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, "assets", "sounds")


def ensure_gamepad_sound_assets(target_dir: Optional[str] = None):
    """Generates default tactile sound assets if they do not exist."""
    if not target_dir:
        target_dir = get_gamepad_assets_dir()
    os.makedirs(target_dir, exist_ok=True)
    sr = 44100

    def write_wav(filename: str, samples: list):
        p = os.path.join(target_dir, filename)
        if os.path.exists(p):
            return
        with wave.open(p, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            raw = bytearray()
            for s in samples:
                val = max(-32767, min(32767, int(s * 32767)))
                raw.extend(struct.pack('<h', val))
            wf.writeframes(raw)

    # 1. Click (40ms tactile mechanical tap)
    samples = []
    for i in range(int(0.04 * sr)):
        t = i / sr
        env = math.exp(-120.0 * t)
        s = (0.7 * math.sin(2 * math.pi * 1800 * t) + 0.3 * math.sin(2 * math.pi * 800 * t)) * env
        samples.append(s)
    write_wav("gamepad_click.wav", samples)

    # 2. Pop (60ms soft bubble pop)
    samples = []
    for i in range(int(0.06 * sr)):
        t = i / sr
        env = math.exp(-65.0 * t)
        f = 850.0 - (500.0 * (t / 0.06))
        s = math.sin(2 * math.pi * f * t) * env
        samples.append(s)
    write_wav("gamepad_pop.wav", samples)

    # 3. Chime (120ms gentle confirmation chime)
    samples = []
    for i in range(int(0.12 * sr)):
        t = i / sr
        env = math.exp(-28.0 * t)
        s = (0.6 * math.sin(2 * math.pi * 880 * t) + 0.4 * math.sin(2 * math.pi * 1320 * t)) * env
        samples.append(s)
    write_wav("gamepad_chime.wav", samples)

    # 4. Beep (40ms subtle electronic pip)
    samples = []
    for i in range(int(0.04 * sr)):
        t = i / sr
        env = math.exp(-80.0 * t)
        s = math.sin(2 * math.pi * 1400 * t) * env
        samples.append(s)
    write_wav("gamepad_beep.wav", samples)


def get_gamepad_sound_asset_path(sound_key: str) -> Optional[str]:
    """Returns absolute path to a preset sound file."""
    assets_dir = get_gamepad_assets_dir()
    sound_map = {
        "click": "gamepad_click.wav",
        "pop": "gamepad_pop.wav",
        "chime": "gamepad_chime.wav",
        "beep": "gamepad_beep.wav",
        "bell": "bell.wav",
    }
    filename = sound_map.get(sound_key)
    if filename:
        path = os.path.join(assets_dir, filename)
        if os.path.exists(path):
            return path
        # Try generating if missing
        ensure_gamepad_sound_assets(assets_dir)
        if os.path.exists(path):
            return path
    return None


def play_gamepad_sound(
    sound_key: Optional[str] = None,
    custom_file_path: Optional[str] = None,
    volume: Optional[int] = None,
):
    """
    Plays the configured gamepad feedback sound asynchronously.
    Can be called with explicit preset key and volume for testing in configuration dialogs.
    """
    config = get_module_config("gamepad")
    if volume is None:
        volume = int(config.get("sound_volume", 80))

    if volume <= 0:
        return

    if sound_key is None:
        if not config.get("audio_feedback", True):
            return
        sound_key = config.get("sound_preset", "click")
        custom_file_path = config.get("custom_sound_path", "")

    # 1. Custom Audio File
    if sound_key == "custom" and custom_file_path and os.path.exists(custom_file_path):
        _play_file(custom_file_path, volume=volume)
        return

    # 2. Preset Sound Assets
    asset_path = get_gamepad_sound_asset_path(sound_key)
    if asset_path and os.path.exists(asset_path):
        _play_file(asset_path, volume=volume)
        return

    # 3. Fallback: System Beep
    try:
        if QApplication:
            QApplication.beep()
    except Exception:
        pass


def _play_file(filepath: str, volume: int = 80):
    """Plays an audio file asynchronously with ultra-low latency and volume control."""
    if play_sound_with_volume:
        try:
            play_sound_with_volume(filepath, volume=volume)
            return
        except Exception:
            pass

    # Fallback: Windows winsound
    if sys.platform == "win32":
        try:
            import winsound
            winsound.PlaySound(filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        except Exception:
            pass

    # Secondary: Anki audio player
    try:
        if aqt and hasattr(aqt, "sound") and hasattr(aqt.sound, "play"):
            aqt.sound.play(filepath)
            return
    except Exception:
        pass

    # Tertiary: Beep fallback
    try:
        if QApplication:
            QApplication.beep()
    except Exception:
        pass
