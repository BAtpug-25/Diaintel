"""
DiaIntel — Drug Named Entity Recognition
Extracts drug names and dosages using custom NER + RxNorm lexicon.

Target drugs (with brand/generic variants):
- Metformin → glucophage, glumetza, fortamet
- Ozempic → semaglutide, wegovy
- Jardiance → empagliflozin
- Januvia → sitagliptin
- Farxiga → dapagliflozin
- Trulicity → dulaglutide
- Victoza → liraglutide
- Glipizide → glucotrol

Implemented in Step 3.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger("diaintel.nlp.drug_ner")

# Drug name mapping: all variants → normalized name
DRUG_LEXICON = {
    # Metformin
    "metformin": "metformin",
    "glucophage": "metformin",
    "glumetza": "metformin",
    "fortamet": "metformin",
    # Ozempic / Semaglutide
    "ozempic": "semaglutide",
    "semaglutide": "semaglutide",
    "wegovy": "semaglutide",
    # Jardiance / Empagliflozin
    "jardiance": "empagliflozin",
    "empagliflozin": "empagliflozin",
    # Januvia / Sitagliptin
    "januvia": "sitagliptin",
    "sitagliptin": "sitagliptin",
    # Farxiga / Dapagliflozin
    "farxiga": "dapagliflozin",
    "dapagliflozin": "dapagliflozin",
    # Trulicity / Dulaglutide
    "trulicity": "dulaglutide",
    "dulaglutide": "dulaglutide",
    # Victoza / Liraglutide
    "victoza": "liraglutide",
    "liraglutide": "liraglutide",
    # Glipizide
    "glipizide": "glipizide",
    "glucotrol": "glipizide",
}

# Common drug display names
DRUG_DISPLAY_NAMES = {
    "metformin": "Metformin",
    "semaglutide": "Ozempic",
    "empagliflozin": "Jardiance",
    "sitagliptin": "Januvia",
    "dapagliflozin": "Farxiga",
    "dulaglutide": "Trulicity",
    "liraglutide": "Victoza",
    "glipizide": "Glipizide",
}

# Dosage pattern
DOSAGE_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?)\s*(mg|mcg|ml|units?|iu)\b',
    re.IGNORECASE
)

# Frequency patterns
FREQUENCY_PATTERNS = [
    (re.compile(r'twice\s+(?:a\s+)?daily', re.I), "twice daily"),
    (re.compile(r'once\s+(?:a\s+)?daily', re.I), "once daily"),
    (re.compile(r'once\s+(?:a\s+)?week(?:ly)?', re.I), "weekly"),
    (re.compile(r'twice\s+(?:a\s+)?week(?:ly)?', re.I), "twice weekly"),
    (re.compile(r'daily', re.I), "daily"),
    (re.compile(r'weekly', re.I), "weekly"),
    (re.compile(r'every\s+(?:other\s+)?day', re.I), "every other day"),
]


class DrugNER:
    """Extracts drug mentions, dosages, and frequencies from text."""

    def __init__(self):
        # Build regex pattern for all drug names
        drug_names = sorted(DRUG_LEXICON.keys(), key=len, reverse=True)
        pattern = r'\b(' + '|'.join(re.escape(d) for d in drug_names) + r')\b'
        self.drug_pattern = re.compile(pattern, re.IGNORECASE)
        logger.info(f"DrugNER initialized with {len(DRUG_LEXICON)} drug variants")

    def extract(self, text: str) -> List[Dict]:
        """
        Extract drug mentions from text.

        Returns list of dicts with:
            drug_name, drug_normalized, dosage, frequency, confidence
        """
        # TODO: Full implementation with spaCy in Step 3
        # For now, regex-based extraction

        mentions = []
        seen_drugs = set()

        for match in self.drug_pattern.finditer(text):
            drug_raw = match.group(1).lower()
            drug_normalized = DRUG_LEXICON.get(drug_raw, drug_raw)

            if drug_normalized in seen_drugs:
                continue
            seen_drugs.add(drug_normalized)

            # Look for dosage near the drug mention
            context = text[max(0, match.start() - 50):match.end() + 50]
            dosage = self._extract_dosage(context)
            frequency = self._extract_frequency(context)

            mentions.append({
                "drug_name": drug_raw,
                "drug_normalized": drug_normalized,
                "dosage": dosage,
                "frequency": frequency,
                "confidence": 0.95,  # High confidence for exact match
            })

        return mentions

    def _extract_dosage(self, context: str) -> Optional[str]:
        """Extract dosage from text context around a drug mention."""
        match = DOSAGE_PATTERN.search(context)
        if match:
            return match.group(0).strip()
        return None

    def _extract_frequency(self, context: str) -> Optional[str]:
        """Extract frequency from text context around a drug mention."""
        for pattern, freq_label in FREQUENCY_PATTERNS:
            if pattern.search(context):
                return freq_label
        return None

    def contains_target_drug(self, text: str) -> bool:
        """Quick check if text mentions any target drug."""
        return bool(self.drug_pattern.search(text))


# Singleton
drug_ner = DrugNER()
