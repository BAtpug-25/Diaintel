"""
DiaIntel - Timeline Extractor
Associates temporal expressions with nearby adverse events.
"""

import logging
import re
from typing import Dict, List, Tuple

import spacy
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

logger = logging.getLogger("diaintel.nlp.timeline_extractor")

TIMELINE_PATTERNS = [
    r"\b(\d+)\s*(day|week|month|year)s?\b",
    r"\b(a few|several|some)\s+(day|week|month)s?\b",
    r"\b(about|around|nearly)\s+\d+\s+\w+\b",
    r"\bafter\s+(\d+|a few|several)\s+\w+\b",
    r"\b(overnight|immediately|instantly)\b",
    r"\b(long-term|short-term|permanent)\b",
]

TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]")

_timeline_nlp = None


def _get_nlp():
    global _timeline_nlp
    if _timeline_nlp is not None:
        return _timeline_nlp

    try:
        _timeline_nlp = spacy.load("en_core_web_lg")
    except OSError:
        _timeline_nlp = spacy.blank("en")
        if "sentencizer" not in _timeline_nlp.pipe_names:
            _timeline_nlp.add_pipe("sentencizer")

    return _timeline_nlp


def _tokenize_with_offsets(text: str) -> List[Dict]:
    return [
        {"text": match.group(0), "start": match.start(), "end": match.end()}
        for match in TOKEN_PATTERN.finditer(text)
    ]


def _char_to_token_index(tokens: List[Dict], char_pos: int) -> int:
    for index, token in enumerate(tokens):
        if token["start"] <= char_pos < token["end"]:
            return index
    return max(0, len(tokens) - 1)


def get_duration_for_span(text: str, span_start: int, span_end: int) -> str:
    """Return a normalized duration string for the detected span."""
    return text[span_start:span_end].strip()


def _collect_temporal_spans(text: str) -> List[Tuple[int, int, str]]:
    spans: List[Tuple[int, int, str]] = []
    doc = _get_nlp()(text)

    for ent in getattr(doc, "ents", []):
        if ent.label_ in {"DATE", "TIME"}:
            spans.append((ent.start_char, ent.end_char, ent.text.strip()))

    for pattern in TIMELINE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            spans.append((match.start(), match.end(), get_duration_for_span(text, match.start(), match.end())))

    deduped = {}
    for start, end, label in spans:
        deduped[(start, end)] = label
    return [(start, end, label) for (start, end), label in sorted(deduped.items(), key=lambda item: item[0][0])]


def extract_timeline_matches(text: str, ae_terms: List[str]) -> List[Dict]:
    """Return timeline markers associated with the nearest AE mention in the text."""
    if not text or not ae_terms:
        return []

    tokens = _tokenize_with_offsets(text)
    if not tokens:
        return []

    text_lower = text.lower()
    ae_occurrences: List[Dict] = []
    for ae_term in ae_terms:
        lowered_term = (ae_term or "").lower()
        if not lowered_term:
            continue
        for match in re.finditer(re.escape(lowered_term), text_lower):
            ae_occurrences.append(
                {
                    "ae_term": ae_term,
                    "token_index": _char_to_token_index(tokens, match.start()),
                }
            )
            break

    if not ae_occurrences:
        return []

    matches = {}
    for span_start, _, label in _collect_temporal_spans(text):
        span_token_index = _char_to_token_index(tokens, span_start)
        nearest = min(ae_occurrences, key=lambda item: abs(item["token_index"] - span_token_index))
        if abs(nearest["token_index"] - span_token_index) <= 15:
            matches[nearest["ae_term"]] = label

    return [
        {"ae_term": ae_term, "temporal_marker": marker}
        for ae_term, marker in matches.items()
    ]


def extract_timelines_for_post(post_id: int, text: str, db: Session) -> int:
    """
    Update ae_signals.temporal_marker for AE rows whose mention is near a temporal expression.
    """
    if not text:
        return 0

    ae_rows = db.execute(
        sql_text(
            """
            SELECT id, ae_term, COALESCE(ae_normalized, ae_term) AS ae_display
            FROM ae_signals
            WHERE post_id = :post_id
            """
        ),
        {"post_id": post_id},
    ).mappings().all()

    if not ae_rows:
        return 0

    timeline_matches = extract_timeline_matches(text, [row["ae_term"] for row in ae_rows])
    if not timeline_matches:
        return 0

    updates = []
    for match in timeline_matches:
        ae_row = next((row for row in ae_rows if row["ae_term"] == match["ae_term"]), None)
        if ae_row is None:
            continue
        updates.append({"id": ae_row["id"], "temporal_marker": match["temporal_marker"]})

    if not updates:
        return 0

    db.execute(
        sql_text(
            """
            UPDATE ae_signals
            SET temporal_marker = :temporal_marker
            WHERE id = :id
              AND (temporal_marker IS NULL OR temporal_marker = '')
            """
        ),
        updates,
    )
    return len(updates)
