# -*- coding: utf-8 -*-
"""
Central Config Manager for Obsidian Addon Suite.
Provides unified access to theme, priority_sequencer, dashboard, pomodoro, ankiconnect, and multiple_choice configs.
"""

from typing import Dict, Any, Optional
import copy

try:
    from aqt import mw
except ImportError:
    mw = None

ADDON_PACKAGE_NAME = __name__.split(".")[0]

DEFAULT_CONFIG: Dict[str, Any] = {
    "general": {
        "language": "auto",
    },
    "theme": {
        "enabled": True,
        "preset": "oled_dark",
        "custom_overrides": {},
        "answer_buttons": {
            "button_scale": 1.15,
        },
    },
    "priority_sequencer": {
        "deck_priorities": {},
        "default_priority": 100,
        "random_tie_breaker": True,
        "randomize_cards_within_deck": False,
        "auto_reorder_on_profile_open": False,
        "auto_reorder_on_sync": False,
    },
    "dashboard": {
        "enabled": True,
        "show_on_overview": True,
        "show_on_deck_browser": True,
        "show_daily_goals": True,
        "show_deck_composition": True,
        "show_today_progress": True,
        "show_remaining": True,
        "show_done_today": True,
        "include_new_in_remaining_total": True,
        "hide_native_msg_box": False,
        "card_opacity": 95,
        "layout_columns": 3,
    },
    "pomodoro": {
        "enabled": True,
        "work_duration_minutes": 25,
        "short_break_minutes": 5,
        "long_break_minutes": 15,
        "long_break_interval": 4,
        "soft_break_mode": True,
        "inactivity_detection": True,
        "inactivity_timeout_seconds": 60,
        "auto_pause_outside_reviewer": True,
        "pause_on_focus_loss": True,
        "sound_notifications": True,
        "alarm_sound_preset": "digital_alarm",
        "custom_alarm_sound_path": "",
        "auto_hide_cursor_in_focus": True,
        "deck_profiles": {},
        "hotkeys": {
            "toggle_pause": "Alt+P",
            "skip_to_break": "Alt+S",
            "reset_cycle": "Alt+R",
        },
    },
    "ankiconnect": {
        "apiKey": None,
        "apiLogPath": None,
        "webBindAddress": "127.0.0.1",
        "webBindPort": 8765,
        "webCorsOrigin": None,
        "webCorsOriginList": ["http://localhost", "app://obsidian.md"],
    },
    "multiple_choice": {
        "maxQuestionsToShow": 5,
        "colorQuestionTable": False,
        "colorAnswerTable": True,
        "hideAnswerTable": False,
        "answerColoring": {
            "correctColor": "#27ae60",
            "incorrectColor": "#c0392b",
        },
    },
    "gamepad": {
        "enabled": True,
        "driver": "auto",
        "deadzone": 0.15,
        "scroll_sensitivity": 50.0,
        "trigger_threshold": 0.5,
        "continuous_scroll_stick": "right",
        "audio_feedback": True,
        "sound_preset": "click",
        "custom_sound_path": "",
        "trigger_on_release": True,
        "visual_feedback_intensity": "moderate",
        "button_scale": 1.15,
        "bindings": {
            "show_answer": ["A", "RT"],
            "return_screen": ["B"],
            "expand_subdecks": ["X"],
            "answer_ease_1": ["X"],
            "answer_ease_2": ["Y"],
            "answer_ease_3": ["B"],
            "answer_ease_4": ["A"],
            "undo": ["LB"],
            "replay_audio": ["L3"],
            "pause_audio": ["R3"],
            "toggle_flag": ["BACK"],
            "suspend_card": ["START"],
            "scroll_up": ["DPAD_UP", "LS_UP"],
            "scroll_down": ["DPAD_DOWN", "LS_DOWN"],
            "dpad_left": ["DPAD_LEFT", "LS_LEFT"],
            "dpad_right": ["DPAD_RIGHT", "LS_RIGHT"],
            "scroll_page_up": ["RS_UP"],
            "scroll_page_down": ["RS_DOWN"],
            "scroll_page_left": ["RS_LEFT"],
            "scroll_page_right": ["RS_RIGHT"],
            "nav_decks": [],
            "nav_add": [],
            "nav_browse": [],
            "nav_stats": [],
            "nav_sync": [],
            "topbar_toggle_focus": [],
            "pomo_toggle": [],
            "pomo_skip": [],
            "pomo_reset": [],
            "pomo_expand": [],
        },
    },
}

_in_memory_config: Optional[Dict[str, Any]] = None


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merges override dictionary into base dictionary."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def get_config() -> Dict[str, Any]:
    """Retrieves full unified addon configuration with defaults merged."""
    global _in_memory_config
    if mw and hasattr(mw, "addonManager") and mw.addonManager:
        try:
            stored = mw.addonManager.getConfig(ADDON_PACKAGE_NAME)
            if stored is None:
                stored = mw.addonManager.getConfig(__name__)
            if stored and isinstance(stored, dict):
                return _deep_merge(DEFAULT_CONFIG, stored)
        except Exception:
            pass

    if _in_memory_config is None:
        _in_memory_config = copy.deepcopy(DEFAULT_CONFIG)
    return _in_memory_config


def write_config(config: Dict[str, Any]) -> None:
    """Persists updated full configuration."""
    global _in_memory_config
    _in_memory_config = copy.deepcopy(config)

    if mw and hasattr(mw, "addonManager") and mw.addonManager:
        try:
            mw.addonManager.writeConfig(ADDON_PACKAGE_NAME, config)
        except Exception:
            try:
                mw.addonManager.writeConfig(__name__, config)
            except Exception as e:
                print(f"[Obsidian Addon] Error persisting config: {e}")


def get_module_config(module_key: str) -> Dict[str, Any]:
    """Retrieves config for a specific subsystem."""
    cfg = get_config()
    default_sub = DEFAULT_CONFIG.get(module_key, {})
    user_sub = cfg.get(module_key, {})
    if isinstance(user_sub, dict):
        return _deep_merge(default_sub, user_sub)
    return copy.deepcopy(default_sub)


def write_module_config(module_key: str, module_cfg: Dict[str, Any]) -> None:
    """Updates and saves config for a specific subsystem."""
    full_cfg = get_config()
    full_cfg[module_key] = module_cfg
    write_config(full_cfg)


class _DualKeyPriorityDict(dict):
    """Dictionary supporting lookups by either int or str deck ID transparently."""
    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            if isinstance(key, int):
                return super().__getitem__(str(key))
            elif isinstance(key, str) and (key.isdigit() or (key.startswith("-") and key[1:].isdigit())):
                return super().__getitem__(int(key))
            raise

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        if super().__contains__(key):
            return True
        if isinstance(key, int):
            return super().__contains__(str(key))
        if isinstance(key, str) and (key.isdigit() or (key.startswith("-") and key[1:].isdigit())):
            return super().__contains__(int(key))
        return False


def get_deck_priorities() -> Dict[Any, int]:
    """Helper to get deck priorities dictionary supporting both int and str keys."""
    prio_cfg = get_module_config("priority_sequencer")
    raw = prio_cfg.get("deck_priorities", {})
    result = _DualKeyPriorityDict()
    for k, v in raw.items():
        try:
            val = int(v)
            int_k = int(k)
            result[int_k] = val
        except (ValueError, TypeError):
            try:
                result[str(k)] = int(v)
            except (ValueError, TypeError):
                continue
    return result


def set_deck_priority(deck_id: int, priority: Optional[int]) -> None:
    """Sets or clears priority for a deck ID."""
    prio_cfg = get_module_config("priority_sequencer")
    priorities = prio_cfg.get("deck_priorities", {})
    str_key = str(deck_id)
    int_key = None
    try:
        int_key = int(deck_id)
    except (ValueError, TypeError):
        pass

    if priority is None:
        priorities.pop(str_key, None)
        if int_key is not None:
            priorities.pop(int_key, None)
    else:
        priorities[str_key] = int(priority)
        if int_key is not None:
            priorities.pop(int_key, None)

    prio_cfg["deck_priorities"] = priorities
    write_module_config("priority_sequencer", prio_cfg)

