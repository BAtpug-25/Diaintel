"""
DiaIntel — Outcome Extractor
Rule-based treatment outcome extraction written to treatment_outcomes.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import spacy
from spacy.matcher import PhraseMatcher
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

logger = logging.getLogger("diaintel.nlp.outcome_extractor")

OUTCOME_KEYWORDS = {
    "weight_loss": ["lost weight", "losing weight", "weight loss", "dropped pounds"],
    "glucose_improvement": ["a1c dropped", "blood sugar improved", "numbers came down"],
    "glucose_worsening": ["blood sugar spiked", "a1c went up", "glucose worse"],
    "treatment_failure": ["stopped working", "no effect", "gave up on", "discontinued"],
    "treatment_success": ["working great", "life changing", "excellent results"],
    "energy_change": ["more energy", "less fatigue", "exhausted", "tired all the time"],
}

OUTCOME_VERBS = [
    "helped",
    "improved",
    "worsened",
    "lost",
    "gained",
    "dropped",
    "failed",
    "stabilized",
    "controlled",
    "reduced",
    "increased",
]

VERB_TO_CATEGORY = {
    "helped": "treatment_success",
    "improved": "glucose_improvement",
    "worsened": "glucose_worsening",
    "lost": "weight_loss",
    "gained": "energy_change",
    "dropped": "glucose_improvement",
    "failed": "treatment_failure",
    "stabilized": "glucose_improvement",
    "controlled": "glucose_improvement",
    "reduced": "glucose_improvement",
    "increased": "glucose_worsening",
}

NEGATION_WORDS = {"not", "didn't", "didnt", "no", "never", "hardly"}

_nlp = None
_matcher = None


def _get_nlp():
    global _nlp, _matcher

    if _nlp is not None:
        return _nlp, _matcher

    try:
        _nlp = spacy.load("en_core_web_lg", disable=["ner"])
    except OSError:
        _nlp = spacy.blank("en")
        if "sentencizer" not in _nlp.pipe_names:
            _nlp.add_pipe("sentencizer")

    _matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
    _matcher.add("OUTCOME_VERBS", [_nlp.make_doc(term) for term in OUTCOME_VERBS])
    return _nlp, _matcher


def _detect_polarity(sentence_tokens: List[str], anchor_index: int) -> str:
    start = max(0, anchor_index - 5)
    window = sentence_tokens[start:anchor_index]
    return "negative" if any(token in NEGATION_WORDS for token in window) else "positive"


def _keyword_matches(sentence_lower: str) -> List[Tuple[str, float]]:
    matches: List[Tuple[str, float]] = []
    for category, phrases in OUTCOME_KEYWORDS.items():
        exact = next((phrase for phrase in phrases if phrase in sentence_lower), None)
        if exact:
            matches.append((category, 0.9))
            continue

        partial = any(
            len(set(phrase.split()) & set(sentence_lower.split())) >= max(2, len(phrase.split()) - 1)
            for phrase in phrases
        )
        if partial:
            matches.append((category, 0.6))
    return matches


def _extract_duration(sentence_text: str) -> str | None:
    duration_match = re.search(
        r"\b(\d+\s*(?:day|week|month|year)s?|a few\s+(?:days?|weeks?|months?)|several\s+(?:days?|weeks?|months?))\b",
        sentence_text,
        re.IGNORECASE,
    )
    return duration_match.group(1) if duration_match else None


def process_outcomes_for_post(post_id: int, text: str, drug_names: List[str], db: Session) -> int:
    """
    Extract outcomes for a processed post and insert them into treatment_outcomes.
    """
    if not text or not drug_names:
        return 0

    nlp, matcher = _get_nlp()
    doc = nlp(text)
    records: List[Dict] = []
    seen = set()

    for sent in doc.sents:
        sentence_text = sent.text.strip()
        sentence_lower = sentence_text.lower()
        keyword_results = _keyword_matches(sentence_lower)
        verb_matches = matcher(sent)

        fallback_results: List[Tuple[str, float, int]] = []
        for _, start, _ in verb_matches:
            token = sent[start]
            category = VERB_TO_CATEGORY.get(token.text.lower())
            if category:
                fallback_results.append((category, 0.7, start))

        if not keyword_results and not fallback_results:
            continue

        sentence_tokens = [token.text.lower() for token in sent]
        duration = _extract_duration(sentence_text)

        chosen_results: List[Tuple[str, float, int]] = []
        if keyword_results:
            for category, confidence in keyword_results:
                anchor_index = next(
                    (index for index, token in enumerate(sentence_tokens) if token in category.split("_")),
                    0,
                )
                chosen_results.append((category, confidence, anchor_index))
        else:
            chosen_results = fallback_results

        for category, confidence, anchor_index in chosen_results:
            polarity = _detect_polarity(sentence_tokens, anchor_index)
            if polarity == "negative":
                if category == "glucose_improvement":
                    category = "glucose_worsening"
                elif category == "treatment_success":
                    category = "treatment_failure"

            for drug_name in sorted(set(drug_names)):
                dedupe_key = (drug_name, category, sentence_text)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                records.append(
                    {
                        "post_id": post_id,
                        "drug_name": drug_name,
                        "outcome_category": category,
                        "outcome_text": sentence_text,
                        "polarity": polarity,
                        "confidence": confidence,
                        "duration": duration,
                        "detected_at": datetime.now(timezone.utc),
                    }
                )

    if not records:
        return 0

    db.execute(
        sql_text(
            """
            INSERT INTO treatment_outcomes
                (post_id, drug_name, outcome_category, outcome_text, polarity, confidence, duration, detected_at)
            VALUES
                (:post_id, :drug_name, :outcome_category, :outcome_text, :polarity, :confidence, :duration, :detected_at)
            """
        ),
        records,
    )
    return len(records)
