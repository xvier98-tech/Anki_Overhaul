# -*- coding: utf-8 -*-
"""
Native Windows DirectInput / WinMM Joystick Driver using pure Python ctypes.
Enables instant, out-of-the-box support for Sony PlayStation controllers
(DualShock 4 / DualSense, Vendor: 054c), Nintendo Switch, 8BitDo in D-Input mode,
and generic Bluetooth/USB gamepads without requiring DS4Windows or external packages.
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
    BUTTON_LT,
    BUTTON_RT,
    BUTTON_BACK,
    BUTTON_START,
    BUTTON_L3,
    BUTTON_R3,
    BUTTON_DPAD_UP,
    BUTTON_DPAD_DOWN,
    BUTTON_DPAD_LEFT,
    BUTTON_DPAD_RIGHT,
    BUTTON_GUIDE,
    BUTTON_TOUCHPAD,
)

JOYERR_NOERROR = 0
JOY_RETURNALL = 0x000000FF


class JOYCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD),
        ("wPid", wintypes.WORD),
        ("szPname", wintypes.WCHAR * 32),
        ("wXmin", wintypes.UINT),
        ("wXmax", wintypes.UINT),
        ("wYmin", wintypes.UINT),
        ("wYmax", wintypes.UINT),
        ("wZmin", wintypes.UINT),
        ("wZmax", wintypes.UINT),
        ("wNumButtons", wintypes.UINT),
        ("wPeriodMin", wintypes.UINT),
        ("wPeriodMax", wintypes.UINT),
        ("wRmin", wintypes.UINT),
        ("wRmax", wintypes.UINT),
        ("wUmin", wintypes.UINT),
        ("wUmax", wintypes.UINT),
        ("wVmin", wintypes.UINT),
        ("wVmax", wintypes.UINT),
        ("wCaps", wintypes.UINT),
        ("wMaxAxes", wintypes.UINT),
        ("wNumAxes", wintypes.UINT),
        ("wMaxButtons", wintypes.UINT),
        ("szRegKey", wintypes.WCHAR * 32),
        ("szOEMVxD", wintypes.WCHAR * 260),
    ]


class JOYINFOEX(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("dwXpos", wintypes.DWORD),
        ("dwYpos", wintypes.DWORD),
        ("dwZpos", wintypes.DWORD),
        ("dwRpos", wintypes.DWORD),
        ("dwUpos", wintypes.DWORD),
        ("dwVpos", wintypes.DWORD),
        ("dwButtons", wintypes.DWORD),
        ("dwButtonNumber", wintypes.DWORD),
        ("dwPOV", wintypes.DWORD),
        ("dwReserved1", wintypes.DWORD),
        ("dwReserved2", wintypes.DWORD),
    ]


# Standard DirectInput / DualShock 4 button bit indices (1 << N)
DINPUT_DS4_MAP = {
    0: BUTTON_X,       # Square / X
    1: BUTTON_A,       # Cross / A
    2: BUTTON_B,       # Circle / B
    3: BUTTON_Y,       # Triangle / Y
    4: BUTTON_LB,      # L1
    5: BUTTON_RB,      # R1
    6: BUTTON_LT,      # L2
    7: BUTTON_RT,      # R2
    8: BUTTON_BACK,    # Share / Back
    9: BUTTON_START,   # Options / Start
    10: BUTTON_L3,     # L3
    11: BUTTON_R3,     # R3
    12: BUTTON_GUIDE,   # PS Button / Guide / Home (B16)
    13: BUTTON_TOUCHPAD,# Touchpad Click / Capture (B17)
}


class DirectInputDriver(BaseGamepadDriver):
    """
    DirectInput / WinMM driver for PlayStation and generic USB/Bluetooth controllers.
    """

    def __init__(self):
        self._winmm = None
        self._active_device_id: Optional[int] = None
        self._cached_name: str = ""
        self._init_driver()

    def _init_driver(self):
        if sys.platform != "win32":
            return
        try:
            self._winmm = ctypes.windll.winmm
        except Exception:
            self._winmm = None

    def is_available(self) -> bool:
        return self._winmm is not None

    def get_driver_name(self) -> str:
        return "Windows DirectInput / WinMM (PlayStation & Genérico)"

    def poll(self) -> GamepadState:
        if not self.is_available():
            return GamepadState(connected=False, device_name="WinMM não disponível")

        info = JOYINFOEX()
        info.dwSize = ctypes.sizeof(info)
        info.dwFlags = JOY_RETURNALL

        # Check previously active device first
        devices_to_check = [self._active_device_id] if self._active_device_id is not None else []
        devices_to_check.extend([i for i in range(16) if i != self._active_device_id])

        found_id = None
        for dev_id in devices_to_check:
            res = self._winmm.joyGetPosEx(dev_id, ctypes.byref(info))
            if res == JOYERR_NOERROR:
                found_id = dev_id
                break

        if found_id is None:
            self._active_device_id = None
            self._cached_name = ""
            return GamepadState(connected=False, device_name="Nenhum controle DirectInput conectado")

        # Update cached name if device changed
        if found_id != self._active_device_id or not self._cached_name:
            self._active_device_id = found_id
            caps = JOYCAPSW()
            if self._winmm.joyGetDevCapsW(found_id, ctypes.byref(caps), ctypes.sizeof(caps)) == 0:
                raw_name = caps.szPname.strip()
                # Friendly display name
                if "joystick" in raw_name.lower():
                    self._cached_name = f"🎮 Wireless Controller (PlayStation / DirectInput #{found_id + 1})"
                else:
                    self._cached_name = f"🎮 {raw_name} (#{found_id + 1})"
            else:
                self._cached_name = f"🎮 Wireless Controller (#{found_id + 1})"

        # 1. Parse Buttons
        active_buttons: Set[str] = set()
        dw_buttons = info.dwButtons

        for bit_idx, btn_name in DINPUT_DS4_MAP.items():
            if dw_buttons & (1 << bit_idx):
                active_buttons.add(btn_name)

        # Extended button bits (DirectInput 16 and 17)
        if dw_buttons & (1 << 16):
            active_buttons.add(BUTTON_GUIDE)
            active_buttons.add("B16")
        if dw_buttons & (1 << 17):
            active_buttons.add(BUTTON_TOUCHPAD)
            active_buttons.add("B17")

        # 2. Parse D-Pad (POV Hat)
        # dwPOV is in hundredths of a degree (0 = Up, 9000 = Right, 18000 = Down, 27000 = Left, 65535 = Released)
        pov = info.dwPOV
        if pov != 65535 and pov != 0xFFFF:
            if pov == 0:
                active_buttons.add(BUTTON_DPAD_UP)
            elif pov == 4500:
                active_buttons.add(BUTTON_DPAD_UP)
                active_buttons.add(BUTTON_DPAD_RIGHT)
            elif pov == 9000:
                active_buttons.add(BUTTON_DPAD_RIGHT)
            elif pov == 13500:
                active_buttons.add(BUTTON_DPAD_DOWN)
                active_buttons.add(BUTTON_DPAD_RIGHT)
            elif pov == 18000:
                active_buttons.add(BUTTON_DPAD_DOWN)
            elif pov == 22500:
                active_buttons.add(BUTTON_DPAD_DOWN)
                active_buttons.add(BUTTON_DPAD_LEFT)
            elif pov == 27000:
                active_buttons.add(BUTTON_DPAD_LEFT)
            elif pov == 31500:
                active_buttons.add(BUTTON_DPAD_UP)
                active_buttons.add(BUTTON_DPAD_LEFT)

        # 3. Parse Analog Sticks (Axes range 0 to 65535, center ~32767)
        # Left Stick
        lx = max(-1.0, min(1.0, (info.dwXpos - 32767) / 32767.0))
        # Invert Y so up is positive
        ly = max(-1.0, min(1.0, -(info.dwYpos - 32767) / 32767.0))

        # Right Stick (Z and R axes on DualShock 4)
        rx = max(-1.0, min(1.0, (info.dwZpos - 32767) / 32767.0))
        ry = max(-1.0, min(1.0, -(info.dwRpos - 32767) / 32767.0))

        # Triggers
        # DualShock 4 reports L2/R2 digitally on buttons 6/7, and analogically on U/V axes
        lt = 1.0 if (dw_buttons & (1 << 6)) else 0.0
        rt = 1.0 if (dw_buttons & (1 << 7)) else 0.0

        return GamepadState(
            connected=True,
            device_name=self._cached_name,
            buttons=active_buttons,
            left_trigger=lt,
            right_trigger=rt,
            thumb_lx=lx,
            thumb_ly=ly,
            thumb_rx=rx,
            thumb_ry=ry,
        )
