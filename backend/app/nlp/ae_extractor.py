"""
DiaIntel — Adverse Event Extractor (Step 4)
Hybrid keyword + embedding-based AE extraction.

Batch mode uses BioBERT for historical processing.
Real-time mode uses DistilBERT for the /analyze endpoint.
"""

import os

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import logging
import re
import time
from datetime import datetime, timezone
from typing import Dict, List

import torch
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.utils.meddra_mapper import meddra_mapper

logger = logging.getLogger("diaintel.nlp.ae_extractor")

AE_TERMS = [
    "nausea", "vomiting", "diarrhea", "constipation",
    "bloating", "stomach cramps", "abdominal pain",
    "headache", "dizziness", "fatigue",
    "weight loss", "weight gain", "appetite loss",
    "hypoglycemia", "low blood sugar",
    "muscle pain", "joint pain", "back pain",
    "urinary tract infection", "uti",
    "dehydration", "dry mouth",
    "skin rash", "itching", "injection site reaction",
    "pancreatitis", "thyroid", "kidney",
    "heart palpitations", "chest pain",
    "hair loss", "blurred vision",
    "insomnia", "anxiety", "depression",
    "stomach ache", "stomach pain", "gi issues", "gi problems",
    "tired", "exhaustion", "dizzy",
    "felt sick", "feeling sick", "throwing up",
    "can't sleep", "couldn't sleep",
    "gained weight", "lost weight",
    "sugar crash", "sugar low",
    "rash", "hives",
]

SEVERE_KEYWORDS = {"severe", "horrible", "unbearable", "extreme", "terrible", "excruciating", "intense", "worst"}
MILD_KEYWORDS = {"mild", "slight", "minor", "barely", "faint", "subtle"}

BATCH_SIZE = 16
MAX_LENGTH = 256

_biobert_tokenizer = None
_biobert_model = None
_distilbert_tokenizer = None
_distilbert_model = None
_device = None
_biobert_seed_embeddings = None
_distilbert_seed_embeddings = None


def _ensure_device() -> str:
    global _device
    if _device is None:
        _device = "cuda" if torch.cuda.is_available() else "cpu"
    return _device


def _load_biobert():
    global _biobert_tokenizer, _biobert_model, _biobert_seed_embeddings
    if _biobert_model is not None:
        return

    from transformers import AutoModel, AutoTokenizer

    model_path = f"{settings.MODEL_CACHE_DIR}/dmis-lab--biobert-base-cased-v1.2"
    logger.info("Loading BioBERT from %s on %s", model_path, _ensure_device())
    _biobert_tokenizer = AutoTokenizer.from_pretrained(model_path)
    _biobert_model = AutoModel.from_pretrained(model_path)
    _biobert_model.to(_ensure_device())
    _biobert_model.eval()
    _biobert_seed_embeddings = _compute_seed_embeddings(_biobert_tokenizer, _biobert_model)


def _load_distilbert():
    global _distilbert_tokenizer, _distilbert_model, _distilbert_seed_embeddings
    if _distilbert_model is not None:
        return

    from transformers import AutoModel, AutoTokenizer

    model_path = f"{settings.MODEL_CACHE_DIR}/distilbert-base-uncased"
    logger.info("Loading DistilBERT from %s on %s", model_path, _ensure_device())
    _distilbert_tokenizer = AutoTokenizer.from_pretrained(model_path)
    _distilbert_model = AutoModel.from_pretrained(model_path)
    _distilbert_model.to(_ensure_device())
    _distilbert_model.eval()
    _distilbert_seed_embeddings = _compute_seed_embeddings(_distilbert_tokenizer, _distilbert_model)


def _compute_seed_embeddings(tokenizer, model) -> torch.Tensor:
    embeddings = []
    with torch.no_grad():
        for term in AE_TERMS:
            encoded = tokenizer(
                term,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=32,
            ).to(_ensure_device())
            outputs = model(**encoded)
            embeddings.append(outputs.last_hidden_state.mean(dim=1).squeeze(0))
    return torch.stack(embeddings)


def extract_ae_spans(text: str) -> List[Dict]:
    """Scan text for known AE terms and return matched spans with offsets."""
    if not text:
        return []

    spans = []
    occupied = set()
    lowered = text.lower()

    for term in sorted(AE_TERMS, key=len, reverse=True):
        pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
        for match in pattern.finditer(lowered):
            start, end = match.start(), match.end()
            if any(not (end <= other_start or start >= other_end) for other_start, other_end in occupied):
                continue
            occupied.add((start, end))
            spans.append(
                {
                    "term": term,
                    "start": start,
                    "end": end,
                    "normalized": meddra_mapper.normalize(term),
                }
            )
    return spans


def _compute_span_confidence(text: str, spans: List[Dict], tokenizer, model, seed_embeddings: torch.Tensor) -> List[Dict]:
    if not spans:
        return spans

    with torch.no_grad():
        encoded = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=MAX_LENGTH,
        ).to(_ensure_device())
        outputs = model(**encoded)
        pooled = outputs.last_hidden_state.mean(dim=1).squeeze(0)
        similarities = torch.nn.functional.cosine_similarity(pooled.unsqueeze(0), seed_embeddings, dim=1)
        max_similarity = float(similarities.max().item())

    for span in spans:
        base_confidence = 0.8
        similarity_boost = max(0.0, max_similarity - 0.5) * 0.4
        span["confidence"] = min(0.99, round(base_confidence + similarity_boost, 4))
    return spans


def detect_severity(text: str, ae_term: str) -> str:
    lowered = text.lower()
    position = lowered.find(ae_term.lower())
    if position >= 0:
        context = lowered[max(0, position - 100): min(len(lowered), position + len(ae_term) + 100)]
    else:
        context = lowered

    context_words = set(re.findall(r"\b\w+\b", context))
    if context_words & SEVERE_KEYWORDS:
        return "severe"
    if context_words & MILD_KEYWORDS:
        return "mild"
    return "moderate"


def process_batch(posts: List[Dict], db_session: Session) -> int:
    """
    Process a batch of cleaned posts with BioBERT and insert ae_signals rows.
    """
    if not posts:
        return 0

    _load_biobert()

    batch_start = time.time()
    ae_records = []
    inserted_count = 0

    for index in range(0, len(posts), BATCH_SIZE):
        sub_batch = posts[index:index + BATCH_SIZE]
        texts = [post["clean_text"] for post in sub_batch]

        with torch.no_grad():
            encoded = _biobert_tokenizer(
                texts,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=MAX_LENGTH,
            ).to(_ensure_device())
            outputs = _biobert_model(**encoded)
            pooled = outputs.last_hidden_state.mean(dim=1)
            similarities = torch.nn.functional.cosine_similarity(
                pooled.unsqueeze(1),
                _biobert_seed_embeddings.unsqueeze(0),
                dim=2,
            )
            max_similarities = similarities.max(dim=1).values.tolist()

        for row_index, post in enumerate(sub_batch):
            spans = extract_ae_spans(post["clean_text"])
            if not spans:
                continue

            drugs = post.get("drug_mentions") or []
            if not drugs:
                continue
            max_similarity = max_similarities[row_index]
            for span in spans:
                confidence = min(0.99, round(0.8 + max(0.0, max_similarity - 0.5) * 0.4, 4))
                severity = detect_severity(post["clean_text"], span["term"])
                for drug_name in drugs:
                    ae_records.append(
                        {
                            "post_id": post["id"],
                            "drug_name": drug_name,
                            "ae_term": span["term"],
                            "ae_normalized": span["normalized"],
                            "severity": severity,
                            "confidence": confidence,
                            "temporal_marker": None,
                            "detected_at": datetime.now(timezone.utc),
                            "is_new_signal": False,
                        }
                    )
                    inserted_count += 1

    if ae_records:
        db_session.execute(
            sql_text(
                """
                INSERT INTO ae_signals
                    (post_id, drug_name, ae_term, ae_normalized, severity, confidence, temporal_marker, detected_at, is_new_signal)
                VALUES
                    (:post_id, :drug_name, :ae_term, :ae_normalized, :severity, :confidence, :temporal_marker, :detected_at, :is_new_signal)
                """
            ),
            ae_records,
        )
        db_session.commit()

    logger.info(
        "AE extraction complete: %s posts -> %s signals in %.1fs",
        len(posts),
        inserted_count,
        time.time() - batch_start,
    )
    return inserted_count


def process_unprocessed_posts() -> int:
    """
    Batch process processed_posts that do not yet have ae_signals rows.
    """
    db = SessionLocal()
    total_inserted = 0

    try:
        while True:
            rows = db.execute(
                sql_text(
                    """
                    SELECT pp.id, pp.cleaned_text
                    FROM processed_posts pp
                    LEFT JOIN ae_signals ae ON ae.post_id = pp.id
                    WHERE ae.id IS NULL
                    ORDER BY pp.id
                    LIMIT :limit
                    """
                ),
                {"limit": BATCH_SIZE},
            ).mappings().all()

            if not rows:
                break

            posts = []
            for row in rows:
                drugs = db.execute(
                    sql_text(
                        """
                        SELECT DISTINCT drug_normalized
                        FROM drug_mentions
                        WHERE post_id = :post_id
                        """
                    ),
                    {"post_id": row["id"]},
                ).scalars().all()
                posts.append(
                    {
                        "id": row["id"],
                        "clean_text": row["cleaned_text"],
                        "drug_mentions": drugs,
                    }
                )

            total_inserted += process_batch(posts, db)

        return total_inserted
    finally:
        db.close()


def analyze_text_realtime(text: str) -> Dict:
    """
    Analyze a single text for adverse events using DistilBERT embeddings.
    """
    _load_distilbert()
    start = time.time()

    spans = extract_ae_spans(text)
    spans = _compute_span_confidence(
        text,
        spans,
        _distilbert_tokenizer,
        _distilbert_model,
        _distilbert_seed_embeddings,
    )

    adverse_events = []
    seen_normalized = set()
    for span in spans:
        if span["normalized"] in seen_normalized:
            continue
        seen_normalized.add(span["normalized"])
        adverse_events.append(
            {
                "ae_term": span["term"],
                "ae_normalized": span["normalized"],
                "severity": detect_severity(text, span["term"]),
                "confidence": span["confidence"],
            }
        )

    return {
        "adverse_events": adverse_events,
        "processing_time_ms": round((time.time() - start) * 1000, 1),
    }


class AEExtractor:
    """Wrapper class for backward compatibility with existing imports."""

    def __init__(self):
        self.initialized = False

    def initialize_biobert(self, model_path: str = None):
        _load_biobert()
        self.initialized = True

    def initialize_distilbert(self, model_path: str = None):
        _load_distilbert()
        self.initialized = True

    def extract_batch(self, texts: List[str]) -> List[List[Dict]]:
        _load_biobert()
        results = []
        for text in texts:
            spans = extract_ae_spans(text)
            spans = _compute_span_confidence(text, spans, _biobert_tokenizer, _biobert_model, _biobert_seed_embeddings)
            for span in spans:
                span["severity"] = detect_severity(text, span["term"])
            results.append(spans)
        return results

    def extract_realtime(self, text: str) -> List[Dict]:
        return analyze_text_realtime(text)["adverse_events"]

    def _classify_severity(self, ae_term: str, context: str) -> str:
        return detect_severity(context, ae_term)


ae_extractor = AEExtractor()
