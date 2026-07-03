from typing import Optional


SUPPORTED_LANGUAGES = {"zh-CN", "en-US"}


def normalize_language(lang: Optional[str], default: str = "zh-CN") -> str:
    if not lang:
        return default
    if lang in SUPPORTED_LANGUAGES:
        return lang
    normalized = lang.lower()
    if normalized.startswith("en"):
        return "en-US"
    if normalized.startswith("zh"):
        return "zh-CN"
    return default


def choose_text(lang: str, zh_text: Optional[str], en_text: Optional[str]) -> Optional[str]:
    if lang == "en-US":
        return en_text or zh_text
    return zh_text or en_text
