# -*- coding: utf-8 -*-
"""
Multiple Choice for Anki integrated module.
"""

from .template import (
    manage_multiple_choice_note_type,
    update_multiple_choice_note_type_from_config,
)

def setup_multiple_choice():
    """Initializes the multiple choice note type and hooks."""
    try:
        manage_multiple_choice_note_type()
    except Exception as e:
        print(f"Error initializing multiple choice: {e}")

__all__ = [
    "manage_multiple_choice_note_type",
    "update_multiple_choice_note_type_from_config",
    "setup_multiple_choice",
]
