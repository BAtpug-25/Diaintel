"""
DiaIntel — Misinformation Detector
Flags potentially unsafe claims with local BART-MNLI zero-shot inference.
"""

import os

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import torch
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger("diaintel.nlp.misinfo_detector")

MISINFO_HYPOTHESES = [
    "This text makes a false medical claim",
    "This text recommends stopping prescribed medication",
    "This text claims a drug cures diabetes",
    "This text promotes dangerous self-medication",
    "This text contradicts established medical guidelines",
]

_tokenizer = None
_model = None
_device = None


def _load_model():
    global _tokenizer, _model, _device

    if _model is not None:
        return

    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    model_path = f"{settings.MODEL_CACHE_DIR}/facebook--bart-large-mnli"
    _device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Loading BART-MNLI misinfo detector from %s on %s", model_path, _device)

    _tokenizer = AutoTokenizer.from_pretrained(model_path)
    _model = AutoModelForSequenceClassification.from_pretrained(model_path)
    _model.to(_device)
    _model.eval()


def _entailment_score(premise: str, hypothesis: str) -> float:
    _load_model()

    with torch.no_grad():
        encoded = _tokenizer(
            premise,
            hypothesis,
            return_tensors="pt",
            truncation=True,
            max_length=256,
        ).to(_device)
        logits = _model(**encoded).logits
        contradiction_entailment = logits[:, [0, 2]]
        probs = torch.nn.functional.softmax(contradiction_entailment, dim=1)
        return float(probs[0, 1].item())


class MisinfoDetector:
    """Detects potential medical misinformation using BART-MNLI zero-shot."""

    def __init__(self):
        self.initialized = False
        logger.info("MisinfoDetector created (model not loaded)")

    def initialize(self, model_path: Optional[str] = None):
        _load_model()
        self.initialized = True

    def detect(self, text: str) -> Dict:
        if not text:
            return {
                "is_flagged": False,
                "claim_text": None,
                "flag_reason": None,
                "confidence": 0.0,
                "hypothesis_scores": [],
            }

        scores = []
        best_hypothesis = None
        best_score = 0.0

        for hypothesis in MISINFO_HYPOTHESES:
            score = _entailment_score(text, hypothesis)
            scores.append({"hypothesis": hypothesis, "score": round(score, 4)})
            if score > best_score:
                best_score = score
                best_hypothesis = hypothesis

        return {
            "is_flagged": best_score >= 0.7,
            "claim_text": text if best_score >= 0.7 else None,
            "flag_reason": best_hypothesis if best_score >= 0.7 else None,
            "confidence": round(best_score, 4),
            "hypothesis_scores": scores,
        }

    def detect_batch(self, texts: List[str]) -> List[Dict]:
        return [self.detect(text) for text in texts]


def check_misinfo_for_post(post_id: int, text: str, db: Session) -> Dict:
    """
    Flag a processed post if it appears to contain misinformation.
    """
    existing = db.execute(
        sql_text("SELECT id FROM misinfo_flags WHERE post_id = :post_id LIMIT 1"),
        {"post_id": post_id},
    ).first()
    if existing:
        return {"is_flagged": True, "confidence": 1.0, "flag_reason": "already_flagged", "claim_text": None}

    result = misinfo_detector.detect(text)
    if result["is_flagged"]:
        db.execute(
            sql_text(
                """
                INSERT INTO misinfo_flags
                    (post_id, claim_text, flag_reason, confidence, flagged_at, reviewed)
                VALUES
                    (:post_id, :claim_text, :flag_reason, :confidence, :flagged_at, FALSE)
                """
            ),
            {
                "post_id": post_id,
                "claim_text": result["claim_text"],
                "flag_reason": result["flag_reason"],
                "confidence": result["confidence"],
                "flagged_at": datetime.now(timezone.utc),
            },
        )
    return result


misinfo_detector = MisinfoDetector()
