"""
DiaIntel - Analyze routes.
Live text analysis endpoint using DistilBERT and the v2 treatment-intelligence helpers.
"""

import re
import time

from fastapi import APIRouter, HTTPException

from app.models.pydantic_models import AnalyzeRequest, AnalyzeResult
from app.nlp.ae_extractor import analyze_text_realtime
from app.nlp.cleaner import cleaner
from app.nlp.combo_detector import detect_combinations
from app.nlp.drug_ner import drug_ner
from app.nlp.misinfo_detector import misinfo_detector
from app.nlp.outcome_extractor import extract_outcomes
from app.nlp.sentiment import sentiment_analyzer
from app.nlp.timeline_extractor import extract_timeline_matches

router = APIRouter()


def _highlight_text(text: str, terms: list[str]) -> str:
    highlighted = text
    for term in sorted({term for term in terms if term}, key=len, reverse=True):
        highlighted = re.sub(
            re.escape(term),
            lambda match: f"[{match.group(0)}]",
            highlighted,
            flags=re.IGNORECASE,
        )
    return highlighted


@router.post("/analyze", response_model=AnalyzeResult)
async def analyze_text(request: AnalyzeRequest):
    start_time = time.time()
    raw_text = request.text or ""

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    clean_result = cleaner.clean(raw_text)
    if clean_result is None:
        return {
            "drugs": [],
            "adverse_events": [],
            "outcomes": [],
            "timelines": [],
            "combinations": [],
            "sentiment": {},
            "misinfo": {
                "is_flagged": False,
                "claim_text": None,
                "flag_reason": None,
                "confidence": 0.0,
                "hypothesis_scores": [],
            },
            "highlighted_text": None,
            "processing_time_ms": round((time.time() - start_time) * 1000, 2),
        }

    cleaned_text = clean_result["cleaned_text"]
    drug_mentions = drug_ner.extract(cleaned_text)
    normalized_drugs = [mention["drug_normalized"] for mention in drug_mentions]
    ae_result = analyze_text_realtime(cleaned_text)
    outcome_rows = extract_outcomes(cleaned_text, normalized_drugs)
    combo_rows = detect_combinations(normalized_drugs, cleaned_text)
    sentiment_rows = sentiment_analyzer.analyze_per_drug(cleaned_text, normalized_drugs) if normalized_drugs else []
    misinfo_result = misinfo_detector.detect(cleaned_text)

    timeline_rows = [
        {
            "label": row["temporal_marker"],
            "kind": "ae_duration",
            "target_type": "ae",
            "target_label": row["ae_term"],
        }
        for row in extract_timeline_matches(cleaned_text, [ae["ae_term"] for ae in ae_result["adverse_events"]])
    ]
    timeline_rows.extend(
        {
            "label": row["duration"],
            "kind": "outcome_duration",
            "target_type": "outcome",
            "target_label": row["outcome_category"],
        }
        for row in outcome_rows
        if row.get("duration")
    )

    highlight_terms = [mention["drug_name"] for mention in drug_mentions]
    highlight_terms.extend([mention.get("dosage") for mention in drug_mentions if mention.get("dosage")])
    highlight_terms.extend([row["ae_term"] for row in ae_result["adverse_events"]])

    payload = {
        "drugs": drug_mentions,
        "adverse_events": ae_result["adverse_events"],
        "outcomes": outcome_rows,
        "timelines": timeline_rows,
        "combinations": combo_rows,
        "sentiment": {
            row["drug_name"]: {
                "label": row["label"],
                "score": row["score"],
                "confidence": row["confidence"],
            }
            for row in sentiment_rows
        },
        "misinfo": misinfo_result,
        "highlighted_text": _highlight_text(cleaned_text, highlight_terms),
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    return payload
