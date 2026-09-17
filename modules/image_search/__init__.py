# -*- coding: utf-8 -*-
"""
Web Image Search & Downloader integration for Anki's Card Editor.
Adds a toolbar button to the card editor, allowing users to search, preview with zoom,
download, and insert images directly at the current cursor position.
"""

import os
from typing import Optional

try:
    from aqt import mw, gui_hooks
except ImportError:
    mw = None
    gui_hooks = None

try:
    from ...utils.i18n import tr
    from ...utils.config_manager import get_module_config
except (ImportError, ValueError):
    from utils.i18n import tr
    from utils.config_manager import get_module_config

from .ui.search_dialog import ImageSearchDialog


def get_selected_text_from_editor(editor) -> str:
    """Attempts to retrieve the currently selected text in the active field."""
    try:
        if hasattr(editor, "web") and editor.web:
            page = editor.web.page()
            if page and hasattr(page, "selectedText"):
                txt = page.selectedText().strip()
                if txt:
                    return txt
    except Exception:
        pass
    return ""


def insert_image_into_editor(editor, data: bytes, ext: str, query: str, target_idx: Optional[int] = None):
    """
    Saves image into Anki's collection media directory and injects HTML img tag
    into the editor's active field. Guarantees UI update via loadNote and note saving.
    """
    if not editor:
        return

    import re
    import time

    clean_q = re.sub(r"[^a-zA-Z0-9_-]", "_", query).strip("_")[:24] or "img"
    timestamp = int(time.time())
    desired_name = f"obsidian_{clean_q}_{timestamp}{ext}"

    # 1. Save data into Anki's media collection
    try:
        if hasattr(editor, "mw") and editor.mw and hasattr(editor.mw, "col") and editor.mw.col:
            media_filename = editor.mw.col.media.write_data(desired_name, data)
        else:
            media_filename = desired_name
    except Exception as e:
        print(f"[ImageSearch] Error writing media data: {e}")
        media_filename = desired_name

    # Properly escape filename for HTML img tag according to Anki standards
    img_tag = f'<img src="{media_filename}">'
    try:
        if hasattr(editor, "mw") and editor.mw and hasattr(editor.mw, "col") and editor.mw.col:
            if hasattr(editor.mw.col, "media") and hasattr(editor.mw.col.media, "escape_media_filenames"):
                escaped = editor.mw.col.media.escape_media_filenames(img_tag)
                if isinstance(escaped, str):
                    img_tag = escaped
    except Exception:
        pass

    # 2. Reactivate editor parent window and webview
    parent_window = getattr(editor, "parentWindow", None) or getattr(editor, "widget", None) or mw
    if parent_window and hasattr(parent_window, "activateWindow"):
        try:
            parent_window.activateWindow()
        except Exception:
            pass

    if hasattr(editor, "web") and editor.web:
        if hasattr(editor.web, "setFocus"):
            try:
                editor.web.setFocus()
            except Exception:
                pass

    # 3. Resolve target field index
    if target_idx is None or target_idx < 0:
        target_idx = getattr(editor, "currentField", None)
    if target_idx is None:
        target_idx = getattr(editor, "last_field_index", 0)
    if target_idx is None:
        target_idx = 0

    # Ensure field is focused in webview
    if hasattr(editor, "web") and editor.web:
        try:
            editor.web.eval(f"focusField({target_idx});")
        except Exception:
            pass

    # 4. Insert into note.fields and trigger loadNote
    if hasattr(editor, "note") and editor.note and hasattr(editor.note, "fields"):
        try:
            fields = editor.note.fields
            if 0 <= target_idx < len(fields):
                current_text = fields[target_idx]
                if current_text and current_text.strip():
                    if img_tag not in current_text:
                        fields[target_idx] = f"{current_text}<br>{img_tag}"
                else:
                    fields[target_idx] = img_tag

                # Call Anki's canonical loadNote method to refresh the UI and set focus
                if hasattr(editor, "loadNote"):
                    editor.loadNote(focusTo=target_idx)

                # If not in Add Cards mode (e.g. Browser or Review edit), save note to DB
                if not getattr(editor, "addMode", True):
                    if hasattr(editor, "_save_current_note"):
                        editor._save_current_note()
                    elif hasattr(editor, "saveNow"):
                        editor.saveNow(lambda: None)
        except Exception as e:
            print(f"[ImageSearch] Error updating note fields: {e}")

    # 5. Also call doPaste if available as legacy/test fallback
    if hasattr(editor, "doPaste"):
        try:
            editor.doPaste(img_tag, internal=False)
        except Exception:
            pass


def open_image_search_for_editor(editor):
    """Opens the Image Search Dialog attached to the card editor."""
    if not editor:
        return

    # Check config
    cfg = get_module_config("image_search")
    if cfg and not cfg.get("enabled", True):
        return

    saved_field = getattr(editor, "currentField", None)
    if saved_field is None:
        saved_field = getattr(editor, "last_field_index", 0)
    if saved_field is None:
        saved_field = 0

    # Flush any pending edits and save selection range before opening modal dialog
    if hasattr(editor, "web") and editor.web:
        try:
            editor.web.eval(
                "try { if (typeof saveNow === 'function') { saveNow(true); } } catch(e){};"
                "try { window._obsidian_saved_range = (window.getSelection && window.getSelection().rangeCount > 0) ? "
                "window.getSelection().getRangeAt(0).cloneRange() : null; } catch(e){}"
            )
        except Exception:
            pass

    selected_text = get_selected_text_from_editor(editor)

    parent_window = getattr(editor, "parentWindow", None) or getattr(editor, "widget", None) or mw
    dialog = ImageSearchDialog(
        parent=parent_window,
        editor=editor,
        initial_query=selected_text,
        saved_field_index=saved_field,
    )

    pomodoro_engine = None
    try:
        try:
            from ..pomodoro.timer_engine import get_pomodoro_engine
        except (ImportError, ValueError):
            from modules.pomodoro.timer_engine import get_pomodoro_engine
        pomodoro_engine = get_pomodoro_engine()
        if pomodoro_engine and pomodoro_engine.is_running and getattr(pomodoro_engine.state, "value", "") == "work":
            if hasattr(pomodoro_engine, "pause_for_editing"):
                pomodoro_engine.pause_for_editing(source="image_search")
    except Exception:
        pass

    try:
        dialog.exec()
    finally:
        if pomodoro_engine and getattr(pomodoro_engine, "is_paused_by_editing", False):
            if hasattr(pomodoro_engine, "resume_from_editing"):
                pomodoro_engine.resume_from_editing(source="image_search")

    # Once dialog is closed and destroyed, execute insertion if downloaded data exists and not yet inserted
    if getattr(dialog, "downloaded_data", None) and not getattr(dialog, "_inserted", False):
        dialog._inserted = True
        data, ext, query = dialog.downloaded_data
        insert_image_into_editor(editor, data, ext, query, saved_field)


def on_editor_did_init_buttons(buttons: list, editor):
    """
    Hook handler for Anki's gui_hooks.editor_did_init_buttons.
    Adds the Image Search button to the editor toolbar.
    """
    cfg = get_module_config("image_search")
    if cfg and not cfg.get("enabled", True):
        return

    addon_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    icon_path = os.path.join(addon_dir, "assets", "icons", "image_search.png")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(addon_dir, "assets", "icons", "image_search.svg")

    shortcut_key = cfg.get("shortcut", "Ctrl+Shift+I") if cfg else "Ctrl+Shift+I"
    tip = f"{tr('image_search_tooltip', 'Pesquisar e Inserir Imagens da Web')} ({shortcut_key})"

    try:
        btn = editor.addButton(
            icon=icon_path if os.path.exists(icon_path) else None,
            cmd="obsidian_image_search",
            func=open_image_search_for_editor,
            tip=tip,
            label="🖼️" if not os.path.exists(icon_path) else "",
            id="obsidian_image_search_btn",
            keys=shortcut_key,
        )
        buttons.append(btn)
    except Exception as e:
        print(f"[Obsidian Addon] Failed to register image search button: {e}")


def setup_image_search_hooks():
    """Registers editor toolbar hooks with Anki."""
    if not gui_hooks:
        return

    try:
        gui_hooks.editor_did_init_buttons.append(on_editor_did_init_buttons)
    except Exception as e:
        print(f"[Obsidian Addon] Error setting up image search hooks: {e}")
