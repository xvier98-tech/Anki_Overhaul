# -*- coding: utf-8 -*-
"""
Audio playback and sound notification system for Pomodoro transitions.
Supports preset synthesized sounds (bell, school bell, analog clock, digital watch)
and custom user MP3/WAV files with cross-platform Anki audio integration.
"""

import os
import sys
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


def get_sound_asset_path(sound_key: str) -> Optional[str]:
    """Returns absolute path to a preset sound file."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    assets_dir = os.path.join(base_dir, "assets", "sounds")

    sound_map = {
        "bell": "bell.wav",
        "school_bell": "school_bell.wav",
        "analog_alarm": "analog_alarm.wav",
        "digital_alarm": "digital_alarm.wav",
    }
    filename = sound_map.get(sound_key)
    if filename:
        path = os.path.join(assets_dir, filename)
        if os.path.exists(path):
            return path
    return None


def play_pomodoro_sound(
    sound_key: Optional[str] = None,
    custom_file_path: Optional[str] = None,
    event_type: str = "work_end",
    volume: Optional[int] = None,
):
    """
    Plays the configured Pomodoro notification sound or a specific preset/custom file.
    event_type can be:
    - 'work_end': Focus block ended
    - 'break_end': Rest break ended
    - 'focus_loss': Anki window lost focus during focus mode (distraction alert)
    - 'inactivity': User inactivity timeout during focus mode
    """
    config = get_module_config("pomodoro")

    if volume is None:
        if event_type == "break_end":
            volume = int(config.get("break_sound_volume", 100))
        elif event_type in ("focus_loss", "inactivity"):
            volume = int(config.get("alarm_sound_volume", 100))
        else:
            volume = int(config.get("sound_volume", 100))

    if volume <= 0:
        return

    if sound_key is None:
        if not config.get("sound_notifications", True):
            return
        if event_type == "break_end":
            sound_key = config.get("break_sound_preset", "school_bell")
            custom_file_path = config.get("custom_break_sound_path", "")
        elif event_type in ("focus_loss", "inactivity"):
            sound_key = config.get("alarm_sound_preset", config.get("focus_loss_sound_preset", "digital_alarm"))
            custom_file_path = config.get("custom_alarm_sound_path", "")
        else:
            sound_key = config.get("sound_preset", "bell")
            custom_file_path = config.get("custom_sound_path", "")

    # 1. Custom MP3/WAV file
    if sound_key == "custom" and custom_file_path and os.path.exists(custom_file_path):
        _play_file(custom_file_path, volume=volume)
        return

    # 2. Preset Sound Assets
    asset_path = get_sound_asset_path(sound_key)
    if asset_path and os.path.exists(asset_path):
        _play_file(asset_path, volume=volume)
        return

    # 3. Fallback: System Beep
    try:
        if QApplication:
            QApplication.beep()
    except Exception:
        pass


def _play_file(filepath: str, volume: int = 100):
    """Plays an audio file using winsound with PCM volume attenuation or Qt audio."""
    if play_sound_with_volume:
        try:
            play_sound_with_volume(filepath, volume=volume)
            return
        except Exception:
            pass

    # 1. On Windows, if WAV, winsound is 100% reliable, zero-latency, and plays even in background
    if sys.platform == "win32" and filepath.lower().endswith(".wav"):
        try:
            import winsound
            winsound.PlaySound(filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        except Exception:
            pass

    # 2. Prefer Anki's native audio engine if available
    try:
        if aqt and hasattr(aqt, "sound") and hasattr(aqt.sound, "play"):
            aqt.sound.play(filepath)
            return
    except Exception:
        pass

    # 3. Windows fallback
    if sys.platform == "win32":
        try:
            import winsound
            winsound.PlaySound(filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        except Exception:
            pass

    # 4. Generic Qt Fallback
    try:
        if QApplication:
            QApplication.beep()
    except Exception:
        pass


def play_chime_sound(sound_type: str = "work_end"):
    """Legacy alias used across timer engine."""
    play_pomodoro_sound(event_type=sound_type)
