"""
DiaIntel — Sentiment Analyzer
Scores per-drug sentiment using a local RoBERTa sentiment model.
"""

import os

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import logging
import math
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

import torch
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger("diaintel.nlp.sentiment")

TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]")
WINDOW_RADIUS = 100

_tokenizer = None
_model = None
_device = None


def _load_model():
    global _tokenizer, _model, _device

    if _model is not None:
        return

    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    model_path = f"{settings.MODEL_CACHE_DIR}/cardiffnlp--twitter-roberta-base-sentiment"
    _device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info("Loading RoBERTa sentiment model from %s on %s", model_path, _device)
    _tokenizer = AutoTokenizer.from_pretrained(model_path)
    _model = AutoModelForSequenceClassification.from_pretrained(model_path)
    _model.to(_device)
    _model.eval()


def _softmax(logits: torch.Tensor) -> torch.Tensor:
    return torch.nn.functional.softmax(logits, dim=-1)


def _tokenize_text(text: str) -> List[str]:
    return [match.group(0) for match in TOKEN_PATTERN.finditer(text)]


def _extract_window(text: str, drug_name: str) -> str:
    tokens = _tokenize_text(text)
    lowered = [token.lower() for token in tokens]
    drug_parts = drug_name.lower().split()

    for index in range(len(lowered)):
        if lowered[index:index + len(drug_parts)] == drug_parts:
            start = max(0, index - WINDOW_RADIUS)
            end = min(len(tokens), index + len(drug_parts) + WINDOW_RADIUS)
            return " ".join(tokens[start:end])

    return text if len(tokens) <= WINDOW_RADIUS * 2 else " ".join(tokens[: WINDOW_RADIUS * 2])


def _normalize_label(label: str) -> str:
    lowered = label.lower()
    if "negative" in lowered or lowered.endswith("_0") or lowered == "label_0":
        return "negative"
    if "neutral" in lowered or lowered.endswith("_1") or lowered == "label_1":
        return "neutral"
    return "positive"


def analyze_window(text: str) -> Dict:
    """Score a text window and return label, signed score, and confidence."""
    _load_model()

    with torch.no_grad():
        encoded = _tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=256,
        ).to(_device)
        logits = _model(**encoded).logits
        probs = _softmax(logits)[0]

    label_index = int(torch.argmax(probs).item())
    label = _normalize_label(_model.config.id2label.get(label_index, f"LABEL_{label_index}"))
    confidence = float(probs[label_index].item())
    signed_score = float(probs[2].item() - probs[0].item())

    return {
        "label": label,
        "score": round(signed_score, 4),
        "confidence": round(confidence, 4),
    }


class SentimentAnalyzer:
    """Analyzes sentiment of text related to specific drugs."""

    def __init__(self):
        self.initialized = False
        logger.info("SentimentAnalyzer created (model not loaded)")

    def initialize(self, model_path: Optional[str] = None):
        _load_model()
        self.initialized = True

    def analyze(self, text: str) -> Dict:
        return analyze_window(text)

    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        return [analyze_window(text) for text in texts]

    def analyze_per_drug(self, text: str, drugs: List[str]) -> List[Dict]:
        results = []
        for drug in drugs:
            window_text = _extract_window(text, drug)
            result = analyze_window(window_text)
            result["drug_name"] = drug
            result["window_text"] = window_text
            results.append(result)
        return results


def _refresh_drug_cache(drug_name: str, db: Session) -> None:
    db.execute(
        sql_text(
            """
            INSERT INTO drug_stats_cache (drug_name, total_posts, top_ae_json, avg_sentiment, last_computed)
            VALUES (
                :drug_name,
                (
                    SELECT COUNT(DISTINCT post_id)
                    FROM drug_mentions
                    WHERE drug_normalized = :drug_name
                ),
                COALESCE(
                    (
                        SELECT jsonb_agg(
                            jsonb_build_object('ae_term', ae_term, 'count', cnt)
                            ORDER BY cnt DESC
                        )
                        FROM (
                            SELECT COALESCE(ae_normalized, ae_term) AS ae_term, COUNT(*) AS cnt
                            FROM ae_signals
                            WHERE drug_name = :drug_name
                            GROUP BY COALESCE(ae_normalized, ae_term)
                            ORDER BY cnt DESC
                            LIMIT 5
                        ) ranked_aes
                    ),
                    '[]'::jsonb
                ),
                COALESCE(
                    (
                        SELECT AVG(sentiment_score)
                        FROM sentiment_scores
                        WHERE drug_name = :drug_name
                    ),
                    0.0
                ),
                NOW()
            )
            ON CONFLICT (drug_name) DO UPDATE
            SET total_posts = EXCLUDED.total_posts,
                top_ae_json = EXCLUDED.top_ae_json,
                avg_sentiment = EXCLUDED.avg_sentiment,
                last_computed = NOW()
            """
        ),
        {"drug_name": drug_name},
    )


def score_sentiment_for_post(post_id: int, text: str, drug_mentions: List[str], db: Session) -> List[Dict]:
    """
    Score sentiment windows for each normalized drug mention and persist results.
    """
    unique_drugs = sorted({drug for drug in drug_mentions if drug})
    if not unique_drugs or not text:
        return []

    existing = set(
        db.execute(
            sql_text("SELECT drug_name FROM sentiment_scores WHERE post_id = :post_id"),
            {"post_id": post_id},
        ).scalars().all()
    )

    records = []
    results = []
    for drug_name in unique_drugs:
        if drug_name in existing:
            continue
        window_text = _extract_window(text, drug_name)
        result = analyze_window(window_text)
        results.append({"drug_name": drug_name, **result, "window_text": window_text})
        records.append(
            {
                "post_id": post_id,
                "drug_name": drug_name,
                "sentiment_label": result["label"],
                "sentiment_score": result["score"],
                "confidence": result["confidence"],
                "scored_at": datetime.now(timezone.utc),
            }
        )

    if records:
        db.execute(
            sql_text(
                """
                INSERT INTO sentiment_scores
                    (post_id, drug_name, sentiment_label, sentiment_score, confidence, scored_at)
                VALUES
                    (:post_id, :drug_name, :sentiment_label, :sentiment_score, :confidence, :scored_at)
                """
            ),
            records,
        )
        for drug_name in unique_drugs:
            _refresh_drug_cache(drug_name, db)

    return results


def process_unprocessed_sentiment(batch_size: int = 250) -> int:
    """
    Batch-score processed posts that still lack sentiment rows.
    """
    from app.database import SessionLocal

    db = SessionLocal()
    total_inserted = 0

    try:
        rows = db.execute(
            sql_text(
                """
                SELECT pp.id, pp.cleaned_text
                FROM processed_posts pp
                WHERE EXISTS (
                    SELECT 1 FROM drug_mentions dm WHERE dm.post_id = pp.id
                )
                AND NOT EXISTS (
                    SELECT 1 FROM sentiment_scores ss WHERE ss.post_id = pp.id
                )
                ORDER BY pp.id
                LIMIT :limit
                """
            ),
            {"limit": batch_size},
        ).mappings().all()

        for row in rows:
            drug_mentions = db.execute(
                sql_text(
                    """
                    SELECT DISTINCT drug_normalized
                    FROM drug_mentions
                    WHERE post_id = :post_id
                    """
                ),
                {"post_id": row["id"]},
            ).scalars().all()
            inserted = score_sentiment_for_post(row["id"], row["cleaned_text"], drug_mentions, db)
            total_inserted += len(inserted)

        db.commit()
        return total_inserted
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


sentiment_analyzer = SentimentAnalyzer()
