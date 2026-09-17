# -*- coding: utf-8 -*-
"""
Unit tests for Gamepad / Controller Integration Module.
Tests radial deadzone math, trigger thresholding, action dispatching, and driver abstraction.
"""

import unittest
import math
from modules.gamepad.input_manager import apply_radial_deadzone, GamepadInputManager
from modules.gamepad.drivers.base import (
    GamepadState,
    BUTTON_A,
    BUTTON_B,
    BUTTON_X,
    BUTTON_Y,
    BUTTON_LB,
    BUTTON_RB,
    BUTTON_LT,
    BUTTON_RT,
    BUTTON_DPAD_UP,
    BUTTON_DPAD_DOWN,
)
from modules.gamepad.drivers import get_gamepad_driver, XInputDriver, PygameDriver
from modules.gamepad.actions import (
    GamepadActionDispatcher,
    get_default_bindings,
    ACTION_DEFINITIONS,
)


class DummyMockDriver:
    """Mock driver for deterministic unit testing."""

    def __init__(self):
        self.state = GamepadState(
            connected=True,
            device_name="Mock Gamepad",
            buttons=set(),
            left_trigger=0.0,
            right_trigger=0.0,
            thumb_lx=0.0,
            thumb_ly=0.0,
            thumb_rx=0.0,
            thumb_ry=0.0,
        )

    def is_available(self):
        return True

    def get_driver_name(self):
        return "Mock Driver"

    def poll(self):
        return self.state


class TestGamepadModule(unittest.TestCase):

    def test_radial_deadzone_filtering(self):
        deadzone = 0.15

        # 1. Inputs below deadzone should be zeroed
        x, y = apply_radial_deadzone(0.08, 0.05, deadzone)
        self.assertEqual(x, 0.0)
        self.assertEqual(y, 0.0)

        # 2. Origin should be zero
        x, y = apply_radial_deadzone(0.0, 0.0, deadzone)
        self.assertEqual(x, 0.0)
        self.assertEqual(y, 0.0)

        # 3. Exactly at deadzone boundary should be zero
        x, y = apply_radial_deadzone(0.15, 0.0, deadzone)
        self.assertEqual(x, 0.0)
        self.assertEqual(y, 0.0)

        # 4. Inputs above deadzone should be smoothly rescaled
        x, y = apply_radial_deadzone(1.0, 0.0, deadzone)
        self.assertAlmostEqual(x, 1.0, places=5)
        self.assertEqual(y, 0.0)

        # 5. Diagonal deflection
        diag_mag = math.hypot(0.6, 0.6)
        expected_rescaled = (diag_mag - deadzone) / (1.0 - deadzone)
        x, y = apply_radial_deadzone(0.6, 0.6, deadzone)
        actual_mag = math.hypot(x, y)
        self.assertAlmostEqual(actual_mag, expected_rescaled, places=5)

    def test_trigger_threshold_mode(self):
        manager = GamepadInputManager()
        mock = DummyMockDriver()
        manager.driver = mock
        manager.trigger_threshold = 0.5

        # Triggers at 0.3 (below threshold) -> no LT/RT
        mock.state.left_trigger = 0.3
        mock.state.right_trigger = 0.4
        manager.poll_cycle()
        self.assertNotIn(BUTTON_LT, manager._previous_buttons)
        self.assertNotIn(BUTTON_RT, manager._previous_buttons)

        # Triggers at 0.7 (above threshold) -> LT/RT activated
        mock.state.left_trigger = 0.7
        mock.state.right_trigger = 0.8
        manager.poll_cycle()
        self.assertIn(BUTTON_LT, manager._previous_buttons)
        self.assertIn(BUTTON_RT, manager._previous_buttons)

    def test_button_edge_detection(self):
        manager = GamepadInputManager()
        mock = DummyMockDriver()
        manager.driver = mock

        captured_presses = []
        captured_releases = []
        manager.button_down.connect(captured_presses.append)
        manager.button_up.connect(captured_releases.append)

        # Press A
        mock.state.buttons = {BUTTON_A}
        manager.poll_cycle()
        self.assertEqual(captured_presses, [BUTTON_A])
        self.assertEqual(captured_releases, [])

        # Hold A
        manager.poll_cycle()
        self.assertEqual(captured_presses, [BUTTON_A])  # no duplicate press

        # Release A and press B
        mock.state.buttons = {BUTTON_B}
        manager.poll_cycle()
        self.assertIn(BUTTON_B, captured_presses)
        self.assertIn(BUTTON_A, captured_releases)

    def test_listening_mode_capture(self):
        manager = GamepadInputManager()
        mock = DummyMockDriver()
        manager.driver = mock

        captured_listening = []
        manager.listening_captured.connect(captured_listening.append)
        manager.listening_mode = True

        # Press X
        mock.state.buttons = {BUTTON_X}
        manager.poll_cycle()

        self.assertEqual(captured_listening, [BUTTON_X])
        self.assertFalse(manager.listening_mode)  # Automatically disabled after capture

    def test_action_dispatcher_mappings(self):
        defaults = get_default_bindings()
        dispatcher = GamepadActionDispatcher(defaults)

        # In default layout, A is mapped to show_answer and answer_ease_4
        self.assertIn("A", defaults["show_answer"])
        self.assertIn("A", defaults["answer_ease_4"])
        self.assertIn("B", defaults["return_screen"])
        self.assertIn("X", defaults["expand_subdecks"])
        self.assertIn("X", defaults["answer_ease_1"])
        self.assertIn("B", defaults["answer_ease_3"])
        self.assertIn("LB", defaults["undo"])

        # Custom bindings
        custom = {
            "show_answer": ["RB"],
            "answer_ease_1": ["A"],
            "return_screen": ["BACK"],
            "expand_subdecks": ["Y"],
        }
        dispatcher.set_bindings(custom)
        self.assertTrue(dispatcher.handle_button_press("RB"))
        self.assertTrue(dispatcher.handle_button_press("A"))
        self.assertTrue(dispatcher.handle_button_press("BACK"))
        self.assertTrue(dispatcher.handle_button_press("Y"))
        self.assertFalse(dispatcher.handle_button_press("START"))  # not mapped

    def test_xinput_driver_instantiation(self):
        driver = XInputDriver()
        # Should not throw any exception regardless of environment
        state = driver.poll()
        self.assertIsInstance(state, GamepadState)
        self.assertIsInstance(state.buttons, set)

    def test_directinput_driver_instantiation(self):
        from modules.gamepad.drivers import DirectInputDriver
        driver = DirectInputDriver()
        state = driver.poll()
        self.assertIsInstance(state, GamepadState)
        self.assertIsInstance(state.buttons, set)

    def test_composite_driver_instantiation(self):
        from modules.gamepad.drivers import CompositeGamepadDriver
        driver = CompositeGamepadDriver()
        state = driver.poll()
        self.assertIsInstance(state, GamepadState)
        self.assertIsInstance(state.buttons, set)

    def test_driver_factory(self):
        driver = get_gamepad_driver("auto")
        self.assertIsNotNone(driver)
        self.assertIn("Universal", driver.get_driver_name())

    def test_telemetry_emission(self):
        manager = GamepadInputManager()
        mock = DummyMockDriver()
        manager.driver = mock

        captured_telemetry = []
        manager.telemetry_updated.connect(captured_telemetry.append)

        # Deflect right stick and press A
        mock.state.thumb_rx = 0.5
        mock.state.thumb_ry = 0.8
        mock.state.buttons = {BUTTON_A}
        mock.state.left_trigger = 0.75
        manager.poll_cycle()

        self.assertEqual(len(captured_telemetry), 1)
        t = captured_telemetry[0]
        self.assertTrue(t["connected"])
        self.assertIn("A", t["buttons"])
        self.assertEqual(t["thumb_rx"], 0.5)
        self.assertEqual(t["thumb_ry"], 0.8)
        self.assertEqual(t["left_trigger"], 0.75)
        self.assertIn("scroll_delta", t)
        self.assertNotEqual(t["scroll_delta"], 0.0)  # should calculate scroll since thumb_ry > deadzone

    def test_visualizer_components_import(self):
        from modules.gamepad.visualizer import (
            AnalogStickRadarWidget,
            ButtonTelemetryCard,
            GamepadTesterWidget,
        )
        radar = AnalogStickRadarWidget("TEST")
        radar.set_values(0.2, -0.4, 0.15)
        self.assertEqual(radar.x_val, 0.2)
        self.assertEqual(radar.y_val, -0.4)

        card = ButtonTelemetryCard("B0", "Hint")
        card.set_value(1.0)
        self.assertEqual(card.current_val, 1.0)

    def test_gamepad_sounds(self):
        from modules.gamepad.sounds import (
            ensure_gamepad_sound_assets,
            get_gamepad_sound_asset_path,
            play_gamepad_sound,
        )
        import os
        ensure_gamepad_sound_assets()

        # Check default sound presets
        for preset in ("click", "pop", "chime", "beep"):
            path = get_gamepad_sound_asset_path(preset)
            self.assertIsNotNone(path, f"Preset {preset} should return a valid path")
            self.assertTrue(os.path.exists(path), f"File for {preset} must exist at {path}")

        # Test safe execution of play_gamepad_sound
        try:
            play_gamepad_sound("click")
            play_gamepad_sound("system")
        except Exception as e:
            self.fail(f"play_gamepad_sound raised an unexpected exception: {e}")

    def test_release_mode_and_contraction_scale(self):
        dispatcher = GamepadActionDispatcher()

        # 1. Contraction scale mapping
        dispatcher.visual_intensity = "subtle"
        self.assertEqual(dispatcher.get_contraction_scale(), 0.88)
        dispatcher.visual_intensity = "moderate"
        self.assertEqual(dispatcher.get_contraction_scale(), 0.78)
        dispatcher.visual_intensity = "intense"
        self.assertEqual(dispatcher.get_contraction_scale(), 0.68)

        # 2. Release Mode Lifecycle
        dispatcher.trigger_on_release = True
        # Press A down
        self.assertTrue(dispatcher.handle_button_down("A"))
        self.assertEqual(dispatcher._pressed_action_button, "A")

        # Release A up
        self.assertTrue(dispatcher.handle_button_up("A"))
        self.assertIsNone(dispatcher._pressed_action_button)

        # Unbound button
        self.assertFalse(dispatcher.handle_button_down("START_FAKE"))
        self.assertFalse(dispatcher.handle_button_up("START_FAKE"))

    def test_dialog_isolation_and_pomodoro_actions(self):
        from modules.gamepad.actions import GamepadActionDispatcher, ACTION_DEFINITIONS
        dispatcher = GamepadActionDispatcher()

        # 1. Verify Pomodoro actions exist
        for act in ("pomo_toggle", "pomo_skip", "pomo_reset", "pomo_expand"):
            self.assertIn(act, ACTION_DEFINITIONS)

        # 2. Verify dialog isolation
        dispatcher.is_dialog_active = True
        # In isolation mode, execute_action must return False to prevent background triggers
        self.assertFalse(dispatcher.execute_action("show_answer"))
        self.assertFalse(dispatcher.execute_action("pomo_toggle"))

        # Scroll redirection test with mock scrollbar
        class MockScrollBar:
            def __init__(self):
                self.val = 100
            def value(self):
                return self.val
            def setValue(self, v):
                self.val = v

        class MockScrollArea:
            def __init__(self):
                self._sb = MockScrollBar()
            def verticalScrollBar(self):
                return self._sb

        mock_scroll = MockScrollArea()
        dispatcher.active_dialog_scroll = mock_scroll
        dispatcher.continuous_scroll_webview(50.0)
        self.assertEqual(mock_scroll.verticalScrollBar().val, 150)

    def test_hd_button_card_dimensions(self):
        from modules.gamepad.visualizer import ButtonTelemetryCard
        card = ButtonTelemetryCard("B0", label_hint="Cross", display_title="B0 · A")
        self.assertEqual(card.card_width, 84)
        self.assertEqual(card.card_height, 54)
        self.assertEqual(card.display_title, "B0 · A")

    def test_b16_b17_specs_and_telemetry(self):
        """Verify B16 (Guide) and B17 (Touchpad) exist and update in GamepadTesterWidget."""
        from modules.gamepad.visualizer import GamepadTesterWidget
        from modules.gamepad.drivers.base import BUTTON_GUIDE, BUTTON_TOUCHPAD, ALL_STANDARD_BUTTONS

        self.assertIn(BUTTON_GUIDE, ALL_STANDARD_BUTTONS)
        self.assertIn(BUTTON_TOUCHPAD, ALL_STANDARD_BUTTONS)

        specs = GamepadTesterWidget.BUTTON_SPECS
        self.assertEqual(len(specs), 18)
        spec_ids = [s[0] for s in specs]
        self.assertIn("B16", spec_ids)
        self.assertIn("B17", spec_ids)

        tester = GamepadTesterWidget()
        tester.update_telemetry({
            "connected": True,
            "device_name": "DualShock 4",
            "buttons": {"GUIDE", "TOUCHPAD"},
        })
        self.assertEqual(tester.button_cards["B16"].current_val, 1.0)
        self.assertEqual(tester.button_cards["B17"].current_val, 1.0)

    def test_focus_wheel_widgets_ignore_unfocused(self):
        """Verify FocusWheel widgets ignore wheel events when not focused."""
        from utils.ui_helpers import FocusWheelSlider, FocusWheelComboBox, FocusWheelSpinBox

        class DummyWheelEvent:
            def __init__(self):
                self.ignored = False
                self.accepted = False
            def ignore(self):
                self.ignored = True
            def accept(self):
                self.accepted = True

        slider = FocusWheelSlider()
        combo = FocusWheelComboBox()
        spin = FocusWheelSpinBox()

        ev1, ev2, ev3 = DummyWheelEvent(), DummyWheelEvent(), DummyWheelEvent()
        slider.wheelEvent(ev1)
        combo.wheelEvent(ev2)
        spin.wheelEvent(ev3)

        self.assertTrue(ev1.ignored)
        self.assertTrue(ev2.ignored)
        self.assertTrue(ev3.ignored)

    def test_gamepad_tester_widget_update_telemetry(self):
        from modules.gamepad.visualizer import GamepadTesterWidget
        tester = GamepadTesterWidget()
        sample_telemetry = {
            "connected": True,
            "device_name": "Wireless Controller",
            "buttons": {"A", "LT"},
            "left_trigger": 0.85,
            "right_trigger": 0.0,
            "thumb_lx": 0.45,
            "thumb_ly": -0.25,
            "thumb_rx": 0.0,
            "thumb_ry": 0.0,
            "scroll_delta": 12.5,
            "scroll_stick": "right",
            "deadzone": 0.15,
        }
        # Verify update_telemetry executes cleanly without unpack error
        try:
            tester.update_telemetry(sample_telemetry)
        except Exception as e:
            self.fail(f"update_telemetry raised an unexpected error: {e}")

    def test_topbar_focus_and_navigation(self):
        """Verify focus transitions between decks and topbar and horizontal navigation."""
        from modules.gamepad.actions import GamepadActionDispatcher, ACTION_DEFINITIONS

        dispatcher = GamepadActionDispatcher()
        self.assertEqual(dispatcher.focus_zone, "decks")
        self.assertEqual(dispatcher.topbar_index, 0)

        # Toggle to topbar
        dispatcher.toggle_topbar_focus()
        self.assertEqual(dispatcher.focus_zone, "topbar")
        self.assertEqual(dispatcher.topbar_index, 0)

        # Step right across all 5 buttons
        dispatcher.navigate_topbar(1)
        self.assertEqual(dispatcher.topbar_index, 1)  # Adicionar
        dispatcher.navigate_topbar(1)
        self.assertEqual(dispatcher.topbar_index, 2)  # Painel
        dispatcher.navigate_topbar(1)
        self.assertEqual(dispatcher.topbar_index, 3)  # Estatísticas
        dispatcher.navigate_topbar(1)
        self.assertEqual(dispatcher.topbar_index, 4)  # Sincronizar
        dispatcher.navigate_topbar(1)
        self.assertEqual(dispatcher.topbar_index, 4)  # Clamps at max

        # Step left
        dispatcher.navigate_topbar(-1)
        self.assertEqual(dispatcher.topbar_index, 3)

        # Toggle back to decks
        dispatcher.toggle_topbar_focus()
        self.assertEqual(dispatcher.focus_zone, "decks")

    def test_direct_navigation_actions_defined(self):
        """Verify all new direct navigation actions are registered in ACTION_DEFINITIONS."""
        from modules.gamepad.actions import ACTION_DEFINITIONS

        expected = [
            "nav_decks",
            "nav_add",
            "nav_browse",
            "nav_stats",
            "nav_sync",
            "topbar_toggle_focus",
            "dpad_left",
            "dpad_right",
        ]
        for act in expected:
            self.assertIn(act, ACTION_DEFINITIONS)

    def test_table_bindings_expanded_height(self):
        """Verify the keybinding table has expanded height to display at least 8 actions."""
        from modules.gamepad.config_dialog import GamepadConfigWidget

        mgr = GamepadInputManager()
        mgr.driver = DummyMockDriver()
        widget = GamepadConfigWidget(input_manager=mgr)
        self.assertGreaterEqual(widget.table_bindings.minimumHeight(), 380)
        self.assertGreaterEqual(widget.table_bindings.verticalHeader().defaultSectionSize(), 38)

    def test_unlimited_multi_shortcuts_and_keyboard(self):
        """Verify actions can have unlimited triggers including keyboard shortcuts."""
        dispatcher = GamepadActionDispatcher()
        custom = {
            "show_answer": ["A", "KEY:Espaço", "RS_DOWN", "KEY:Enter", "RB"],
        }
        dispatcher.set_bindings(custom)

        self.assertTrue(dispatcher.has_binding("A"))
        self.assertTrue(dispatcher.has_binding("KEY:Espaço"))
        self.assertTrue(dispatcher.has_binding("RS_DOWN"))
        self.assertTrue(dispatcher.has_binding("KEY:Enter"))
        self.assertTrue(dispatcher.has_binding("RB"))
        self.assertFalse(dispatcher.has_binding("KEY:Escape"))

        # Both keyboard and stick directions resolve to show_answer
        self.assertEqual(dispatcher._resolve_current_action("KEY:Espaço"), "show_answer")
        self.assertEqual(dispatcher._resolve_current_action("RS_DOWN"), "show_answer")

    def test_discrete_stick_gesture_emission(self):
        """Verify tilting left or right stick emits STICK_LS_* or STICK_RS_* events."""
        from modules.gamepad.drivers.base import STICK_RS_UP, STICK_LS_DOWN
        mgr = GamepadInputManager()
        mock = DummyMockDriver()
        mgr.driver = mock

        captured_down = []
        mgr.button_down.connect(captured_down.append)

        # Deflect right stick upwards
        mock.state.thumb_ry = 0.75
        mgr.poll_cycle()
        self.assertIn(STICK_RS_UP, captured_down)

        # Deflect left stick downwards
        mock.state.thumb_ly = -0.80
        mgr.poll_cycle()
        self.assertIn(STICK_LS_DOWN, captured_down)

    def test_scroll_page_actions_and_stick_defaults(self):
        """Verify scroll_page_* actions and default inclusion of stick gestures."""
        self.assertIn("scroll_page_up", ACTION_DEFINITIONS)
        self.assertIn("scroll_page_down", ACTION_DEFINITIONS)
        self.assertIn("scroll_page_left", ACTION_DEFINITIONS)
        self.assertIn("scroll_page_right", ACTION_DEFINITIONS)

        self.assertIn("LS_UP", ACTION_DEFINITIONS["scroll_up"]["default"])
        self.assertIn("LS_DOWN", ACTION_DEFINITIONS["scroll_down"]["default"])
        self.assertIn("LS_LEFT", ACTION_DEFINITIONS["dpad_left"]["default"])
        self.assertIn("LS_RIGHT", ACTION_DEFINITIONS["dpad_right"]["default"])
        self.assertIn("RS_UP", ACTION_DEFINITIONS["scroll_page_up"]["default"])
        self.assertIn("RS_DOWN", ACTION_DEFINITIONS["scroll_page_down"]["default"])

    def test_pomodoro_gamepad_actions(self):
        """Verify Pomodoro actions trigger immediately as instant actions on button down."""
        dispatcher = GamepadActionDispatcher()
        dispatcher.set_bindings({
            "pomo_toggle": ["START"],
            "pomo_skip": ["RB"],
            "pomo_reset": ["LB"],
            "pomo_expand": ["BACK"],
        })

        # Test instant trigger on button down
        self.assertTrue(dispatcher.handle_button_down("START"))
        self.assertTrue(dispatcher.handle_button_down("RB"))
        self.assertTrue(dispatcher.handle_button_down("LB"))
        self.assertTrue(dispatcher.handle_button_down("BACK"))

    def test_multi_action_fallback(self):
        """Verify button assigned to multiple actions falls through non-applicable actions."""
        dispatcher = GamepadActionDispatcher()
        # R3 is assigned to pause_audio and pomo_toggle
        dispatcher.set_bindings({
            "pause_audio": ["R3"],
            "pomo_toggle": ["R3"],
        })
        # Since we are in mock environment (not in review), pause_audio returns False,
        # but pomo_toggle succeeds, so handle_button_down should return True.
        self.assertTrue(dispatcher.handle_button_down("R3"))


if __name__ == "__main__":
    unittest.main()
