"""
DiaIntel — Combination Detector
Detects drug combinations from a processed post and updates drug_combinations.
"""

import itertools
import logging
from typing import List

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

    unique_drugs = sorted({mention for mention in mentions if mention})
    if len(unique_drugs) < 2:
        return 0

    score = _score_combo_text(text or "")
    if score < 0.4:
        return 0

    records = []
    for drug_1, drug_2 in itertools.combinations(unique_drugs, 2):
        ordered_pair: List[str] = sorted([drug_1, drug_2])
        records.append(
            {
                "drug_1": ordered_pair[0],
                "drug_2": ordered_pair[1],
                "concurrency_score": round(score, 4),
                "example_post_id": post_id,
            }
        )

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
        records,
    )
    return len(records)
