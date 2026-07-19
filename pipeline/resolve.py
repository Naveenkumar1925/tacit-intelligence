"""Entity resolution for equipment tags (spec 8 P1 path 3, spec 14 gotcha #1).

Every mention of a pump/exchanger/valve, however it is spelled, must resolve to
exactly one canonical register tag. Duplicate equipment nodes silently break
every multi-hop query, so this module is deliberately small, deterministic and
unit-tested inline (run:  py pipeline/resolve.py).

Handled spellings (spec 6.6): "P-101A", "Pump 101A", "P101-A", "p-101a",
plus ASR output like "pee one oh one a" after digit normalisation (voice module).
"""

import re

# canonical register tags -> compact keys ("P101A") are built by the caller from
# the equipment register; this module only normalises raw mentions to keys.

_PREFIX_WORDS = {
    "PUMP": "P",
    "HEATEXCHANGER": "HX",
    "EXCHANGER": "HX",
    "CONTROLVALVE": "CV",
    "VALVE": "CV",
}

# spoken forms that Whisper produces for letters/digits ("pee one oh one a")
_SPOKEN = {
    "PEE": "P", "BEE": "B", "SEE": "C", "AY": "A", "EH": "A",
    "OH": "0", "O": "0", "ZERO": "0", "ONE": "1", "TWO": "2", "THREE": "3",
    "FOUR": "4", "FIVE": "5", "SIX": "6", "SEVEN": "7", "EIGHT": "8", "NINE": "9",
}

TAG_KEY_RE = re.compile(r"^(P|HX|CV)(\d{3})([A-Z])$")

# finds tag-like mentions in free text, tolerant of separators and the word forms
MENTION_RE = re.compile(
    r"\b(?:(pump|heat\s+exchanger|exchanger|control\s+valve|valve)\s*[-.\s]*)?"
    r"(p|hx|cv)?\s*[-.\s]*(\d{3})\s*[-.\s]*([a-c])\b",
    re.IGNORECASE,
)


def canonical_key(raw: str) -> str | None:
    """Normalise one raw tag mention to a compact key like 'P101A', or None."""
    s = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
    for word, abbr in _PREFIX_WORDS.items():
        if s.startswith(word):
            s = abbr + s[len(word):]
            break
    m = TAG_KEY_RE.match(s)
    return "".join(m.groups()) if m else None


def normalise_spoken(text: str) -> str:
    """Replace spelled-out digits/letters so the tag regex can fire on ASR text.

    'pee one oh one a' -> tokens P,1,0,1,a -> merged 'P101a' (consecutive
    single-character tokens are joined, otherwise the \\d{3} in the tag regex
    never sees contiguous digits).
    """
    out, buf = [], []
    for t in text.split():
        bare = re.sub(r"[^A-Za-z]", "", t).upper()
        mapped = _SPOKEN.get(bare, t)
        if len(mapped) == 1 and mapped.isalnum():
            buf.append(mapped)
        else:
            if buf:
                out.append("".join(buf))
                buf = []
            out.append(mapped)
    if buf:
        out.append("".join(buf))
    return " ".join(out)


def find_mentions_raw(text: str) -> list[tuple[str, str]]:
    """Return (canonical_key, raw_matched_text) for every tag-like mention."""
    out = []
    for m in MENTION_RE.finditer(text):
        word, prefix, num, letter = m.groups()
        pfx = None
        if prefix:
            pfx = prefix.upper()
        elif word:
            pfx = _PREFIX_WORDS.get(re.sub(r"\s+", "", word).upper())
        if not pfx:
            continue
        out.append((f"{pfx}{num}{letter.upper()}", m.group(0).strip()))
    return out


def find_mentions(text: str) -> list[str]:
    """Return canonical keys for every tag-like mention found in free text."""
    return [key for key, _raw in find_mentions_raw(text)]


def display_tag(key: str) -> str:
    """'P101A' -> 'P-101A' (the register's canonical display form)."""
    m = TAG_KEY_RE.match(key)
    if not m:
        raise ValueError(f"not a tag key: {key}")
    pfx, num, letter = m.groups()
    return f"{pfx}-{num}{letter}"


if __name__ == "__main__":
    # spec 6.6: the four spellings of P-101A must all resolve to one key
    for form in ("P-101A", "Pump 101A", "P101-A", "p-101a"):
        assert canonical_key(form) == "P101A", (form, canonical_key(form))
    # ASR: "pee one oh one a" -> P101A after spoken normalisation
    spoken = normalise_spoken("the pee one oh one a strainer chokes in monsoon")
    assert "P101A" in find_mentions(spoken), (spoken, find_mentions(spoken))
    # free text mentions
    assert find_mentions("clean Pump 101A and check HX-201B and cv 303 a") == [
        "P101A", "HX201B", "CV303A"]
    # non-tags must not match
    assert canonical_key("SOP-114") is None
    assert canonical_key("WO-2024-0031") is None
    assert display_tag("P101A") == "P-101A"
    print("resolve.py: all self-tests passed")
