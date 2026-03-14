"""
DiaIntel — MedDRA Mapper
Maps extracted adverse event terms to MedDRA preferred terms.

Provides normalization of AE terms for consistent reporting.

Implemented in Step 3.
"""

import logging
from typing import Optional, Dict

logger = logging.getLogger("diaintel.utils.meddra_mapper")

# Simplified AE term normalization mapping
AE_NORMALIZATION = {
    # Gastrointestinal
    "nausea": "Nausea",
    "vomiting": "Vomiting",
    "diarrhea": "Diarrhoea",
    "diarrhoea": "Diarrhoea",
    "constipation": "Constipation",
    "bloating": "Abdominal distension",
    "stomach cramps": "Abdominal pain",
    "abdominal pain": "Abdominal pain",
    "stomach pain": "Abdominal pain",
    "stomach ache": "Abdominal pain",
    "gi issues": "Gastrointestinal disorder",
    "gi problems": "Gastrointestinal disorder",
    "appetite loss": "Decreased appetite",
    "loss of appetite": "Decreased appetite",

    # Neurological
    "headache": "Headache",
    "dizziness": "Dizziness",
    "dizzy": "Dizziness",
    "fatigue": "Fatigue",
    "tired": "Fatigue",
    "exhaustion": "Fatigue",
    "insomnia": "Insomnia",
    "anxiety": "Anxiety",
    "depression": "Depression",

    # Metabolic
    "weight loss": "Weight decreased",
    "weight gain": "Weight increased",
    "hypoglycemia": "Hypoglycaemia",
    "low blood sugar": "Hypoglycaemia",
    "dehydration": "Dehydration",

    # Musculoskeletal
    "muscle pain": "Myalgia",
    "joint pain": "Arthralgia",
    "back pain": "Back pain",

    # Dermatological
    "skin rash": "Rash",
    "rash": "Rash",
    "itching": "Pruritus",
    "injection site reaction": "Injection site reaction",

    # Other
    "hair loss": "Alopecia",
    "blurred vision": "Vision blurred",
    "dry mouth": "Dry mouth",
    "heart palpitations": "Palpitations",
    "chest pain": "Chest pain",
    "uti": "Urinary tract infection",
    "urinary tract infection": "Urinary tract infection",
}


class MedDRAMapper:
    """Maps raw AE terms to standardized MedDRA preferred terms."""

    def __init__(self):
        self.mapping = AE_NORMALIZATION
        logger.info(f"MedDRAMapper initialized with {len(self.mapping)} terms")

    def normalize(self, ae_term: str) -> str:
        """Normalize an AE term to MedDRA preferred term."""
        normalized = self.mapping.get(ae_term.lower().strip())
        if normalized:
            return normalized
        # Return title-cased version if not in mapping
        return ae_term.strip().title()

    def is_known_ae(self, term: str) -> bool:
        """Check if a term is a known adverse event."""
        return term.lower().strip() in self.mapping

    def get_all_terms(self) -> list:
        """Get all known AE terms."""
        return list(set(self.mapping.values()))


# Singleton
meddra_mapper = MedDRAMapper()
