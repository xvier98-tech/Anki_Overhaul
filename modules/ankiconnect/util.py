# -*- coding: utf-8 -*-
"""
AnkiConnect utilities and settings helper.
"""

import os
import sys
import enum
import itertools

try:
    import aqt
    version_string = getattr(aqt, "appVersion", "24.0.0")
    for suffix in ["b", "rc"]:
        version_string = version_string.replace(suffix, ".")
    anki_version = tuple(int(segment) for segment in version_string.split(".") if segment.isdigit())
except Exception:
    anki_version = (24, 0, 0)

try:
    from ...utils.config_manager import get_module_config
except (ImportError, ValueError):
    from utils.config_manager import get_module_config

class MediaType(enum.Enum):
    Audio = 1
    Video = 2
    Picture = 3


DEFAULT_CONFIG = {
    'apiKey': None,
    'apiLogPath': None,
    'apiPollInterval': 25,
    'apiVersion': 6,
    'webBacklog': 5,
    'webBindAddress': os.getenv('ANKICONNECT_BIND_ADDRESS', '127.0.0.1'),
    'webBindPort': 8765,
    'webCorsOrigin': os.getenv('ANKICONNECT_CORS_ORIGIN', None),
    'webCorsOriginList': ['http://localhost', 'app://obsidian.md'],
    'ignoreOriginList': [],
    'webTimeout': 10000,
}


def setting(key):
    try:
        cfg = get_module_config("ankiconnect")
        return cfg.get(key, DEFAULT_CONFIG.get(key))
    except Exception:
        return DEFAULT_CONFIG.get(key)


def download(url):
    if not anki:
        return None
    client = anki.sync.AnkiRequestsClient()
    client.timeout = setting('webTimeout') / 1000
    resp = client.get(url)
    if resp.status_code != 200:
        raise Exception('{} download failed with return code {}'.format(url, resp.status_code))
    return client.streamContent(resp)


def api(*versions):
    def decorator(func):
        setattr(func, 'versions', versions)
        setattr(func, 'api', True)
        return func
    return decorator


def cardQuestion(card):
    if getattr(card, 'question', None) is None:
        return card._getQA()['q']
    return card.question()


def cardAnswer(card):
    if getattr(card, 'answer', None) is None:
        return card._getQA()['a']
    return card.answer()


def patch_anki_2_1_50_having_null_stdout_on_windows():
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf8")


if sys.version_info >= (3, 12):
    batched = itertools.batched
else:
    def batched(iterable, n):
        iterator = iter(iterable)
        while True:
            batch = tuple(itertools.islice(iterator, n))
            if not batch:
                break
            yield batch
