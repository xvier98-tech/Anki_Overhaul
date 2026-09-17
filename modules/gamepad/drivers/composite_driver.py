# -*- coding: utf-8 -*-
"""
Composite Universal Gamepad Driver for Windows.
Combines XInput (Xbox, modern PC) and DirectInput/WinMM (PlayStation DualShock 4,
DualSense, 8BitDo, Switch Pro, and generic controllers) into a seamless, auto-detecting driver.
"""

from .base import BaseGamepadDriver, GamepadState
from .xinput_driver import XInputDriver
from .directinput_driver import DirectInputDriver


class CompositeGamepadDriver(BaseGamepadDriver):
    """
    Seamlessly polls XInput and DirectInput backends.
    If an XInput controller is active, uses it.
    If a DirectInput (e.g. PlayStation DualShock 4/DualSense) controller is active, uses it.
    """

    def __init__(self):
        self.xinput = XInputDriver()
        self.dinput = DirectInputDriver()

    def is_available(self) -> bool:
        return self.xinput.is_available() or self.dinput.is_available()

    def get_driver_name(self) -> str:
        return "Windows Universal (XInput + PlayStation/DirectInput)"

    def poll(self) -> GamepadState:
        # 1. Check XInput first (Xbox, PC)
        if self.xinput.is_available():
            x_state = self.xinput.poll()
            if x_state.connected:
                return x_state

        # 2. Check DirectInput / WinMM (PlayStation DualShock 4 / DualSense, Bluetooth, USB)
        if self.dinput.is_available():
            d_state = self.dinput.poll()
            if d_state.connected:
                return d_state

        return GamepadState(connected=False, device_name="Nenhum controle detectado")
