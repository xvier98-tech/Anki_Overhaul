# -*- coding: utf-8 -*-
"""
Unit tests for Gamepad Accessibility & Modal Navigation Suite.
Validates:
1. ACTION_DEFINITIONS containing pomo_fullscreen and open_settings.
2. Action execution dispatch for pomo_fullscreen and open_settings.
3. RestOverlayDialog gamepad D-pad / thumbstick navigation and A / B button actions.
4. ObsidianSuiteHubDialog accessible navigation (LB/RB tab switching, LS directional navigation,
   A button toggle/click, RS slider/spinbox adjustment, B popup/dialog dismiss).
"""

import unittest
from unittest.mock import MagicMock, patch

from modules.gamepad.actions import (
    ACTION_DEFINITIONS,
    GamepadActionDispatcher,
)
import modules.gamepad.actions as actions_mod
from modules.pomodoro.timer_engine import PomodoroEngine
from modules.pomodoro.hud_manager import RestOverlayDialog
import modules.unified_config.settings_dialog as settings_dialog_mod
from modules.unified_config.settings_dialog import ObsidianSuiteHubDialog


class TestGamepadAccessibility(unittest.TestCase):
    """Suíte de testes de acessibilidade e navegação via gamepad."""

    def test_action_definitions_contains_new_actions(self):
        """
        Valida que 'pomo_fullscreen' e 'open_settings' estão presentes em ACTION_DEFINITIONS
        com seus respectivos metadados: name, description e default.
        """
        # 1. pomo_fullscreen
        self.assertIn("pomo_fullscreen", ACTION_DEFINITIONS)
        pomo_action = ACTION_DEFINITIONS["pomo_fullscreen"]
        self.assertIn("name", pomo_action)
        self.assertIn("description", pomo_action)
        self.assertIn("default", pomo_action)
        self.assertIsInstance(pomo_action["name"], str)
        self.assertIsInstance(pomo_action["description"], str)
        self.assertIsInstance(pomo_action["default"], list)
        self.assertTrue(len(pomo_action["name"]) > 0)
        self.assertTrue(len(pomo_action["description"]) > 0)

        # 2. open_settings
        self.assertIn("open_settings", ACTION_DEFINITIONS)
        settings_action = ACTION_DEFINITIONS["open_settings"]
        self.assertIn("name", settings_action)
        self.assertIn("description", settings_action)
        self.assertIn("default", settings_action)
        self.assertIsInstance(settings_action["name"], str)
        self.assertIsInstance(settings_action["description"], str)
        self.assertIsInstance(settings_action["default"], list)
        self.assertTrue(len(settings_action["name"]) > 0)
        self.assertTrue(len(settings_action["description"]) > 0)

    def test_action_execution(self):
        """
        Valida que execute_action('pomo_fullscreen') dispara toggle_focus_fullscreen
        e execute_action('open_settings') dispara a abertura do diálogo de configurações.
        """
        dispatcher = GamepadActionDispatcher()

        mock_mw = MagicMock()
        mock_mw.state = "deckBrowser"

        with patch.object(actions_mod, "mw", mock_mw):
            # Teste 1: execute_action("pomo_fullscreen") -> toggle_focus_fullscreen
            with patch("modules.pomodoro.hooks.toggle_focus_fullscreen") as mock_toggle:
                result_fullscreen = dispatcher.execute_action("pomo_fullscreen")
                self.assertTrue(result_fullscreen)
                mock_toggle.assert_called_once()

            # Teste 2: execute_action("open_settings") -> ObsidianSuiteHubDialog
            with patch("modules.unified_config.settings_dialog.ObsidianSuiteHubDialog") as mock_dialog_cls:
                mock_dialog_instance = MagicMock()
                mock_dialog_cls.return_value = mock_dialog_instance

                result_settings = dispatcher.execute_action("open_settings")
                self.assertTrue(result_settings)
                mock_dialog_cls.assert_called_once()
                mock_dialog_instance.exec.assert_called_once()

    def test_rest_overlay_gamepad_navigation(self):
        """
        Valida que RestOverlayDialog suporta navegação por analógico esquerdo / D-pad:
        - Alterna entre '+5 min' (índice 0) e 'Voltar ao Estudo' (índice 1).
        - Pressionar A com índice 0 dispara _add_5_minutes.
        - Pressionar A com índice 1 dispara _resume_work.
        - Pressionar B dispara _resume_work.
        """
        engine = PomodoroEngine()
        dialog = RestOverlayDialog(engine)

        # Estado inicial padrão: 'Voltar ao Estudo' (índice 1) selecionado
        self.assertEqual(dialog._selected_btn_idx, 1)

        # Navegação para a esquerda com DPAD_LEFT seleciona '+5 min' (índice 0)
        self.assertTrue(dialog.handle_gamepad_button("DPAD_LEFT"))
        self.assertEqual(dialog._selected_btn_idx, 0)

        # Navegação para a direita com DPAD_RIGHT seleciona 'Voltar ao Estudo' (índice 1)
        self.assertTrue(dialog.handle_gamepad_button("DPAD_RIGHT"))
        self.assertEqual(dialog._selected_btn_idx, 1)

        # Navegação com analógico esquerdo: STICK_LS_UP seleciona índice 0
        self.assertTrue(dialog.handle_gamepad_button("STICK_LS_UP"))
        self.assertEqual(dialog._selected_btn_idx, 0)

        # Navegação com analógico esquerdo: STICK_LS_DOWN seleciona índice 1
        self.assertTrue(dialog.handle_gamepad_button("STICK_LS_DOWN"))
        self.assertEqual(dialog._selected_btn_idx, 1)

        # Aliases curtos: LS_LEFT e LS_RIGHT
        self.assertTrue(dialog.handle_gamepad_button("LS_LEFT"))
        self.assertEqual(dialog._selected_btn_idx, 0)
        self.assertTrue(dialog.handle_gamepad_button("LS_RIGHT"))
        self.assertEqual(dialog._selected_btn_idx, 1)

        # Mock das funções de ação para validação estrita dos cliques do gamepad
        dialog._add_5_minutes = MagicMock()
        dialog._resume_work = MagicMock()

        # Botão A com índice 0 dispara _add_5_minutes
        dialog._selected_btn_idx = 0
        self.assertTrue(dialog.handle_gamepad_button("A"))
        dialog._add_5_minutes.assert_called_once()
        dialog._resume_work.assert_not_called()

        # Botão A com índice 1 dispara _resume_work
        dialog._add_5_minutes.reset_mock()
        dialog._resume_work.reset_mock()
        dialog._selected_btn_idx = 1
        self.assertTrue(dialog.handle_gamepad_button("A"))
        dialog._resume_work.assert_called_once()
        dialog._add_5_minutes.assert_not_called()

        # Botão B dispara _resume_work mesmo que o índice seja 0
        dialog._add_5_minutes.reset_mock()
        dialog._resume_work.reset_mock()
        dialog._selected_btn_idx = 0
        self.assertTrue(dialog.handle_gamepad_button("B"))
        dialog._resume_work.assert_called_once()
        dialog._add_5_minutes.assert_not_called()

    def test_settings_dialog_gamepad_navigation(self):
        """
        Valida navegação acessível em ObsidianSuiteHubDialog via gamepad:
        - LB/RB alternam abas.
        - LS_DOWN/LS_UP navegam widgets focáveis.
        - A alterna QCheckBox e clica QPushButton.
        - RS_LEFT/RS_RIGHT ajustam valores de slider/spinbox.
        - B fecha popup se aberto, senão fecha diálogo.
        """
        # Criamos subclasses isoladas do mock UI para simular fielmente os tipos de widgets
        class MockCheckBox(settings_dialog_mod._MockUI):
            pass

        class MockButton(settings_dialog_mod._MockUI):
            pass

        class MockSlider(settings_dialog_mod._MockUI):
            pass

        class MockSpinBox(settings_dialog_mod._MockUI):
            pass

        class MockComboBox(settings_dialog_mod._MockUI):
            pass

        # Aplicamos patch nos tipos de widgets dentro de settings_dialog
        with patch.object(settings_dialog_mod, "QCheckBox", MockCheckBox), \
             patch.object(settings_dialog_mod, "QPushButton", MockButton), \
             patch.object(settings_dialog_mod, "QSlider", MockSlider), \
             patch.object(settings_dialog_mod, "QSpinBox", MockSpinBox), \
             patch.object(settings_dialog_mod, "QComboBox", MockComboBox):

            dialog = ObsidianSuiteHubDialog()

            # 1. Alternância de abas via LB e RB
            total_tabs = dialog.tabs.count()
            self.assertGreater(total_tabs, 0)
            initial_tab = dialog.tabs.currentIndex()

            # RB avança para a próxima aba (com wrap-around modular)
            self.assertTrue(dialog.handle_gamepad_button("RB"))
            self.assertEqual(dialog.tabs.currentIndex(), (initial_tab + 1) % total_tabs)

            # LB retorna para a aba anterior
            self.assertTrue(dialog.handle_gamepad_button("LB"))
            self.assertEqual(dialog.tabs.currentIndex(), initial_tab)

            # 2. Configuração dos widgets interativos da aba
            chk = MockCheckBox()
            chk.setChecked(False)

            btn = MockButton()
            btn.click = MagicMock()

            slider = MockSlider()
            slider.setValue(50)

            spin = MockSpinBox()
            spin.setValue(10)

            combo = MockComboBox()
            combo.showPopup = MagicMock()
            combo.hidePopup = MagicMock()

            interactive_widgets = [chk, btn, slider, spin, combo]
            dialog._get_interactive_widgets_for_current_tab = lambda: interactive_widgets
            dialog._is_combobox_popup_open = lambda c: getattr(dialog, "_active_open_combobox", None) == c

            # Inicia o foco no primeiro widget (chk)
            dialog._set_gamepad_focus(chk)
            self.assertEqual(dialog._current_gamepad_widget, chk)

            # 3. Navegação vertical com LS_DOWN e LS_UP
            # LS_DOWN move de chk -> btn
            self.assertTrue(dialog.handle_gamepad_button("LS_DOWN"))
            self.assertEqual(dialog._current_gamepad_widget, btn)

            # LS_DOWN move de btn -> slider
            self.assertTrue(dialog.handle_gamepad_button("LS_DOWN"))
            self.assertEqual(dialog._current_gamepad_widget, slider)

            # LS_UP move de slider -> btn
            self.assertTrue(dialog.handle_gamepad_button("LS_UP"))
            self.assertEqual(dialog._current_gamepad_widget, btn)

            # LS_UP move de btn -> chk
            self.assertTrue(dialog.handle_gamepad_button("LS_UP"))
            self.assertEqual(dialog._current_gamepad_widget, chk)

            # LS_UP a partir de chk faz wrap para combo (último widget)
            self.assertTrue(dialog.handle_gamepad_button("LS_UP"))
            self.assertEqual(dialog._current_gamepad_widget, combo)

            # 4. Ação do Botão A: QCheckBox e QPushButton
            # Toggle de QCheckBox
            dialog._set_gamepad_focus(chk)
            self.assertFalse(chk.isChecked())
            self.assertTrue(dialog.handle_gamepad_button("A"))
            self.assertTrue(chk.isChecked())
            self.assertTrue(dialog.handle_gamepad_button("A"))
            self.assertFalse(chk.isChecked())

            # Clique em QPushButton
            dialog._set_gamepad_focus(btn)
            self.assertTrue(dialog.handle_gamepad_button("A"))
            btn.click.assert_called_once()

            # 5. Ajuste Horizontal via RS_RIGHT / RS_LEFT em QSlider e QSpinBox
            # QSlider
            dialog._set_gamepad_focus(slider)
            self.assertEqual(slider.value(), 50)
            self.assertTrue(dialog.handle_gamepad_button("RS_RIGHT"))
            self.assertEqual(slider.value(), 51)
            self.assertTrue(dialog.handle_gamepad_button("RS_LEFT"))
            self.assertEqual(slider.value(), 50)

            # QSpinBox
            dialog._set_gamepad_focus(spin)
            self.assertEqual(spin.value(), 10)
            self.assertTrue(dialog.handle_gamepad_button("RS_RIGHT"))
            self.assertEqual(spin.value(), 11)
            self.assertTrue(dialog.handle_gamepad_button("RS_LEFT"))
            self.assertEqual(spin.value(), 10)

            # 6. Comportamento do Botão B: Fecha popup se aberto, senão fecha diálogo
            # Abrir popup do QComboBox com botão A
            dialog._set_gamepad_focus(combo)
            self.assertTrue(dialog.handle_gamepad_button("A"))
            self.assertEqual(dialog._active_open_combobox, combo)

            dialog.reject = MagicMock()

            # Pressionar B enquanto o popup está aberto fecha apenas o popup (não fecha o diálogo)
            self.assertTrue(dialog.handle_gamepad_button("B"))
            combo.hidePopup.assert_called_once()
            self.assertIsNone(dialog._active_open_combobox)
            dialog.reject.assert_not_called()

            # Pressionar B quando nenhum popup está aberto fecha o diálogo (reject)
            self.assertTrue(dialog.handle_gamepad_button("B"))
            dialog.reject.assert_called_once()

    def test_dialog_isolation_delegation_in_dispatcher(self):
        """
        Valida que GamepadActionDispatcher roteia eventos de botão para o diálogo ativo
        quando set_active_dialog() está definido, e bloqueia ações normais (isolamento modal).
        """
        dispatcher = GamepadActionDispatcher()

        mock_dialog = MagicMock()
        mock_dialog.handle_gamepad_button.return_value = True

        # Define diálogo ativo
        dispatcher.set_active_dialog(mock_dialog)
        self.assertEqual(dispatcher.get_active_dialog(), mock_dialog)
        self.assertTrue(dispatcher.is_dialog_active)

        # Disparar botão deve delegar ao diálogo
        handled = dispatcher.handle_button_down("A")
        self.assertTrue(handled)
        mock_dialog.handle_gamepad_button.assert_called_with("A")

        # execute_action deve retornar False devido ao isolamento
        self.assertFalse(dispatcher.execute_action("show_answer"))
        self.assertFalse(dispatcher.execute_action("pomo_fullscreen"))

        # Desativar diálogo
        dispatcher.set_active_dialog(None)
        self.assertIsNone(dispatcher.get_active_dialog())
        self.assertFalse(dispatcher.is_dialog_active)


if __name__ == "__main__":
    unittest.main()
