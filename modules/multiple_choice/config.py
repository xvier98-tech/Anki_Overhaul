# -*- coding: utf-8 -*-
"""
Configuration helper for Multiple Choice for Anki.
"""

from typing import Dict, Any

try:
    from aqt import mw
except ImportError:
    mw = None

try:
    from ...utils.config_manager import get_module_config, write_module_config
except (ImportError, ValueError):
    from utils.config_manager import get_module_config, write_module_config

DEFAULT_MC_CONFIG: Dict[str, Any] = {
    "maxQuestionsToShow": 5,
    "colorQuestionTable": False,
    "colorAnswerTable": True,
    "hideAnswerTable": False,
    "answerColoring": {
        "correctColor": "#27ae60",
        "incorrectColor": "#c0392b",
    },
}

default_conf_local = {"version": "2.10.3"}
default_conf_syncd = {"version": "2.10.3"}


def get_mc_config() -> Dict[str, Any]:
    return get_module_config("multiple_choice")


def write_mc_config(conf: Dict[str, Any]) -> None:
    write_module_config("multiple_choice", conf)


def getSyncedConfig():
    if not mw or not mw.col:
        return default_conf_syncd
    if mw.col.get_config("mc_conf") is None:
        mw.col.set_config("mc_conf", default_conf_syncd)
    return mw.col.get_config("mc_conf")


def updateSyncedConfig():
    if not mw or not mw.col:
        return
    tmp_conf = mw.col.get_config("mc_conf") or {}
    for key in list(default_conf_syncd.keys()):
        if key not in tmp_conf:
            tmp_conf[key] = default_conf_syncd[key]
    tmp_conf["version"] = default_conf_syncd["version"]
    mw.col.set_config("mc_conf", tmp_conf)


def getLocalConfig():
    if not mw:
        return default_conf_local
    if "mc_conf" not in mw.pm.profile:
        mw.pm.profile["mc_conf"] = default_conf_local
    return mw.pm.profile["mc_conf"]


def updateLocalConfig():
    if not mw:
        return
    if "mc_conf" not in mw.pm.profile:
        mw.pm.profile["mc_conf"] = default_conf_local
    for key in list(default_conf_local.keys()):
        if key not in mw.pm.profile["mc_conf"]:
            mw.pm.profile["mc_conf"][key] = default_conf_local[key]
    mw.pm.profile["mc_conf"]["version"] = default_conf_local["version"]
