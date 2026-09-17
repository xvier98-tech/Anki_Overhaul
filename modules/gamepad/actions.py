# -*- coding: utf-8 -*-
"""
Action Mapping and Execution Layer for Gamepad Inputs.
Binds normalized gamepad buttons to native Anki actions across DeckBrowser, Overview, and Reviewer.
Includes Release Mode (trigger on button up), customizable visual contraction intensity,
state-transition cooldown debouncing, and tactile on-screen visual button feedback.
"""

import sys
import ctypes
import time
from typing import Dict, List, Optional, Any
try:
    from aqt import mw
    import aqt.sound
    from aqt.utils import tooltip
except ImportError:
    mw = None
    aqt = None
    tooltip = None


def keep_system_and_pomodoro_active() -> None:
    """
    Prevents OS display sleep/dimming and notifies the Pomodoro engine of user activity.
    On Windows: calls SetThreadExecutionState(ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
    to reset system and display idle timers.
    """
    if sys.platform == "win32":
        try:
            # 0x00000001 = ES_SYSTEM_REQUIRED, 0x00000002 = ES_DISPLAY_REQUIRED
            ctypes.windll.kernel32.SetThreadExecutionState(0x00000001 | 0x00000002)
        except Exception:
            pass

    try:
        try:
            from ..pomodoro.hooks import get_pomodoro_engine
        except (ImportError, ValueError):
            from modules.pomodoro.hooks import get_pomodoro_engine
        engine = get_pomodoro_engine()
        if engine and hasattr(engine, "register_user_activity"):
            engine.register_user_activity()
    except Exception:
        pass


try:
    from .sounds import play_gamepad_sound
except (ImportError, ValueError):
    try:
        from modules.gamepad.sounds import play_gamepad_sound
    except (ImportError, ValueError):
        def play_gamepad_sound(*args, **kwargs):
            pass

try:
    from ...utils.i18n import tr
except (ImportError, ValueError):
    try:
        from utils.i18n import tr
    except ImportError:
        def tr(key, default=None, **kwargs):
            return default if default is not None else key

ACTION_DEFINITIONS = {
    "show_answer": {
        "name": "Abrir Baralho / Iniciar Estudo / Mostrar Resposta",
        "description": "No início: abre o baralho. No overview: clica em Estudar. No reviewer: exibe resposta / fácil (Espaço/A)",
        "default": ["A", "RT"],
    },
    "return_screen": {
        "name": "Retornar Tela (Voltar ao Início)",
        "description": "Retorna da tela de visão geral (overview) ou revisão para a tela de baralhos",
        "default": ["B"],
    },
    "expand_subdecks": {
        "name": "Expandir / Recolher Subbaralhos",
        "description": "Alterna a expansão da árvore de subbaralhos do baralho selecionado no início",
        "default": ["X"],
    },
    "answer_ease_1": {
        "name": "Responder: De novo (1)",
        "description": "Avalia o card com 'De novo'",
        "default": ["X"],
    },
    "answer_ease_2": {
        "name": "Responder: Difícil (2)",
        "description": "Avalia o card com 'Difícil'",
        "default": ["Y"],
    },
    "answer_ease_3": {
        "name": "Responder: Bom (3)",
        "description": "Avalia o card com 'Bom'",
        "default": ["B"],
    },
    "answer_ease_4": {
        "name": "Responder: Fácil (4)",
        "description": "Avalia o card com 'Fácil'",
        "default": ["A"],
    },
    "undo": {
        "name": "Desfazer Revisão",
        "description": "Desfaz a última resposta (Ctrl+Z)",
        "default": ["LB"],
    },
    "replay_audio": {
        "name": "Repetir Áudio",
        "description": "Toca novamente o áudio do card (R)",
        "default": ["L3"],
    },
    "pause_audio": {
        "name": "Pausar Áudio",
        "description": "Alterna reprodução/pausa do áudio atual",
        "default": ["R3"],
    },
    "toggle_flag": {
        "name": "Alternar Bandeira / Flag",
        "description": "Adiciona ou remove a bandeira do card atual",
        "default": ["BACK"],
    },
    "suspend_card": {
        "name": "Suspender Card",
        "description": "Suspende o card atual (!)",
        "default": ["START"],
    },
    "scroll_up": {
        "name": "Navegação: Cima (Rolar Página / Baralho Acima)",
        "description": "Rola o conteúdo para cima ou navega para o baralho anterior",
        "default": ["DPAD_UP", "LS_UP"],
    },
    "scroll_down": {
        "name": "Navegação: Baixo (Rolar Página / Baralho Abaixo)",
        "description": "Rola o conteúdo para baixo ou navega para o próximo baralho",
        "default": ["DPAD_DOWN", "LS_DOWN"],
    },
    "dpad_left": {
        "name": "Navegação: Esquerda (Barra Superior / Recolher)",
        "description": "Seleciona o botão anterior na barra superior ou recolhe subbaralhos",
        "default": ["DPAD_LEFT", "LS_LEFT"],
    },
    "dpad_right": {
        "name": "Navegação: Direita (Barra Superior / Expandir)",
        "description": "Seleciona o próximo botão na barra superior ou expande subbaralhos",
        "default": ["DPAD_RIGHT", "LS_RIGHT"],
    },
    "scroll_page_up": {
        "name": "Rolagem: Rolar Página para Cima (Right Stick)",
        "description": "Rola o conteúdo da página ou janela para cima",
        "default": ["RS_UP"],
    },
    "scroll_page_down": {
        "name": "Rolagem: Rolar Página para Baixo (Right Stick)",
        "description": "Rola o conteúdo da página ou janela para baixo",
        "default": ["RS_DOWN"],
    },
    "scroll_page_left": {
        "name": "Rolagem: Rolar Conteúdo para Esquerda",
        "description": "Rola o conteúdo da página ou janela para a esquerda",
        "default": ["RS_LEFT"],
    },
    "scroll_page_right": {
        "name": "Rolagem: Rolar Conteúdo para Direita",
        "description": "Rola o conteúdo da página ou janela para a direita",
        "default": ["RS_RIGHT"],
    },
    "nav_decks": {
        "name": "Navegação: Ir para Baralhos (Início)",
        "description": "Retorna imediatamente à tela inicial de baralhos",
        "default": [],
    },
    "nav_add": {
        "name": "Navegação: Abrir Adicionar Cartões",
        "description": "Abre a janela de criação e adição de novos cartões",
        "default": [],
    },
    "nav_browse": {
        "name": "Navegação: Abrir Painel de Cartões (Browse)",
        "description": "Abre o navegador e painel de cartões da coleção",
        "default": [],
    },
    "nav_stats": {
        "name": "Navegação: Abrir Estatísticas",
        "description": "Abre o painel de gráficos e estatísticas de estudo",
        "default": [],
    },
    "nav_sync": {
        "name": "Navegação: Sincronizar Coleção",
        "description": "Dispara a sincronização imediata com os servidores do AnkiWeb",
        "default": [],
    },
    "topbar_toggle_focus": {
        "name": "Navegação: Alternar entre Baralhos e Barra Superior",
        "description": "Alterna o foco do controle entre a lista de baralhos e os 5 botões superiores",
        "default": [],
    },
    "pomo_toggle": {
        "name": "Pomodoro: Iniciar / Pausar Cronômetro",
        "description": "Alterna entre rodar e pausar o ciclo de foco/intervalo do Pomodoro",
        "default": [],
    },
    "pomo_skip": {
        "name": "Pomodoro: Pular para Próxima Etapa",
        "description": "Avança imediatamente para a próxima etapa (foco ou descanso)",
        "default": [],
    },
    "pomo_reset": {
        "name": "Pomodoro: Reiniciar Rodada Atual",
        "description": "Reinicia o contador de tempo da etapa atual do Pomodoro",
        "default": [],
    },
    "pomo_expand": {
        "name": "Pomodoro: Expandir / Minimizar Janela Flutuante",
        "description": "Alterna entre o botão flutuante circular (FAB) e a janela expandida",
        "default": [],
    },
    "pomo_fullscreen": {
        "name": "Pomodoro: Alternar Modo Tela Cheia",
        "description": "Alterna o modo de tela cheia (F11) da janela principal para imersão e foco nos estudos",
        "default": [],
    },
    "open_settings": {
        "name": "Configurações: Abrir Central Obsidian Suite",
        "description": "Abre o painel unificado de configurações da suíte Obsidian Addon",
        "default": [],
    },
}


def qt_key_event_to_string(event) -> str:
    """Translates a Qt QKeyEvent into a clean, human-readable key name string."""
    try:
        from PyQt6.QtCore import Qt
        key = event.key()
        modifiers = event.modifiers()

        # Skip standalone modifiers
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return ""

        parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("Shift")

        key_map = {
            Qt.Key.Key_Space: "Espaço",
            Qt.Key.Key_Return: "Enter",
            Qt.Key.Key_Enter: "Enter",
            Qt.Key.Key_Backspace: "Backspace",
            Qt.Key.Key_Tab: "Tab",
            Qt.Key.Key_Escape: "Escape",
            Qt.Key.Key_Up: "Cima",
            Qt.Key.Key_Down: "Baixo",
            Qt.Key.Key_Left: "Esquerda",
            Qt.Key.Key_Right: "Direita",
            Qt.Key.Key_PageUp: "PageUp",
            Qt.Key.Key_PageDown: "PageDown",
            Qt.Key.Key_Home: "Home",
            Qt.Key.Key_End: "End",
            Qt.Key.Key_Delete: "Delete",
            Qt.Key.Key_Insert: "Insert",
        }

        if key in key_map:
            key_str = key_map[key]
        else:
            text = event.text().upper() if hasattr(event, "text") else ""
            if text and text.isprintable():
                key_str = text
            else:
                key_name = getattr(Qt.Key(key), "name", str(key))
                key_str = key_name.replace("Key_", "")

        if parts:
            return "+".join(parts) + "+" + key_str
        return key_str
    except Exception:
        return ""


def get_default_bindings() -> Dict[str, List[str]]:
    """Returns the default mapping dictionary of action_id -> list of default triggers."""
    res = {}
    for action_id, meta in ACTION_DEFINITIONS.items():
        res[action_id] = list(meta["default"])
    return res


class GamepadActionDispatcher:
    """Dispatches physical button events to Anki actions based on configured bindings."""

    def __init__(self, bindings: Optional[Dict[str, List[str]]] = None):
        self.bindings = bindings if bindings is not None else get_default_bindings()
        self._last_state_transition_time: float = 0.0
        self.state_transition_cooldown: float = 0.25  # 250ms minimum interval between question -> answer action

        # Release mode & visual intensity options
        self.trigger_on_release: bool = True
        self.visual_intensity: str = "moderate"
        self._pressed_action_button: Optional[str] = None
        self._pressed_action_id: Optional[str] = None

        # Isolation flag and active modal dialog reference
        self._active_dialog: Optional[Any] = None
        self.is_dialog_active: bool = False
        self.active_dialog_scroll: Optional[Any] = None

        # Focus Zones in DeckBrowser: "decks" or "topbar"
        self.focus_zone: str = "decks"
        self.topbar_index: int = 0          # 0: Baralhos, 1: Adicionar, 2: Painel, 3: Estatísticas, 4: Sincronizar
        self.focused_deck_index: int = 0    # Tracks index of focused deck row in DeckBrowser
        self.last_focused_deck_id: Optional[str] = None

    def set_active_dialog(self, dialog: Optional[Any]):
        """Registers the currently active modal dialog or clears it if None."""
        self._active_dialog = dialog
        self.is_dialog_active = dialog is not None
        if dialog and hasattr(dialog, "findChild"):
            try:
                from PyQt6.QtWidgets import QScrollArea
                scroll = dialog.findChild(QScrollArea)
                if scroll:
                    self.active_dialog_scroll = scroll
            except Exception:
                pass
        elif dialog is None:
            self.active_dialog_scroll = None

    def get_active_dialog(self) -> Optional[Any]:
        """Returns the currently active dialog instance if set."""
        return self._active_dialog

    def set_bindings(self, new_bindings: Dict[str, List[str]]):
        self.bindings = new_bindings

    def has_binding(self, button_or_trigger: str) -> bool:
        """Checks if a given button, stick gesture, or keyboard trigger is mapped to any action."""
        for bound_list in self.bindings.values():
            if button_or_trigger in bound_list:
                return True
        return False

    def get_contraction_scale(self) -> float:
        """Returns the scale factor for the visual button press animation."""
        scales = {
            "subtle": 0.88,
            "moderate": 0.78,
            "intense": 0.68,
        }
        return scales.get(self.visual_intensity, 0.78)

    def _get_matching_actions(self, button_name: str) -> List[str]:
        """Returns candidate actions for a button, sorted intelligently by context."""
        matching_actions = []
        for action_id, bound_btns in self.bindings.items():
            if button_name in bound_btns:
                matching_actions.append(action_id)

        if not matching_actions:
            return []

        state = getattr(mw, "state", "") if mw else ""
        rev_state = getattr(getattr(mw, "reviewer", None), "state", "") if mw else ""

        def sort_key(a: str) -> int:
            if state == "review":
                if rev_state == "question":
                    return 0 if a == "show_answer" else (1 if not a.startswith("answer_ease") else 2)
                elif rev_state == "answer":
                    return 0 if a.startswith("answer_ease") else (1 if a != "show_answer" else 2)
            else:
                # Outside review, review-only actions should have lower priority
                review_only = (
                    "answer_ease_1", "answer_ease_2", "answer_ease_3", "answer_ease_4",
                    "show_answer", "replay_audio", "toggle_flag", "suspend_card"
                )
                if a in review_only:
                    return 2
            return 1

        matching_actions.sort(key=sort_key)
        return matching_actions

    def _resolve_current_action(self, button_name: str) -> Optional[str]:
        """Resolves the best matching action for the pressed button based on Anki's state."""
        actions = self._get_matching_actions(button_name)
        return actions[0] if actions else None

    def handle_button_down(self, button_name: str) -> bool:
        """
        Called when a physical button is pressed down.
        In Release Mode, activates the on-screen visual pressed state and sound,
        holding the action execution until release.
        """
        keep_system_and_pomodoro_active()

        # Active dialog / modal widget delegation
        active_dlg = self.get_active_dialog()
        if not active_dlg:
            try:
                from PyQt6.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    modal = app.activeModalWidget()
                    if modal and hasattr(modal, "handle_gamepad_button"):
                        active_dlg = modal
            except Exception:
                pass

        if active_dlg and hasattr(active_dlg, "handle_gamepad_button"):
            try:
                handled = active_dlg.handle_gamepad_button(button_name)
                if handled:
                    play_gamepad_sound()
                return True
            except Exception as e:
                print(f"[Gamepad] Error delegating button {button_name} to active dialog: {e}")
                return True

        if self.is_dialog_active:
            return False

        matching_actions = self._get_matching_actions(button_name)
        if not matching_actions:
            return False

        # Instant actions (navigation, pomodoro, undo, audio hotkeys) always trigger immediately on press
        instant_actions = (
            "scroll_up", "scroll_down", "scroll_page_up", "scroll_page_down",
            "scroll_page_left", "scroll_page_right", "dpad_left", "dpad_right",
            "undo", "replay_audio", "pause_audio", "toggle_flag", "suspend_card",
            "nav_decks", "nav_add", "nav_browse", "nav_stats", "nav_sync", "topbar_toggle_focus",
            "pomo_toggle", "pomo_skip", "pomo_reset", "pomo_expand", "pomo_fullscreen", "open_settings",
        )

        for action_id in matching_actions:
            if action_id in instant_actions:
                if self.execute_action(action_id):
                    play_gamepad_sound()
                    return True
            elif self.trigger_on_release:
                self._pressed_action_button = button_name
                self._pressed_action_id = action_id
                self.set_button_visual_pressed(action_id, pressed=True)
                play_gamepad_sound()
                return True
            else:
                if self.execute_action(action_id):
                    play_gamepad_sound()
                    return True

        return False

    def handle_button_up(self, button_name: str) -> bool:
        """
        Called when a physical button is released.
        In Release Mode, releases the on-screen pressed state and executes the action.
        """
        if self.is_dialog_active:
            return False
        if self.trigger_on_release and self._pressed_action_button == button_name:
            action_id = self._pressed_action_id
            self._pressed_action_button = None
            self._pressed_action_id = None
            if action_id:
                self.set_button_visual_pressed(action_id, pressed=False)
                return self.execute_action(action_id)
        return False

    def handle_button_press(self, button_name: str) -> bool:
        """
        Translates pressed button to matching action and executes exactly ONE action per press.
        Prioritizes actions contextually according to Anki's current state to avoid double-triggers.
        """
        keep_system_and_pomodoro_active()

        active_dlg = self.get_active_dialog()
        if not active_dlg:
            try:
                from PyQt6.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    modal = app.activeModalWidget()
                    if modal and hasattr(modal, "handle_gamepad_button"):
                        active_dlg = modal
            except Exception:
                pass

        if active_dlg and hasattr(active_dlg, "handle_gamepad_button"):
            try:
                handled = active_dlg.handle_gamepad_button(button_name)
                if handled:
                    play_gamepad_sound()
                return True
            except Exception as e:
                print(f"[Gamepad] Error delegating button {button_name} to active dialog: {e}")
                return True

        if self.is_dialog_active:
            return False

        matching_actions = self._get_matching_actions(button_name)
        if not matching_actions:
            return False

        for action_id in matching_actions:
            if self.execute_action(action_id):
                play_gamepad_sound()
                return True

        return False

    def _get_active_web(self):
        """Returns the currently visible WebView based on mw.state."""
        if not mw:
            return None
        if mw.state == "review" and hasattr(mw, "reviewer") and mw.reviewer and mw.reviewer.web:
            return mw.reviewer.web
        elif mw.state == "deckBrowser" and hasattr(mw, "deckBrowser") and mw.deckBrowser and mw.deckBrowser.web:
            return mw.deckBrowser.web
        elif mw.state == "overview" and hasattr(mw, "overview") and mw.overview and mw.overview.web:
            return mw.overview.web
        return None

    def set_button_visual_pressed(self, action_id: str, pressed: bool):
        """
        Sets or releases the on-screen visual pressed state for the button corresponding to action_id.
        Allows the user to hold the gamepad button and see the button stay pressed on screen.
        """
        if not mw:
            return

        scale = self.get_contraction_scale()
        state = getattr(mw, "state", "")
        rev_state = getattr(getattr(mw, "reviewer", None), "state", "")

        # 1. Answer buttons (or show_answer in answer state)
        if action_id.startswith("answer_ease_") or (action_id == "show_answer" and state == "review" and rev_state == "answer"):
            ease = 4
            if action_id.startswith("answer_ease_"):
                ease = int(action_id.split("_")[-1])
            bottom_web = getattr(mw.reviewer, "bottom", None) if hasattr(mw, "reviewer") else None
            web = getattr(bottom_web, "web", None) if bottom_web else getattr(getattr(mw, "reviewer", None), "web", None)
            if not web:
                return
            js = f"""
            (function() {{
                let btn = document.querySelector('button[data-ease="{ease}"]') 
                       || document.getElementById('ease{ease}')
                       || document.querySelector('table#middle td:nth-child({ease}) button')
                       || document.querySelectorAll('button')[{ease - 1}];
                if (btn) {{
                    btn.style.transition = 'transform 0.08s cubic-bezier(0.4, 0, 0.2, 1), filter 0.08s ease, box-shadow 0.08s ease';
                    if ({str(pressed).lower()}) {{
                        btn.style.transform = 'scale({scale})';
                        btn.style.filter = 'brightness(1.55)';
                        btn.style.boxShadow = '0 0 20px rgba(56, 189, 248, 0.95)';
                    }} else {{
                        btn.style.transform = '';
                        btn.style.filter = '';
                        btn.style.boxShadow = '';
                    }}
                }}
            }})();
            """
            try:
                web.eval(js)
            except Exception:
                pass

        # 2. Show Answer in question state
        elif action_id == "show_answer" and state == "review" and rev_state == "question":
            bottom_web = getattr(mw.reviewer, "bottom", None) if hasattr(mw, "reviewer") else None
            web = getattr(bottom_web, "web", None) if bottom_web else getattr(getattr(mw, "reviewer", None), "web", None)
            if not web:
                return
            js = f"""
            (function() {{
                let btn = document.getElementById('ansbut') 
                       || document.querySelector('#ansbut button')
                       || document.querySelector('button');
                if (btn) {{
                    btn.style.transition = 'transform 0.08s cubic-bezier(0.4, 0, 0.2, 1), filter 0.08s ease, box-shadow 0.08s ease';
                    if ({str(pressed).lower()}) {{
                        btn.style.transform = 'scale({scale})';
                        btn.style.filter = 'brightness(1.45)';
                        btn.style.boxShadow = '0 0 20px rgba(56, 189, 248, 0.9)';
                    }} else {{
                        btn.style.transform = '';
                        btn.style.filter = '';
                        btn.style.boxShadow = '';
                    }}
                }}
            }})();
            """
            try:
                web.eval(js)
            except Exception:
                pass

        # 3. Overview Study button
        elif (action_id in ("show_answer", "answer_ease_4")) and state == "overview":
            web = getattr(getattr(mw, "overview", None), "web", None)
            if not web:
                return
            js = f"""
            (function() {{
                let btn = document.getElementById('study') || document.querySelector('button.study-btn') || document.querySelector('button#study');
                if (btn) {{
                    btn.style.transition = 'transform 0.08s ease, filter 0.08s ease';
                    if ({str(pressed).lower()}) {{
                        btn.style.transform = 'scale({scale})';
                        btn.style.filter = 'brightness(1.45)';
                    }} else {{
                        btn.style.transform = '';
                        btn.style.filter = '';
                    }}
                }}
            }})();
            """
            try:
                web.eval(js)
            except Exception:
                pass

        # 4. DeckBrowser focused deck
        elif (action_id in ("show_answer", "answer_ease_4", "expand_subdecks")) and state == "deckBrowser":
            web = getattr(getattr(mw, "deckBrowser", None), "web", None)
            if not web:
                return
            js = f"""
            (function() {{
                let target = document.querySelector('tr.deck.gamepad-focused');
                if (target) {{
                    target.style.transition = 'transform 0.08s ease';
                    if ({str(pressed).lower()}) {{
                        target.style.transform = 'scale(0.97)';
                        target.style.filter = 'brightness(1.25)';
                    }} else {{
                        target.style.transform = '';
                        target.style.filter = '';
                    }}
                }}
            }})();
            """
            try:
                web.eval(js)
            except Exception:
                pass

    def execute_action(self, action_id: str) -> bool:
        """
        Executes the specific action safely according to Anki's current state.
        Returns True if an action was handled, preventing accidental chain execution.
        """
        if self.is_dialog_active:
            return False

        if not mw:
            return True

        state = getattr(mw, "state", "")
        is_in_review = (state == "review" and hasattr(mw, "reviewer") and mw.reviewer)

        # 1. Open Deck / Study Now / Show Answer (A / RT)
        if action_id == "show_answer":
            if state == "deckBrowser":
                if self.focus_zone == "topbar":
                    self.activate_topbar_button()
                else:
                    self.open_focused_deck()
                return True
            elif state == "overview":
                self.click_study_button()
                return True
            elif is_in_review:
                if mw.reviewer.state == "question":
                    if not self.trigger_on_release:
                        self.trigger_show_answer_visual_feedback()
                    self._last_state_transition_time = time.time()
                    mw.reviewer._showAnswer()
                    return True
                elif mw.reviewer.state == "answer":
                    # Enforce minimum cooldown after transition so a single press doesn't skip both
                    now = time.time()
                    if (now - self._last_state_transition_time) < self.state_transition_cooldown:
                        return True
                    if not self.trigger_on_release:
                        self.trigger_answer_visual_feedback(4)
                    mw.reviewer._answerCard(4)
                    return True

        # 2. Return Screen (B / Circle)
        elif action_id == "return_screen":
            if self.focus_zone == "topbar":
                self.focus_zone = "decks"
                self.clear_topbar_visual_focus()
                play_gamepad_sound("click")
                return True
            elif state == "overview":
                mw.moveToState("deckBrowser")
                return True
            elif is_in_review and mw.reviewer.state == "question":
                mw.moveToState("overview")
                return True

        # 3. Expand / Collapse Subdecks / Topbar Horizontal (X / Square / D-Pad)
        elif action_id == "expand_subdecks":
            if state == "deckBrowser":
                if self.focus_zone == "topbar":
                    self.navigate_topbar(1)
                else:
                    self.toggle_collapse_focused_deck()
                return True

        elif action_id == "dpad_left":
            if state == "deckBrowser":
                if self.focus_zone == "topbar":
                    self.navigate_topbar(-1)
                else:
                    self.toggle_collapse_focused_deck()
                return True

        elif action_id == "dpad_right":
            if state == "deckBrowser":
                if self.focus_zone == "topbar":
                    self.navigate_topbar(1)
                else:
                    self.toggle_collapse_focused_deck()
                return True

        # 4. Reviewer Answer Buttons (1..4)
        elif action_id in ("answer_ease_1", "answer_ease_2", "answer_ease_3", "answer_ease_4"):
            ease_map = {
                "answer_ease_1": 1,
                "answer_ease_2": 2,
                "answer_ease_3": 3,
                "answer_ease_4": 4,
            }
            ease = ease_map[action_id]

            if is_in_review and mw.reviewer.state == "answer":
                # Check cooldown to avoid rapid double-taps
                now = time.time()
                if (now - self._last_state_transition_time) < self.state_transition_cooldown:
                    return True
                if not self.trigger_on_release:
                    self.trigger_answer_visual_feedback(ease)
                mw.reviewer._answerCard(ease)
                return True
            elif state == "overview" and action_id == "answer_ease_3":
                # B in overview returns to deckBrowser
                mw.moveToState("deckBrowser")
                return True
            elif (state in ("deckBrowser", "overview")) and action_id == "answer_ease_4":
                # A in deckBrowser opens deck or activates topbar button, in overview studies
                if state == "deckBrowser":
                    if self.focus_zone == "topbar":
                        self.activate_topbar_button()
                    else:
                        self.open_focused_deck()
                else:
                    self.click_study_button()
                return True

        # 5. Undo
        elif action_id == "undo":
            if self.focus_zone == "topbar":
                self.focus_zone = "decks"
                self.clear_topbar_visual_focus()
                play_gamepad_sound("click")
                return True
            elif is_in_review:
                if hasattr(mw, "on_undo"):
                    mw.on_undo()
                elif hasattr(mw, "undo"):
                    mw.undo()
                return True
            elif state == "overview":
                mw.moveToState("deckBrowser")
                return True

        # 6. Audio actions
        elif action_id == "replay_audio":
            if is_in_review and hasattr(mw.reviewer, "replay_audio"):
                mw.reviewer.replay_audio()
                return True

        elif action_id == "pause_audio":
            try:
                if aqt and hasattr(aqt.sound, "av_player"):
                    aqt.sound.av_player.toggle_pause()
                    return True
            except Exception:
                pass

        # 7. Card flags & suspend
        elif action_id == "toggle_flag":
            if is_in_review and hasattr(mw.reviewer, "set_user_flag_for_current_card"):
                cur_flag = mw.reviewer.card.user_flag() if mw.reviewer.card else 0
                new_flag = 0 if cur_flag == 1 else 1
                mw.reviewer.set_user_flag_for_current_card(new_flag)
                return True

        elif action_id == "suspend_card":
            if is_in_review and hasattr(mw.reviewer, "suspend_card"):
                mw.reviewer.suspend_card()
                return True

        # 8. Up / Down Navigation
        elif action_id == "scroll_up":
            if state == "deckBrowser":
                self.navigate_deck_selection(-1)
            else:
                self.scroll_webview(-180)
            return True

        elif action_id == "scroll_down":
            if state == "deckBrowser":
                self.navigate_deck_selection(1)
            else:
                self.scroll_webview(180)
            return True

        elif action_id == "scroll_page_up":
            self.scroll_webview(-260)
            return True

        elif action_id == "scroll_page_down":
            self.scroll_webview(260)
            return True

        elif action_id == "scroll_page_left":
            self.scroll_horizontal_webview(-200)
            return True

        elif action_id == "scroll_page_right":
            self.scroll_horizontal_webview(200)
            return True

        # 9. Pomodoro Actions
        elif action_id == "pomo_toggle":
            try:
                try:
                    from ..pomodoro.hooks import get_pomodoro_engine, get_native_pomodoro_fab
                except (ImportError, ValueError):
                    from modules.pomodoro.hooks import get_pomodoro_engine, get_native_pomodoro_fab
                engine = get_pomodoro_engine()
                if engine:
                    engine.toggle_pause()
                    fab = get_native_pomodoro_fab()
                    if fab:
                        if not fab.isVisible():
                            fab.show()
                        fab.update_display()
                        fab.raise_()
                    play_gamepad_sound("click")
                    if tooltip:
                        st = tr("toast_pomo_started", "▶️ Pomodoro: Foco Iniciado") if engine.is_running else tr("toast_pomo_paused", "⏸️ Pomodoro: Pausado")
                        tooltip(st, period=1500)
                    return True
            except Exception as e:
                print(f"[Gamepad] Error executing pomo_toggle: {e}")
            return False

        elif action_id == "pomo_skip":
            try:
                try:
                    from ..pomodoro.hooks import get_pomodoro_engine, get_native_pomodoro_fab
                except (ImportError, ValueError):
                    from modules.pomodoro.hooks import get_pomodoro_engine, get_native_pomodoro_fab
                engine = get_pomodoro_engine()
                if engine:
                    engine.skip_to_break()
                    fab = get_native_pomodoro_fab()
                    if fab:
                        if not fab.isVisible():
                            fab.show()
                        fab.update_display()
                        fab.raise_()
                    play_gamepad_sound("click")
                    if tooltip:
                        tooltip(tr("toast_pomo_skipped", "⏩ Pomodoro: Pulado para Intervalo"), period=1500)
                    return True
            except Exception as e:
                print(f"[Gamepad] Error executing pomo_skip: {e}")
            return False

        elif action_id == "pomo_reset":
            try:
                try:
                    from ..pomodoro.hooks import get_pomodoro_engine, get_native_pomodoro_fab
                except (ImportError, ValueError):
                    from modules.pomodoro.hooks import get_pomodoro_engine, get_native_pomodoro_fab
                engine = get_pomodoro_engine()
                if engine:
                    engine.reset_current_phase()
                    fab = get_native_pomodoro_fab()
                    if fab:
                        if not fab.isVisible():
                            fab.show()
                        fab.update_display()
                        fab.raise_()
                    play_gamepad_sound("pop")
                    if tooltip:
                        tooltip(tr("toast_pomo_reset", "🔄 Pomodoro: Contador Reiniciado"), period=1500)
                    return True
            except Exception as e:
                print(f"[Gamepad] Error executing pomo_reset: {e}")
            return False

        elif action_id == "pomo_expand":
            try:
                try:
                    from ..pomodoro.hooks import get_native_pomodoro_fab
                except (ImportError, ValueError):
                    from modules.pomodoro.hooks import get_native_pomodoro_fab
                fab = get_native_pomodoro_fab()
                if fab and hasattr(fab, "toggle_expand"):
                    if not fab.isVisible():
                        fab.show()
                    fab.toggle_expand()
                    fab.raise_()
                    play_gamepad_sound("pop")
                    return True
            except Exception as e:
                print(f"[Gamepad] Error executing pomo_expand: {e}")
            return False

        elif action_id == "pomo_fullscreen":
            try:
                try:
                    from ..pomodoro.hooks import toggle_focus_fullscreen
                except (ImportError, ValueError):
                    from modules.pomodoro.hooks import toggle_focus_fullscreen
                toggle_focus_fullscreen()
                play_gamepad_sound("click")
                return True
            except Exception as e:
                print(f"[Gamepad] Error executing pomo_fullscreen: {e}")
            return False

        elif action_id == "open_settings":
            try:
                opened = False
                try:
                    from ... import show_unified_settings
                    show_unified_settings()
                    opened = True
                except Exception:
                    pass

                if not opened:
                    try:
                        from ..unified_config.settings_dialog import ObsidianSuiteHubDialog
                    except (ImportError, ValueError):
                        from modules.unified_config.settings_dialog import ObsidianSuiteHubDialog
                    if mw:
                        dialog = ObsidianSuiteHubDialog(mw)
                        dialog.exec()
                        opened = True

                if opened:
                    play_gamepad_sound("system")
                    return True
            except Exception as e:
                print(f"[Gamepad] Error executing open_settings: {e}")
            return False
        # 10. Direct Topbar & Navigation Actions
        elif action_id == "nav_decks":
            self.action_nav_decks()
            return True

        elif action_id == "nav_add":
            self.action_nav_add()
            return True

        elif action_id == "nav_browse":
            self.action_nav_browse()
            return True

        elif action_id == "nav_stats":
            self.action_nav_stats()
            return True

        elif action_id == "nav_sync":
            self.action_nav_sync()
            return True

        elif action_id == "topbar_toggle_focus":
            self.toggle_topbar_focus()
            return True

        return False

    def trigger_answer_visual_feedback(self, ease: int):
        """Simulates visual press/active animation on the on-screen answer button for immediate mode."""
        if not mw or not hasattr(mw, "reviewer") or not mw.reviewer:
            return
        bottom_web = getattr(mw.reviewer, "bottom", None)
        web = getattr(bottom_web, "web", None) if bottom_web else getattr(mw.reviewer, "web", None)
        if not web:
            return

        scale = self.get_contraction_scale()
        js = f"""
        (function() {{
            let btn = document.querySelector('button[data-ease="{ease}"]') 
                   || document.getElementById('ease{ease}')
                   || document.querySelector('table#middle td:nth-child({ease}) button')
                   || document.querySelectorAll('button')[{ease - 1}];
            if (btn) {{
                let origTrans = btn.style.transform;
                let origFilter = btn.style.filter;
                let origShadow = btn.style.boxShadow;
                btn.style.transition = 'transform 0.08s cubic-bezier(0.4, 0, 0.2, 1), filter 0.08s ease, box-shadow 0.08s ease';
                btn.style.transform = 'scale({scale})';
                btn.style.filter = 'brightness(1.55)';
                btn.style.boxShadow = '0 0 20px rgba(56, 189, 248, 0.95)';
                setTimeout(function() {{
                    btn.style.transform = origTrans;
                    btn.style.filter = origFilter;
                    btn.style.boxShadow = origShadow;
                }}, 150);
            }}
        }})();
        """
        try:
            web.eval(js)
        except Exception:
            pass

    def trigger_show_answer_visual_feedback(self):
        """Simulates visual press on the Show Answer button for immediate mode."""
        if not mw or not hasattr(mw, "reviewer") or not mw.reviewer:
            return
        bottom_web = getattr(mw.reviewer, "bottom", None)
        web = getattr(bottom_web, "web", None) if bottom_web else getattr(mw.reviewer, "web", None)
        if not web:
            return

        scale = self.get_contraction_scale()
        js = f"""
        (function() {{
            let btn = document.getElementById('ansbut') 
                   || document.querySelector('#ansbut button')
                   || document.querySelector('button');
            if (btn) {{
                let origTrans = btn.style.transform;
                let origFilter = btn.style.filter;
                btn.style.transition = 'transform 0.08s cubic-bezier(0.4, 0, 0.2, 1), filter 0.08s ease';
                btn.style.transform = 'scale({scale})';
                btn.style.filter = 'brightness(1.45)';
                btn.style.boxShadow = '0 0 18px rgba(56, 189, 248, 0.9)';
                setTimeout(function() {{
                    btn.style.transform = origTrans;
                    btn.style.filter = origFilter;
                    btn.style.boxShadow = '';
                }}, 140);
            }}
        }})();
        """
        try:
            web.eval(js)
        except Exception:
            pass

    def ascend_to_topbar(self):
        """Ascends focus from deck list to the top toolbar."""
        self.focus_zone = "topbar"
        self.topbar_index = 0
        self.clear_deck_selection()
        self.update_topbar_visual_focus()
        play_gamepad_sound("click")

    def descend_from_topbar(self):
        """Descends focus from topbar back into the first deck in the deck list."""
        self.focus_zone = "decks"
        self.focused_deck_index = 0
        self.clear_topbar_visual_focus()
        self.navigate_deck_selection(0, from_topbar=True)
        play_gamepad_sound("click")

    def sync_deck_focus(self, index: int, deck_id: str):
        """Synchronizes Python dispatcher state with the active DOM deck focus."""
        self.focus_zone = "decks"
        self.focused_deck_index = index
        self.last_focused_deck_id = deck_id

    def navigate_deck_selection(self, delta: int, from_topbar: bool = False):
        """Moves focus outline to previous or next visible deck in DeckBrowser with auto-scroll, or ascends to topbar."""
        if not mw or mw.state != "deckBrowser" or not hasattr(mw, "deckBrowser") or not mw.deckBrowser.web:
            return

        # 1. If currently in topbar zone: Down returns to deck list!
        if self.focus_zone == "topbar":
            if delta > 0:
                self.focus_zone = "decks"
                self.focused_deck_index = 0
                self.clear_topbar_visual_focus()
                play_gamepad_sound("click")
                from_topbar = True
            else:
                return

        # Note: We do NOT use a premature check on self.focused_deck_index == 0 here,
        # because only the DOM knows the true position of the focused deck (e.g. after
        # returning from overview or expanding subdecks). The JavaScript evaluation below
        # checks if curIdx === 0 && delta < 0 and triggers ascend_to_topbar via pycmd.

        from_topbar_js = "true" if from_topbar else "false"

        js = f"""
        (function() {{
            let style = document.getElementById('gamepad-deck-focus-style');
            if (!style) {{
                style = document.createElement('style');
                style.id = 'gamepad-deck-focus-style';
                style.innerHTML = `
                    tr.deck.gamepad-focused {{
                        outline: 2px solid #38bdf8 !important;
                        background: rgba(56, 189, 248, 0.18) !important;
                        border-radius: 6px !important;
                        box-shadow: 0 0 14px rgba(56, 189, 248, 0.4) !important;
                        transition: all 0.15s ease !important;
                    }}
                `;
                document.head.appendChild(style);
            }}

            let decks = Array.from(document.querySelectorAll('tr.deck'));
            if (!decks.length) return;

            let fromTopbar = {from_topbar_js};
            let savedDeckId = sessionStorage.getItem('gamepad_focused_deck_id');
            let curIdx = decks.findIndex(el => el.classList.contains('gamepad-focused'));

            if (curIdx === -1 && savedDeckId && !fromTopbar) {{
                let el = document.getElementById(savedDeckId) || decks.find(d => d.id === savedDeckId);
                if (el) {{
                    curIdx = decks.indexOf(el);
                }}
            }}

            // Moving UP from the 1st deck ascends to TopBar!
            if (curIdx === 0 && {delta} < 0 && !fromTopbar) {{
                try {{
                    if (typeof pycmd === "function") {{
                        pycmd("gamepad_ascend_topbar");
                    }} else if (typeof window.pycmd === "function") {{
                        window.pycmd("gamepad_ascend_topbar");
                    }} else if (typeof bridgeCommand === "function") {{
                        bridgeCommand("gamepad_ascend_topbar");
                    }}
                }} catch(e) {{}}
                return;
            }}

            if (curIdx !== -1 && curIdx < decks.length) {{
                decks[curIdx].classList.remove('gamepad-focused');
            }}

            let nextIdx;
            if (fromTopbar) {{
                nextIdx = 0;
            }} else if (curIdx === -1) {{
                nextIdx = ({delta} > 0) ? 0 : decks.length - 1;
            }} else {{
                nextIdx = curIdx + ({delta});
            }}

            nextIdx = Math.max(0, Math.min(decks.length - 1, nextIdx));

            let target = decks[nextIdx];
            if (target) {{
                target.classList.add('gamepad-focused');
                if (target.id) {{
                    sessionStorage.setItem('gamepad_focused_deck_id', target.id);
                }}
                target.scrollIntoView({{ block: 'nearest', behavior: 'smooth' }});

                try {{
                    let deckId = target.id || '';
                    if (typeof pycmd === "function") {{
                        pycmd("gamepad_deck_focused:" + nextIdx + ":" + deckId);
                    }} else if (typeof window.pycmd === "function") {{
                        window.pycmd("gamepad_deck_focused:" + nextIdx + ":" + deckId);
                    }}
                }} catch(e) {{}}
            }}
        }})();
        """
        try:
            mw.deckBrowser.web.eval(js)
        except Exception:
            pass

    def update_topbar_visual_focus(self):
        """Highlights the selected topbar button in mw.toolbar.web with glowing halo."""
        if not mw or not hasattr(mw, "toolbar") or not mw.toolbar or not hasattr(mw.toolbar, "web") or not mw.toolbar.web:
            return

        js = f"""
        (function() {{
            let style = document.getElementById('gamepad-topbar-focus-style');
            if (!style) {{
                style = document.createElement('style');
                style.id = 'gamepad-topbar-focus-style';
                style.innerHTML = `
                    .topbar-gamepad-focused {{
                        outline: 2px solid #38bdf8 !important;
                        outline-offset: 2px !important;
                        box-shadow: 0 0 14px rgba(56, 189, 248, 0.65) !important;
                        border-radius: 6px !important;
                        transform: scale(1.05) !important;
                        transition: all 0.15s ease !important;
                    }}
                `;
                document.head.appendChild(style);
            }}

            let allCandidates = Array.from(document.querySelectorAll('.topbut, a.linkb, button.linkb, a, button'));
            let validButtons = allCandidates.filter(el => {{
                let txt = (el.textContent || '').trim().toLowerCase();
                let clk = (el.getAttribute('onclick') || '').toLowerCase();
                let href = (el.getAttribute('href') || '').toLowerCase();
                let id = (el.id || '').toLowerCase();
                return clk.includes('decks') || clk.includes('add') || clk.includes('browse') || clk.includes('stats') || clk.includes('sync') ||
                       id === 'decks' || id === 'add' || id === 'browse' || id === 'stats' || id === 'sync' ||
                       txt.includes('baralho') || txt.includes('deck') ||
                       txt.includes('adicionar') || txt.includes('add') ||
                       txt.includes('painel') || txt.includes('browse') ||
                       txt.includes('estat') || txt.includes('stat') ||
                       txt.includes('sinc') || txt.includes('sync');
            }});

            document.querySelectorAll('.topbar-gamepad-focused').forEach(el => {{
                el.classList.remove('topbar-gamepad-focused');
            }});

            let idx = {self.topbar_index};
            if (idx >= 0 && idx < validButtons.length) {{
                validButtons[idx].classList.add('topbar-gamepad-focused');
            }}
        }})();
        """
        try:
            mw.toolbar.web.eval(js)
        except Exception:
            pass

    def clear_topbar_visual_focus(self):
        """Clears highlight outline from mw.toolbar.web."""
        if not mw or not hasattr(mw, "toolbar") or not mw.toolbar or not hasattr(mw.toolbar, "web") or not mw.toolbar.web:
            return
        js = """
        (function() {
            document.querySelectorAll('.topbar-gamepad-focused').forEach(el => {
                el.classList.remove('topbar-gamepad-focused');
            });
        })();
        """
        try:
            mw.toolbar.web.eval(js)
        except Exception:
            pass

    def clear_deck_selection(self):
        """Clears highlight outline from deck list in mw.deckBrowser.web."""
        if not mw or not hasattr(mw, "deckBrowser") or not mw.deckBrowser or not mw.deckBrowser.web:
            return
        js = """
        (function() {
            document.querySelectorAll('tr.deck.gamepad-focused').forEach(el => {
                el.classList.remove('gamepad-focused');
            });
        })();
        """
        try:
            mw.deckBrowser.web.eval(js)
        except Exception:
            pass

    def navigate_topbar(self, delta: int):
        """Navigates sequentially across the 5 topbar buttons (0: Baralhos, 1: Adicionar, 2: Painel, 3: Estatísticas, 4: Sincronizar)."""
        if self.focus_zone != "topbar":
            self.focus_zone = "topbar"
            self.topbar_index = 0
            self.clear_deck_selection()
        else:
            self.topbar_index = max(0, min(4, self.topbar_index + delta))
        self.update_topbar_visual_focus()
        play_gamepad_sound("click")

    def toggle_topbar_focus(self):
        """Toggles focus between deck list and top toolbar."""
        if self.focus_zone == "topbar":
            self.descend_from_topbar()
        else:
            self.ascend_to_topbar()

    def activate_topbar_button(self):
        """Activates the currently focused topbar button."""
        play_gamepad_sound("click")
        idx = self.topbar_index
        if idx == 0:
            self.action_nav_decks()
        elif idx == 1:
            self.action_nav_add()
        elif idx == 2:
            self.action_nav_browse()
        elif idx == 3:
            self.action_nav_stats()
        elif idx == 4:
            self.action_nav_sync()

    def action_nav_decks(self):
        """Navigates to DeckBrowser (Baralhos)."""
        if not mw:
            return
        play_gamepad_sound("system")
        mw.moveToState("deckBrowser")
        self.focus_zone = "decks"
        self.focused_deck_index = 0
        self.clear_topbar_visual_focus()

    def action_nav_add(self):
        """Opens Add Cards dialog (Adicionar)."""
        if not mw:
            return
        play_gamepad_sound("system")
        if hasattr(mw, "onAddCard"):
            mw.onAddCard()

    def action_nav_browse(self):
        """Opens Card Browser (Painel)."""
        if not mw:
            return
        play_gamepad_sound("system")
        if hasattr(mw, "onBrowse"):
            mw.onBrowse()

    def action_nav_stats(self):
        """Opens Statistics screen (Estatísticas)."""
        if not mw:
            return
        play_gamepad_sound("system")
        if hasattr(mw, "onStats"):
            mw.onStats()

    def action_nav_sync(self):
        """Triggers Sync (Sincronizar)."""
        if not mw:
            return
        play_gamepad_sound("system")
        if hasattr(mw, "on_sync"):
            mw.on_sync()
        elif hasattr(mw, "onSync"):
            mw.onSync()
        elif hasattr(mw, "sync"):
            mw.sync()

    def open_focused_deck(self):
        """Clicks the focused deck with visual press animation."""
        if not mw or mw.state != "deckBrowser" or not hasattr(mw, "deckBrowser") or not mw.deckBrowser.web:
            return

        js = """
        (function() {
            let target = document.querySelector('tr.deck.gamepad-focused');
            if (!target) {
                let savedDeckId = sessionStorage.getItem('gamepad_focused_deck_id');
                if (savedDeckId) {
                    target = document.getElementById(savedDeckId) || document.querySelector('tr.deck[id="' + savedDeckId + '"]');
                }
                if (!target) {
                    target = document.querySelector('tr.deck');
                }
                if (target) target.classList.add('gamepad-focused');
            }
            if (target) {
                let deckId = target.id || '';
                if (deckId) {
                    sessionStorage.setItem('gamepad_focused_deck_id', deckId);
                }
                try {
                    let decks = Array.from(document.querySelectorAll('tr.deck'));
                    let idx = decks.indexOf(target);
                    if (typeof pycmd === "function") {
                        pycmd("gamepad_deck_focused:" + idx + ":" + deckId);
                    } else if (typeof window.pycmd === "function") {
                        window.pycmd("gamepad_deck_focused:" + idx + ":" + deckId);
                    }
                } catch(e) {}
                target.style.transition = 'transform 0.08s ease';
                target.style.transform = 'scale(0.97)';
                setTimeout(function() {
                    target.style.transform = '';
                    let link = target.querySelector('a.deck');
                    if (link) {
                        link.click();
                        return;
                    }
                    let openBtn = target.querySelector('[onclick*="open:"]');
                    if (openBtn) openBtn.click();
                }, 90);
            }
        })();
        """
        try:
            mw.deckBrowser.web.eval(js)
        except Exception:
            pass

    def click_study_button(self):
        """Clicks the Study Now button in Overview screen with visual button feedback."""
        if not mw or mw.state != "overview" or not hasattr(mw, "overview") or not mw.overview.web:
            return

        js = """
        (function() {
            let btn = document.getElementById('study') 
                   || document.querySelector('button.study-btn') 
                   || document.querySelector('button#study');
            if (btn) {
                btn.style.transition = 'transform 0.08s ease, filter 0.08s ease';
                btn.style.transform = 'scale(0.85)';
                btn.style.filter = 'brightness(1.4)';
                setTimeout(function() {
                    btn.style.transform = '';
                    btn.style.filter = '';
                    btn.click();
                }, 100);
            }
        })();
        """
        try:
            mw.overview.web.eval(js)
        except Exception:
            pass

    def toggle_collapse_focused_deck(self):
        """Toggles subdecks collapse arrow for the focused deck in DeckBrowser."""
        if not mw or mw.state != "deckBrowser" or not hasattr(mw, "deckBrowser") or not mw.deckBrowser.web:
            return

        js = """
        (function() {
            let style = document.getElementById('gamepad-deck-focus-style');
            if (!style) {
                style = document.createElement('style');
                style.id = 'gamepad-deck-focus-style';
                style.innerHTML = `
                    tr.deck.gamepad-focused {
                        outline: 2px solid #38bdf8 !important;
                        background: rgba(56, 189, 248, 0.18) !important;
                        border-radius: 6px !important;
                        box-shadow: 0 0 14px rgba(56, 189, 248, 0.4) !important;
                        transition: all 0.15s ease !important;
                    }
                `;
                document.head.appendChild(style);
            }

            let target = document.querySelector('tr.deck.gamepad-focused') || document.querySelector('tr.deck');
            if (!target) return;

            let deckId = target.id || '';
            if (deckId) {
                sessionStorage.setItem('gamepad_focused_deck_id', deckId);
            }

            let collapseBtn = target.querySelector('a.collapse') || target.querySelector('[onclick*="collapse:"]');
            if (collapseBtn) {
                collapseBtn.click();
            }

            if (deckId) {
                let restoreFocus = function() {
                    let el = document.getElementById(deckId) || document.querySelector('tr.deck[id="' + deckId + '"]');
                    if (el) {
                        document.querySelectorAll('tr.deck.gamepad-focused').forEach(function(d) {
                            d.classList.remove('gamepad-focused');
                        });
                        el.classList.add('gamepad-focused');
                        el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                    }
                };
                setTimeout(restoreFocus, 50);
                setTimeout(restoreFocus, 150);
            }
        })();
        """
        try:
            mw.deckBrowser.web.eval(js)
        except Exception:
            pass

    def scroll_webview(self, pixel_delta: float):
        """Scrolls the active window or active settings dialog smoothly."""
        keep_system_and_pomodoro_active()
        if self.is_dialog_active:
            if self.active_dialog_scroll:
                try:
                    sb = self.active_dialog_scroll.verticalScrollBar()
                    sb.setValue(sb.value() + int(pixel_delta))
                except Exception:
                    pass
            return

        web = self._get_active_web()
        if not web:
            return
        try:
            web.eval(f"window.scrollBy({{top: {pixel_delta:.1f}, behavior: 'smooth'}});")
        except Exception:
            pass

    def scroll_horizontal_webview(self, pixel_delta: float):
        """Scrolls the active window horizontally."""
        keep_system_and_pomodoro_active()
        if self.is_dialog_active:
            if self.active_dialog_scroll:
                try:
                    sb = self.active_dialog_scroll.horizontalScrollBar()
                    sb.setValue(sb.value() + int(pixel_delta))
                except Exception:
                    pass
            return

        web = self._get_active_web()
        if not web:
            return
        try:
            web.eval(f"window.scrollBy({{left: {pixel_delta:.1f}, behavior: 'smooth'}});")
        except Exception:
            pass

    def continuous_scroll_webview(self, pixel_delta: float):
        """Scrolls the active window or active settings dialog continuously during stick movement."""
        keep_system_and_pomodoro_active()
        if self.is_dialog_active:
            if self.active_dialog_scroll:
                try:
                    sb = self.active_dialog_scroll.verticalScrollBar()
                    sb.setValue(sb.value() + int(pixel_delta))
                except Exception:
                    pass
            return

        web = self._get_active_web()
        if not web:
            return
        try:
            web.eval(f"window.scrollBy({{top: {pixel_delta:.1f}, behavior: 'auto'}});")
        except Exception:
            pass


def set_active_dialog(dialog: Optional[Any]):
    """Module-level helper to set active dialog on the global GamepadActionDispatcher."""
    try:
        from .hooks import get_gamepad_dispatcher
    except (ImportError, ValueError):
        try:
            from modules.gamepad.hooks import get_gamepad_dispatcher
        except (ImportError, ValueError):
            get_gamepad_dispatcher = None
    if get_gamepad_dispatcher:
        disp = get_gamepad_dispatcher()
        if disp:
            disp.set_active_dialog(dialog)


def get_active_dialog() -> Optional[Any]:
    """Module-level helper to get active dialog from the global GamepadActionDispatcher."""
    try:
        from .hooks import get_gamepad_dispatcher
    except (ImportError, ValueError):
        try:
            from modules.gamepad.hooks import get_gamepad_dispatcher
        except (ImportError, ValueError):
            get_gamepad_dispatcher = None
    if get_gamepad_dispatcher:
        disp = get_gamepad_dispatcher()
        if disp:
            return disp.get_active_dialog()
    return None
