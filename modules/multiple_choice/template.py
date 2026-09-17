# -*- coding: utf-8 -*-
"""
Manages note type and card templates for Multiple Choice for Anki.
"""

import os
import re
from enum import Enum
from typing import Any

from anki.consts import MODEL_STD
from aqt import mw

from .config import get_mc_config, getSyncedConfig, getLocalConfig, updateSyncedConfig, updateLocalConfig
from .packaging import version

aio_model_name = "AllInOne (kprim, mc, sc)"
aio_card = "AllInOne (kprim, mc, sc)"
aio_fields = {
    "question": "Question",
    "title": "Title",
    "qtype": "QType (0=kprim,1=mc,2=sc)",
    "q1": "Q_1",
    "q2": "Q_2",
    "q3": "Q_3",
    "q4": "Q_4",
    "q5": "Q_5",
    "answers": "Answers",
    "sources": "Sources",
    "extra": "Extra 1",
}

QUESTION_ID_PATTERN = r"^Q_(\d+)$"
DEFAULT_NUMBER_OF_QUESTIONS = 5


class Template_side(Enum):
    FRONT = 1
    BACK = 2


def get_card_folder() -> str:
    return os.path.join(os.path.dirname(__file__), "card")


def get_default_front_template_text() -> str:
    path = os.path.join(get_card_folder(), "front.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_default_back_template_text() -> str:
    path = os.path.join(get_card_folder(), "back.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_default_css_template_text() -> str:
    path = os.path.join(get_card_folder(), "css.css")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def getOptionsJavaScriptFromConfig(user_config, side: Template_side) -> str:
    max_q = user_config.get("maxQuestionsToShow", 5)
    color_q = "true" if user_config.get("colorQuestionTable", False) else "false"
    color_a = "true" if user_config.get("colorAnswerTable", True) else "false"
    hide_a = "false" if user_config.get("hideAnswerTable", False) else "true"
    answer_col = user_config.get("answerColoring", {})

    user_config_front_options_javascript = (
        f"const OPTIONS = {{\n"
        f"    maxQuestionsToShow: {max_q}\n"
        f"}};\n"
    )

    user_config_back_options_javascript = (
        f"const OPTIONS = {{\n"
        f"    qtable: {{\n"
        f"        visible: true,\n"
        f"        colorize: {color_q},\n"
        f"        colors: {answer_col}\n"
        f"    }},\n"
        f"    atable: {{\n"
        f"        visible: {hide_a},\n"
        f"        colorize: {color_a},\n"
        f"        colors: {answer_col}\n"
        f"    }}\n"
        f"}};\n"
    )

    return (
        user_config_front_options_javascript
        if side == Template_side.FRONT
        else user_config_back_options_javascript
    )


def fillTemplateAndModelFromFile(model, user_config=None):
    if user_config:
        front_opts = getOptionsJavaScriptFromConfig(user_config, Template_side.FRONT)
        back_opts = getOptionsJavaScriptFromConfig(user_config, Template_side.BACK)

    front_template = get_default_front_template_text()
    if user_config:
        front_template = re.sub(r"const OPTIONS.*?;", front_opts, front_template, 1, re.DOTALL)
    model["tmpls"][0]["qfmt"] = front_template

    back_template = get_default_back_template_text()
    if user_config:
        back_template = re.sub(r"const OPTIONS.*?;", back_opts, back_template, 1, re.DOTALL)
    model["tmpls"][0]["afmt"] = back_template
    model["css"] = get_default_css_template_text()


def manage_multiple_choice_note_type():
    if not mw or not mw.col:
        return
    try:
        model = mw.col.models.by_name(aio_model_name)
        user_config = get_mc_config()

        if model is None:
            # Create model
            models = mw.col.models
            model = models.new(aio_model_name)
            model["type"] = MODEL_STD

            for f_key in ["question", "title", "qtype", "q1", "q2", "q3", "q4", "q5", "answers", "sources", "extra"]:
                f_name = aio_fields[f_key]
                field = models.new_field(f_name)
                models.add_field(model, field)

            template = models.new_template(aio_card)
            models.add_template(model, template)
            fillTemplateAndModelFromFile(model, user_config)
            models.add(model)
        else:
            # Model exists, check version updates
            synced_config = getSyncedConfig()
            if synced_config and version.parse(synced_config.get("version", "1.0.0")) < version.parse("2.10.3"):
                updateSyncedConfig()
                updateLocalConfig()
                fillTemplateAndModelFromFile(model, user_config)
                mw.col.models.save(model)
    except Exception as e:
        print(f"Multiple Choice initialization note: {e}")


def update_multiple_choice_note_type_from_config():
    if not mw or not mw.col:
        return
    model = mw.col.models.by_name(aio_model_name)
    if model:
        user_config = get_mc_config()
        fillTemplateAndModelFromFile(model, user_config)
        mw.col.models.save(model)
