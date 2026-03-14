"""
DiaIntel — Adverse Event Extractor
Extracts adverse events using BioBERT (batch) and DistilBERT (real-time).

BioBERT (dmis-lab/biobert-base-cased-v1.2):
- Used for batch processing of historical posts
- Higher accuracy, slower inference

DistilBERT (distilbert-base-uncased):
- Used for real-time Live Analyzer only
- Must complete in under 3 seconds
- Faster inference, slightly lower accuracy

Implemented in Step 4.
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger("diaintel.nlp.ae_extractor")


# Common adverse event terms for T2D medications
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
]


class AEExtractor:
    """Extracts adverse events from text using BioBERT/DistilBERT."""

    def __init__(self):
        self.biobert_model = None
        self.distilbert_model = None
        self.initialized = False
        logger.info("AEExtractor created (models not loaded)")

    def initialize_biobert(self, model_path: str):
        """Load BioBERT model for batch processing."""
        # TODO: Implement in Step 4
        logger.info(f"BioBERT loading from {model_path} (placeholder)")
        self.initialized = True

    def initialize_distilbert(self, model_path: str):
        """Load DistilBERT model for real-time processing."""
        # TODO: Implement in Step 4
        logger.info(f"DistilBERT loading from {model_path} (placeholder)")

    def extract_batch(self, texts: List[str]) -> List[List[Dict]]:
        """
        Extract AEs from a batch of texts using BioBERT.

        Returns list of lists of AE dicts per text.
        """
        # TODO: Implement in Step 4
        logger.info(f"Batch AE extraction for {len(texts)} texts (placeholder)")
        return [[] for _ in texts]

    def extract_realtime(self, text: str) -> List[Dict]:
        """
        Extract AEs from a single text using DistilBERT.
        Must complete in under 3 seconds.

        Returns list of AE dicts with:
            ae_term, severity, confidence
        """
        # TODO: Implement in Step 4
        logger.info("Real-time AE extraction (placeholder)")
        return []

    def _classify_severity(self, ae_term: str, context: str) -> str:
        """Classify severity based on context clues."""
        # TODO: Implement in Step 4
        return "unknown"


# Singleton
ae_extractor = AEExtractor()
