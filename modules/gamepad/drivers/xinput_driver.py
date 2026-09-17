# -*- coding: utf-8 -*-
"""
Native Windows XInput Driver using pure Python ctypes.
Requires zero third-party dependencies (works in bundled Anki Python out-of-the-box).
Supports Xbox, 8BitDo (X-input mode), PlayStation (DS4/DualSense via XInput bridge) and PC gamepads.
"""

import sys
import ctypes
from ctypes import wintypes
from typing import Set, Optional

from .base import (
    BaseGamepadDriver,
    GamepadState,
    BUTTON_A,
    BUTTON_B,
    BUTTON_X,
    BUTTON_Y,
    BUTTON_LB,
    BUTTON_RB,
    BUTTON_BACK,
    BUTTON_START,
    BUTTON_L3,
    BUTTON_R3,
    BUTTON_DPAD_UP,
    BUTTON_DPAD_DOWN,
    BUTTON_DPAD_LEFT,
    BUTTON_DPAD_RIGHT,
    BUTTON_GUIDE,
)

# XInput button bitmasks
XINPUT_GAMEPAD_DPAD_UP = 0x0001
XINPUT_GAMEPAD_DPAD_DOWN = 0x0002
XINPUT_GAMEPAD_DPAD_LEFT = 0x0004
XINPUT_GAMEPAD_DPAD_RIGHT = 0x0008
XINPUT_GAMEPAD_START = 0x0010
XINPUT_GAMEPAD_BACK = 0x0020
XINPUT_GAMEPAD_LEFT_THUMB = 0x0040
XINPUT_GAMEPAD_RIGHT_THUMB = 0x0080
XINPUT_GAMEPAD_LEFT_SHOULDER = 0x0100
XINPUT_GAMEPAD_RIGHT_SHOULDER = 0x0200
XINPUT_GAMEPAD_GUIDE = 0x0400  # Xbox / PS Guide Button (B16)
XINPUT_GAMEPAD_A = 0x1000
XINPUT_GAMEPAD_B = 0x2000
XINPUT_GAMEPAD_X = 0x4000
XINPUT_GAMEPAD_Y = 0x8000

ERROR_SUCCESS = 0
ERROR_DEVICE_NOT_CONNECTED = 1167

BUTTON_MAP = [
    (XINPUT_GAMEPAD_A, BUTTON_A),
    (XINPUT_GAMEPAD_B, BUTTON_B),
    (XINPUT_GAMEPAD_X, BUTTON_X),
    (XINPUT_GAMEPAD_Y, BUTTON_Y),
    (XINPUT_GAMEPAD_LEFT_SHOULDER, BUTTON_LB),
    (XINPUT_GAMEPAD_RIGHT_SHOULDER, BUTTON_RB),
    (XINPUT_GAMEPAD_START, BUTTON_START),
    (XINPUT_GAMEPAD_BACK, BUTTON_BACK),
    (XINPUT_GAMEPAD_LEFT_THUMB, BUTTON_L3),
    (XINPUT_GAMEPAD_RIGHT_THUMB, BUTTON_R3),
    (XINPUT_GAMEPAD_DPAD_UP, BUTTON_DPAD_UP),
    (XINPUT_GAMEPAD_DPAD_DOWN, BUTTON_DPAD_DOWN),
    (XINPUT_GAMEPAD_DPAD_LEFT, BUTTON_DPAD_LEFT),
    (XINPUT_GAMEPAD_DPAD_RIGHT, BUTTON_DPAD_RIGHT),
    (XINPUT_GAMEPAD_GUIDE, BUTTON_GUIDE),
]


class XINPUT_GAMEPAD(ctypes.Structure):
    _fields_ = [
        ("wButtons", wintypes.WORD),
        ("bLeftTrigger", wintypes.BYTE),
        ("bRightTrigger", wintypes.BYTE),
        ("sThumbLX", wintypes.SHORT),
        ("sThumbLY", wintypes.SHORT),
        ("sThumbRX", wintypes.SHORT),
        ("sThumbRY", wintypes.SHORT),
    ]


class XINPUT_STATE(ctypes.Structure):
    _fields_ = [
        ("dwPacketNumber", wintypes.DWORD),
        ("Gamepad", XINPUT_GAMEPAD),
    ]


class XInputDriver(BaseGamepadDriver):
    """Windows native XInput driver accessed via ctypes."""

    def __init__(self):
        self._dll = None
        self._active_slot: Optional[int] = None
        self._init_dll()

    def _init_dll(self):
        if sys.platform != "win32":
            return

        # Attempt loading XInput in order of newest to oldest API
        for dll_name in ("xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"):
            try:
                self._dll = ctypes.WinDLL(dll_name)
                # Configure signature for XInputGetState(DWORD dwUserIndex, XINPUT_STATE* pState)
                self._dll.XInputGetState.argtypes = [wintypes.DWORD, ctypes.POINTER(XINPUT_STATE)]
                self._dll.XInputGetState.restype = wintypes.DWORD
                break
            except Exception:
                self._dll = None

    def is_available(self) -> bool:
        return self._dll is not None

    def get_driver_name(self) -> str:
        return "Windows XInput (Nativo / Zero Dependências)"

    def poll(self) -> GamepadState:
        if not self.is_available():
            return GamepadState(connected=False, device_name="XInput não disponível no sistema")

        state = XINPUT_STATE()

        # If we previously had an active slot, try polling it first
        slots_to_check = [self._active_slot] if self._active_slot is not None else []
        slots_to_check.extend([i for i in range(4) if i != self._active_slot])

        found_slot = None
        for slot in slots_to_check:
            res = self._dll.XInputGetState(slot, ctypes.byref(state))
            if res == ERROR_SUCCESS:
                found_slot = slot
                break

        if found_slot is None:
            self._active_slot = None
            return GamepadState(connected=False, device_name="Nenhum controle conectado")

        self._active_slot = found_slot
        gp = state.Gamepad

        # Extract active buttons
        active_buttons: Set[str] = set()
        w_buttons = gp.wButtons
        for mask, btn_name in BUTTON_MAP:
            if w_buttons & mask:
                active_buttons.add(btn_name)

        # Normalize Triggers (0.0 to 1.0)
        lt = gp.bLeftTrigger / 255.0
        rt = gp.bRightTrigger / 255.0

        # Normalize Thumbsticks (-1.0 to 1.0)
        # Invert LY and RY if needed, standard XInput: +Y is UP, +X is RIGHT
        lx = max(-1.0, min(1.0, gp.sThumbLX / 32767.0))
        ly = max(-1.0, min(1.0, gp.sThumbLY / 32767.0))
        rx = max(-1.0, min(1.0, gp.sThumbRX / 32767.0))
        ry = max(-1.0, min(1.0, gp.sThumbRY / 32767.0))

        return GamepadState(
            connected=True,
            device_name=f"🎮 XInput Gamepad (Slot {found_slot + 1})",
            buttons=active_buttons,
            left_trigger=lt,
            right_trigger=rt,
            thumb_lx=lx,
            thumb_ly=ly,
            thumb_rx=rx,
            thumb_ry=ry,
        )
