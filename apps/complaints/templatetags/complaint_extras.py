"""
Template filters for rendering user-generated text safely and cleanly.

`clean_text` removes control / zero-width / replacement characters that
render as garbled vertical bars or empty boxes in browsers (Phase 0 fix),
while preserving newlines and normal punctuation (including non-ASCII
scripts like Devanagari or Tamil, which are left untouched).
"""
import unicodedata

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape

register = template.Library()


# Characters that render as bars/boxes or are invisible but corrupt text
_BAD_CATEGORIES = {'Cc', 'Cf', 'Cs', 'Co', 'Cn', 'Zl', 'Zp'}
_ALLOWED_CONTROLS = {'\n', '\r', '\t'}


def _clean(value):
    if not isinstance(value, str):
        return value
    cleaned = []
    for ch in value:
        if ch in _ALLOWED_CONTROLS:
            cleaned.append('\n' if ch in ('\r', '\n') else ' ' if ch == '\t' else ch)
            continue
        if unicodedata.category(ch) in _BAD_CATEGORIES:
            continue
        cleaned.append(ch)
    text = ''.join(cleaned)
    # Normalise exotic spaces and unicode forms
    text = text.replace('\u00a0', ' ').replace('\u200b', '')
    text = unicodedata.normalize('NFC', text)
    return text


@register.filter
def clean_text(value):
    """Strip control/zero-width characters that render as garbled bars."""
    return _clean(value)


@register.filter
def clean_multiline(value):
    """Clean text and escape it, preserving line breaks (safe output)."""
    text = escape(_clean(value))
    paragraphs = [p.strip() for p in text.split('\n')]
    rendered = '<br>'.join(p for p in paragraphs if p)
    return mark_safe(rendered or '&mdash;')
