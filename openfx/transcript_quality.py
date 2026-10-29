"""Deterministic warning checks for transcript extraction fidelity.

These checks detect selected high-risk changes; they cannot prove semantic equivalence.
"""
from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from typing import Any

_TOKEN_RE = re.compile(r"[+-]?\d+(?:[.,:/-]\d+)*(?:%|٪)?|[^\W\d_]+(?:['’][^\W\d_]+|‌[^\W\d_]+)*", re.UNICODE)
_NEGATIONS = {
    "not", "no", "never", "without", "cannot", "can't", "isn't", "aren't",
    "wasn't", "weren't", "doesn't", "don't", "didn't", "won't", "wouldn't",
    "shouldn't", "mustn't", "neither", "nor",
    "نه", "نیست", "نیستم", "نیستی", "نیستند", "نبود", "نبوده", "هرگز",
    "بدون", "نمی‌شود", "نمیشود", "نمی‌کند", "نمیکند", "نخواهد", "نشود",
}

# Changes to these condition/threshold words can reverse or materially narrow a
# trading rule even when overall token similarity remains high.
_CONDITION_MARKERS = {
    "only", "unless", "except", "until", "if", "when", "while",
    "before", "after", "above", "below", "over", "under", "between",
    "within", "outside", "least", "most", "minimum", "maximum",
    "greater", "less", "equal", "equals", "later", "earlier", "prior",
    "following", "exactly", "strictly", "inclusive", "exclusive",
    "فقط", "مگر", "جز", "به‌جز", "تا", "قبل", "پیش", "بعد",
    "بالا", "پایین", "بالاتر", "پایین‌تر", "حداقل", "حداکثر",
    "بیشتر", "کمتر", "برابر", "اگر", "وقتی", "باید", "لازم",
    "مجاز", "غیرمجاز",
}


_DIGIT_AND_SYMBOL_TRANSLATION = str.maketrans({
    **dict(zip("۰۱۲۳۴۵۶۷۸۹", "0123456789")),
    **dict(zip("٠١٢٣٤٥٦٧٨٩", "0123456789")),
    "٪": "%",
    "−": "-",
    "－": "-",
    "＋": "+",
})


def _tokens(text: str) -> list[str]:
    # Normalize equivalent digit and sign glyphs before comparing. Keep the
    # sign and percent marker attached to numeric tokens so meaningful changes
    # such as -5 -> 5 and 5% -> 5 remain detectable.
    normalized = text.translate(_DIGIT_AND_SYMBOL_TRANSLATION)
    return [token.casefold() for token in _TOKEN_RE.findall(normalized)]


def compare_transcript_fidelity(reference_text: Any, extracted_text: Any, *, min_similarity: float = 0.85) -> dict:
    """Flag dropped/altered numbers, dates, negations, and large text drift."""
    if not isinstance(reference_text, str) or not reference_text.strip():
        raise ValueError("reference_text must be a non-empty string")
    if not isinstance(extracted_text, str) or not extracted_text.strip():
        raise ValueError("extracted_text must be a non-empty string")
    if not isinstance(min_similarity, (int, float)) or isinstance(min_similarity, bool) or not 0 <= min_similarity <= 1:
        raise ValueError("min_similarity must be between 0 and 1")

    reference_tokens = _tokens(reference_text)
    extracted_tokens = _tokens(extracted_text)
    reference_numbers = Counter(token for token in reference_tokens if token.lstrip("+-") and token.lstrip("+-")[0].isdigit())
    extracted_numbers = Counter(token for token in extracted_tokens if token.lstrip("+-") and token.lstrip("+-")[0].isdigit())
    missing_numbers = list((reference_numbers - extracted_numbers).elements())
    unexpected_numbers = list((extracted_numbers - reference_numbers).elements())
    reference_negations = [token for token in reference_tokens if token in _NEGATIONS]
    extracted_negations = [token for token in extracted_tokens if token in _NEGATIONS]
    reference_conditions = [token for token in reference_tokens if token in _CONDITION_MARKERS]
    extracted_conditions = [token for token in extracted_tokens if token in _CONDITION_MARKERS]
    similarity = SequenceMatcher(a=reference_tokens, b=extracted_tokens, autojunk=False).ratio()
    flags = []
    if missing_numbers:
        flags.append("missing_or_changed_numbers")
    if unexpected_numbers:
        flags.append("unexpected_numbers")
    if reference_negations != extracted_negations:
        flags.append("negation_mismatch")
    if reference_conditions != extracted_conditions:
        flags.append("condition_mismatch")
    if similarity < min_similarity:
        flags.append("low_token_similarity")

    return {
        "status": "pass_selected_checks" if not flags else "needs_human_review",
        "similarity": round(similarity, 4),
        "flags": flags,
        "reference_numbers": list(reference_numbers.elements()),
        "extracted_numbers": list(extracted_numbers.elements()),
        "reference_negations": reference_negations,
        "extracted_negations": extracted_negations,
        "scope": "heuristic_only_not_semantic_proof",
    }
