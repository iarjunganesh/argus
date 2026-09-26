"""Whether a retrieved passage actually names the entity being screened.

Retrieval ranks passages by overlap, so a passage sharing only a first name or a country code can
still rank. A screening hit needs more: every word of the entity's name, or of one of its aliases,
must appear in the passage.
"""

import re

_WORD = re.compile(r"[a-z0-9]+")


def _words(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def mentions(text: str, names: list[str]) -> bool:
    words = _words(text)
    return any(name_words <= words for name_words in map(_words, names) if name_words)
