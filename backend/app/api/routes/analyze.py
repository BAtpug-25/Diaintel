"""
DiaIntel — Analyze Routes
Live text analysis endpoint using DistilBERT.
"""

import re
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pydantic_models import AEDetail, AnalyzeRequest, AnalyzeResult
from app.nlp.ae_extractor import analyze_text_realtime
from app.nlp.cleaner import cleaner
from app.nlp.drug_ner import drug_ner
from app.nlp.misinfo_detector import misinfo_detector
from app.nlp.sentiment import sentiment_analyzer

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
async def analyze_text(request: AnalyzeRequest, db: Session = Depends(get_db)):
    start_time = time.time()
    raw_text = request.text or ""

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    clean_result = cleaner.clean(raw_text)
    if clean_result is None:
        return AnalyzeResult(
            drugs=[],
            adverse_events=[],
            sentiment={},
            misinfo_flag=False,
            highlighted_text=None,
            processing_time_ms=round((time.time() - start_time) * 1000, 2),
        )

    cleaned_text = clean_result["cleaned_text"]
    drug_mentions = drug_ner.extract(cleaned_text)
    normalized_drugs = [mention["drug_normalized"] for mention in drug_mentions]
    ae_result = analyze_text_realtime(cleaned_text)
    sentiment_rows = sentiment_analyzer.analyze_per_drug(cleaned_text, normalized_drugs) if normalized_drugs else []
    misinfo_result = misinfo_detector.detect(cleaned_text)

    highlight_terms = [mention["drug_name"] for mention in drug_mentions] + [row["ae_term"] for row in ae_result["adverse_events"]]
    payload = {
        "drugs": drug_mentions,
        "adverse_events": [AEDetail(**row) for row in ae_result["adverse_events"]],
        "sentiment": {
            row["drug_name"]: {
                "label": row["label"],
                "score": row["score"],
                "confidence": row["confidence"],
            }
            for row in sentiment_rows
        },
        "misinfo_flag": bool(misinfo_result["is_flagged"]),
        "highlighted_text": _highlight_text(cleaned_text, highlight_terms),
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    return payload
