# -*- coding: utf-8 -*-
"""
Obsidian Addon Suite - Native Gamepad & Controller Integration Module.
"""

from .hooks import setup_gamepad_hooks, get_gamepad_manager, get_gamepad_dispatcher
from .config_dialog import GamepadConfigWidget

__all__ = [
    "setup_gamepad_hooks",
    "get_gamepad_manager",
    "get_gamepad_dispatcher",
    "GamepadConfigWidget",
]
