# -*- coding: utf-8 -*-
"""
Abstract base class and normalized data structures for Gamepad Drivers.
Provides unified button naming and axis normalization across all backends.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Set, Tuple, Optional


# Standard normalized button identifiers
BUTTON_A = "A"          # Xbox A / PS Cross / Switch B
BUTTON_B = "B"          # Xbox B / PS Circle / Switch A
BUTTON_X = "X"          # Xbox X / PS Square / Switch Y
BUTTON_Y = "Y"          # Xbox Y / PS Triangle / Switch X

BUTTON_LB = "LB"        # Left Bumper / L1 / L
BUTTON_RB = "RB"        # Right Bumper / R1 / R
BUTTON_LT = "LT"        # Left Trigger (when pressed past threshold)
BUTTON_RT = "RT"        # Right Trigger (when pressed past threshold)

BUTTON_BACK = "BACK"    # Back / Select / Share / Minus
BUTTON_START = "START"  # Start / Options / Menu / Plus
BUTTON_L3 = "L3"        # Left Stick Click (LS)
BUTTON_R3 = "R3"        # Right Stick Click (RS)

BUTTON_DPAD_UP = "DPAD_UP"
BUTTON_DPAD_DOWN = "DPAD_DOWN"
BUTTON_DPAD_LEFT = "DPAD_LEFT"
BUTTON_DPAD_RIGHT = "DPAD_RIGHT"

# Extra controller buttons (B16, B17)
BUTTON_GUIDE = "GUIDE"        # B16: PS Button / Xbox Guide / Home
BUTTON_TOUCHPAD = "TOUCHPAD"  # B17: Touchpad Click / Capture / Mic

# Discrete Analog Stick Gestures (Left & Right Stick directions)
STICK_LS_UP = "LS_UP"
STICK_LS_DOWN = "LS_DOWN"
STICK_LS_LEFT = "LS_LEFT"
STICK_LS_RIGHT = "LS_RIGHT"

STICK_RS_UP = "RS_UP"
STICK_RS_DOWN = "RS_DOWN"
STICK_RS_LEFT = "RS_LEFT"
STICK_RS_RIGHT = "RS_RIGHT"

ALL_STANDARD_BUTTONS = [
    BUTTON_A, BUTTON_B, BUTTON_X, BUTTON_Y,
    BUTTON_LB, BUTTON_RB, BUTTON_LT, BUTTON_RT,
    BUTTON_BACK, BUTTON_START, BUTTON_L3, BUTTON_R3,
    BUTTON_DPAD_UP, BUTTON_DPAD_DOWN, BUTTON_DPAD_LEFT, BUTTON_DPAD_RIGHT,
    BUTTON_GUIDE, BUTTON_TOUCHPAD,
    STICK_LS_UP, STICK_LS_DOWN, STICK_LS_LEFT, STICK_LS_RIGHT,
    STICK_RS_UP, STICK_RS_DOWN, STICK_RS_LEFT, STICK_RS_RIGHT,
]


@dataclass
class GamepadState:
    """Normalized snapshot of gamepad state at an instant in time."""
    connected: bool = False
    device_name: str = "Nenhum controle detectado"
    buttons: Set[str] = field(default_factory=set)
    left_trigger: float = 0.0     # 0.0 to 1.0
    right_trigger: float = 0.0    # 0.0 to 1.0
    thumb_lx: float = 0.0         # -1.0 (left) to 1.0 (right)
    thumb_ly: float = 0.0         # -1.0 (down) to 1.0 (up)
    thumb_rx: float = 0.0         # -1.0 (left) to 1.0 (right)
    thumb_ry: float = 0.0         # -1.0 (down) to 1.0 (up)


class BaseGamepadDriver(ABC):
    """Abstract driver interface for reading physical gamepad inputs."""

    @abstractmethod
    def poll(self) -> GamepadState:
        """Polls current hardware input state and returns a normalized GamepadState."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Checks if the driver backend is functional on the current system."""
        pass

    @abstractmethod
    def get_driver_name(self) -> str:
        """Returns human-readable name of this driver."""
        pass
