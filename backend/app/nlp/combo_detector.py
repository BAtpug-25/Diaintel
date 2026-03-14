"""
DiaIntel - Combination Detector
Detects drug combinations from a processed post and updates drug_combinations.
"""

import itertools
import logging
from typing import Dict, List

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

logger = logging.getLogger("diaintel.nlp.combo_detector")

CONCURRENCY_TERMS = ["with", "and", "plus", "+", "together", "alongside", "combining", "both"]
SEQUENTIAL_TERMS = ["switched from", "replaced", "instead of", "stopped"]


def _score_combo_text(text: str) -> float:
    lower_text = text.lower()
    score = 0.5
    score += 0.2 * sum(lower_text.count(term) for term in CONCURRENCY_TERMS)
    score -= 0.3 * sum(lower_text.count(term) for term in SEQUENTIAL_TERMS)
    return max(0.0, min(1.0, score))


def detect_combinations(drug_names: List[str], text: str) -> List[Dict]:
    """Return concurrent drug pairs inferred from a text window."""
    unique_drugs = sorted({drug for drug in drug_names if drug})
    if len(unique_drugs) < 2:
        return []

    score = _score_combo_text(text or "")
    if score < 0.4:
        return []

    return [
        {
            "drug_1": pair[0],
            "drug_2": pair[1],
            "concurrency_score": round(score, 4),
        }
        for pair in itertools.combinations(unique_drugs, 2)
    ]


def detect_combos_for_post(post_id: int, text: str, db: Session) -> int:
    """
    Detect co-mentioned drug pairs for a processed post.
    """
    mentions = db.execute(
        sql_text(
            """
            SELECT DISTINCT drug_normalized
            FROM drug_mentions
            WHERE post_id = :post_id
            ORDER BY drug_normalized
            """
        ),
        {"post_id": post_id},
    ).scalars().all()

    records = detect_combinations(list(mentions), text)
    if not records:
        return 0

    db.execute(
        sql_text(
            """
            INSERT INTO drug_combinations
                (drug_1, drug_2, post_count, concurrency_score, example_post_id, first_detected, last_updated)
            VALUES
                (:drug_1, :drug_2, 1, :concurrency_score, :example_post_id, NOW(), NOW())
            ON CONFLICT (drug_1, drug_2) DO UPDATE
            SET post_count = drug_combinations.post_count + 1,
                concurrency_score =
                    ((drug_combinations.concurrency_score * drug_combinations.post_count) + EXCLUDED.concurrency_score)
                    / (drug_combinations.post_count + 1),
                last_updated = NOW()
            """
        ),
        [
            {
                "drug_1": row["drug_1"],
                "drug_2": row["drug_2"],
                "concurrency_score": row["concurrency_score"],
                "example_post_id": post_id,
            }
            for row in records
        ],
    )
    return len(records)
