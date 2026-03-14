import json
import os
from config import Config

_cache: dict[str, dict] = {}


def load_locale(lang: str) -> dict:
    if lang not in _cache:
        path = os.path.join("locales", f"{lang}.json")
        fallback = os.path.join("locales", "en.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                _cache[lang] = json.load(f)
        except FileNotFoundError:
            with open(fallback, "r", encoding="utf-8") as f:
                _cache[lang] = json.load(f)
    return _cache[lang]


def t(key: str, lang: str = "en", **kwargs) -> str:
    locale = load_locale(lang)
    text = locale.get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
