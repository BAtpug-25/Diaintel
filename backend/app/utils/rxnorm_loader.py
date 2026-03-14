"""
DiaIntel — RxNorm Drug Loader
Loads and provides lookup for the RxNorm drug lexicon.

Maps drug brand names to normalized generic names.

Implemented in Step 3.
"""

import json
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger("diaintel.utils.rxnorm_loader")


class RxNormLoader:
    """Loads and queries the RxNorm drug name mapping."""

    def __init__(self):
        self.drug_map: Dict[str, str] = {}
        self.loaded = False

    def load(self, filepath: str = None):
        """Load drug mappings from rxnorm_drugs.json."""
        if filepath is None:
            filepath = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "data", "rxnorm_drugs.json"
            )

        try:
            with open(filepath, "r") as f:
                self.drug_map = json.load(f)
            self.loaded = True
            logger.info(f"Loaded {len(self.drug_map)} drug mappings from {filepath}")
        except FileNotFoundError:
            logger.warning(f"RxNorm file not found: {filepath}")
            self._load_defaults()
        except Exception as e:
            logger.error(f"Error loading RxNorm data: {e}")
            self._load_defaults()

    def _load_defaults(self):
        """Load default drug mappings as fallback."""
        self.drug_map = {
            "metformin": "metformin",
            "glucophage": "metformin",
            "glumetza": "metformin",
            "fortamet": "metformin",
            "ozempic": "semaglutide",
            "semaglutide": "semaglutide",
            "wegovy": "semaglutide",
            "jardiance": "empagliflozin",
            "empagliflozin": "empagliflozin",
            "januvia": "sitagliptin",
            "sitagliptin": "sitagliptin",
            "farxiga": "dapagliflozin",
            "dapagliflozin": "dapagliflozin",
            "trulicity": "dulaglutide",
            "dulaglutide": "dulaglutide",
            "victoza": "liraglutide",
            "liraglutide": "liraglutide",
            "glipizide": "glipizide",
            "glucotrol": "glipizide",
        }
        self.loaded = True
        logger.info("Loaded default drug mappings")

    def normalize(self, drug_name: str) -> Optional[str]:
        """Normalize a drug name to its generic equivalent."""
        if not self.loaded:
            self.load()
        return self.drug_map.get(drug_name.lower())

    def is_known_drug(self, name: str) -> bool:
        """Check if a name is a known drug."""
        if not self.loaded:
            self.load()
        return name.lower() in self.drug_map


# Singleton
rxnorm_loader = RxNormLoader()
