"""V11.8.5: display-only language choices for Book Library and unified search.

Language names are suggestions, NOT proof that a file is indexed. The counts are
computed from the caller's already retrieved records. No DB access or writes.
"""
from __future__ import annotations

# Common language choices, in the order illustrated by the supplied screenshot.
# Also retain the bot's existing Sinhala/Arabic audience and any catalog extras.
COMMON_LANGUAGES = (
    'Malayalam', 'Tamil', 'English', 'Hindi', 'Telugu',
    'Kannada', 'Gujarati', 'Marathi', 'Punjabi', 'Sinhala', 'Arabic',
)


def language_counts(values, *, limit=30):
    """Return stable (language, count) pairs, including zero-count common choices.

    Input: iterable of (name, count), allowing capitalization variants. Unusual
    catalog values are deliberately shown instead of silently being reclassified.
    """
    merged = {}
    for label, count in values:
        name = ' '.join(str(label or '').split())
        if not name or len(name) > 60:
            continue
        try:
            amount = max(0, int(count or 0))
        except (TypeError, ValueError):
            amount = 0
        folded = name.casefold()
        if folded not in merged:
            merged[folded] = [name, 0]
        merged[folded][1] += amount
    choices = []
    for standard in COMMON_LANGUAGES:
        item = merged.pop(standard.casefold(), None)
        choices.append((standard, item[1] if item else 0))
    extras = sorted(merged.values(), key=lambda v: v[0].casefold())
    choices.extend((name, number) for name, number in extras)
    return choices[:limit]
