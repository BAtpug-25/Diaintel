"""
DiaIntel - Drug catalog helpers.
Shared normalization and metadata utilities for drug-aware routes.
"""

from __future__ import annotations

from app.nlp.drug_ner import DRUG_DISPLAY_NAMES, DRUG_LEXICON


DRUG_METADATA = {
    "metformin": {
        "drug_class": "Biguanide",
        "brand_names": ["Glucophage", "Glumetza", "Fortamet", "Riomet"],
    },
    "semaglutide": {
        "drug_class": "GLP-1 RA",
        "brand_names": ["Ozempic", "Wegovy", "Rybelsus"],
    },
    "empagliflozin": {
        "drug_class": "SGLT2 Inhibitor",
        "brand_names": ["Jardiance"],
    },
    "sitagliptin": {
        "drug_class": "DPP-4 Inhibitor",
        "brand_names": ["Januvia", "Janumet"],
    },
    "dapagliflozin": {
        "drug_class": "SGLT2 Inhibitor",
        "brand_names": ["Farxiga", "Forxiga"],
    },
    "dulaglutide": {
        "drug_class": "GLP-1 RA",
        "brand_names": ["Trulicity"],
    },
    "liraglutide": {
        "drug_class": "GLP-1 RA",
        "brand_names": ["Victoza", "Saxenda"],
    },
    "glipizide": {
        "drug_class": "Sulfonylurea",
        "brand_names": ["Glucotrol"],
    },
}


def normalize_drug_name(name: str) -> str:
    """Map a route parameter or user-facing name to the stored normalized drug key."""
    lowered = (name or "").strip().lower()
    return DRUG_LEXICON.get(lowered, lowered)


def get_drug_metadata(name: str) -> dict:
    normalized = normalize_drug_name(name)
    metadata = DRUG_METADATA.get(normalized, {}).copy()
    metadata.setdefault("drug_class", None)
    metadata.setdefault("brand_names", [])
    metadata["display_name"] = DRUG_DISPLAY_NAMES.get(normalized, normalized.title())
    metadata["normalized_name"] = normalized
    return metadata
