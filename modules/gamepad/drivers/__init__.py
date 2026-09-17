# -*- coding: utf-8 -*-
"""
Gamepad Drivers package.
Provides factory function get_gamepad_driver().
"""

from typing import Optional
from .base import BaseGamepadDriver, GamepadState, ALL_STANDARD_BUTTONS
from .xinput_driver import XInputDriver
from .directinput_driver import DirectInputDriver
from .composite_driver import CompositeGamepadDriver
from .pygame_driver import PygameDriver


def get_gamepad_driver(preferred: str = "auto") -> BaseGamepadDriver:
    """
    Returns the best available gamepad driver.
    - 'auto': Uses CompositeGamepadDriver (detects both Xbox/XInput and PlayStation/DirectInput).
    - 'xinput': Forces XInputDriver.
    - 'directinput': Forces DirectInputDriver (WinMM).
    - 'pygame': Uses PygameDriver if available.
    """
    if preferred == "pygame":
        pg_drv = PygameDriver()
        if pg_drv.is_available():
            return pg_drv

    if preferred == "xinput":
        x_drv = XInputDriver()
        if x_drv.is_available():
            return x_drv

    if preferred == "directinput":
        d_drv = DirectInputDriver()
        if d_drv.is_available():
            return d_drv

    # Default 'auto': Composite driver covering all controllers
    comp_drv = CompositeGamepadDriver()
    if comp_drv.is_available():
        return comp_drv

    # Fallback to Pygame if available
    pg_drv = PygameDriver()
    if pg_drv.is_available():
        return pg_drv

    return comp_drv
