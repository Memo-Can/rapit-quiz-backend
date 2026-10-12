"""Basit kara liste tabanlı isim filtresi.

Uzun kelimeler birleştirilmiş metinde aranır; kısa kelimeler yalnızca tam sözcük
olarak eşleşir (masum isimlerin yanlış engellenmemesi için).
"""

import re
import unicodedata

_TR_MAP = str.maketrans({"ı": "i", "İ": "i", "ß": "ss"})
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "@": "a", "$": "s"})

SUBSTRING_WORDS = {
    "orospu",
    "kahpe",
    "yarrak",
    "sikik",
    "sikeyim",
    "siktir",
    "amcik",
    "pezevenk",
    "gotveren",
    "ibne",
    "fuck",
    "shit",
    "bitch",
    "asshole",
    "nigger",
    "nigga",
}
WHOLE_WORDS = {"amk", "aq", "sik", "got", "pic", "pust", "oc", "cunt", "sg"}


def _normalize(text):
    text = text.translate(_TR_MAP).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.translate(_LEET)


def is_inappropriate(name):
    normalized = _normalize(name)
    tokens = [t for t in re.split(r"[^a-z]+", normalized) if t]
    if any(t in WHOLE_WORDS for t in tokens):
        return True
    squashed = "".join(tokens)
    return any(word in squashed for word in SUBSTRING_WORDS)
