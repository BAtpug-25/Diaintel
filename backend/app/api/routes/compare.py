"""
DiaIntel — Compare Routes
API endpoints for side-by-side drug comparison.
"""

import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pydantic_models import DrugComparison
from app.utils.cache import get_cached_json, set_cached_json

router = APIRouter()


@router.get("/compare", response_model=DrugComparison)
async def compare_drugs(
    drugs: str = Query(..., description="Comma-separated drug names, e.g., metformin,ozempic"),
    db: Session = Depends(get_db),
):
    start_time = time.time()
    drug_list = [drug.strip().lower() for drug in drugs.split(",") if drug.strip()]
    if len(drug_list) < 2:
        raise HTTPException(status_code=400, detail="At least 2 drugs required for comparison")

    cache_key = "compare:" + ",".join(sorted(drug_list))
    cached = await get_cached_json(cache_key)
    if cached:
        cached["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached

    ae_rows = db.execute(
        sql_text(
            """
            SELECT drug_name, COALESCE(ae_normalized, ae_term) AS ae_term, COUNT(*) AS count
            FROM ae_signals
            WHERE drug_name = ANY(:drug_names)
            GROUP BY drug_name, COALESCE(ae_normalized, ae_term)
            ORDER BY ae_term, count DESC
            """
        ),
        {"drug_names": drug_list},
    ).mappings().all()

    ae_matrix = {}
    for row in ae_rows:
        ae_matrix.setdefault(row["ae_term"], {})
        ae_matrix[row["ae_term"]][row["drug_name"]] = int(row["count"])

    common_aes = [
        {"ae_term": ae_term, "counts": counts}
        for ae_term, counts in ae_matrix.items()
        if len(counts) > 1
    ]
    common_aes.sort(key=lambda item: sum(item["counts"].values()), reverse=True)

    sentiment_rows = db.execute(
        sql_text(
            """
            SELECT drug_name,
                   ROUND(AVG(sentiment_score)::numeric, 4) AS avg_score,
                   MODE() WITHIN GROUP (ORDER BY sentiment_label) AS dominant_label
            FROM sentiment_scores
            WHERE drug_name = ANY(:drug_names)
            GROUP BY drug_name
            """
        ),
        {"drug_names": drug_list},
    ).mappings().all()

    post_volume_rows = db.execute(
        sql_text(
            """
            SELECT drug_normalized AS drug_name, COUNT(DISTINCT post_id) AS post_volume
            FROM drug_mentions
            WHERE drug_normalized = ANY(:drug_names)
            GROUP BY drug_normalized
            """
        ),
        {"drug_names": drug_list},
    ).mappings().all()

    payload = {
        "drug_1": drug_list[0],
        "drug_2": drug_list[1],
        "compared_drugs": drug_list,
        "common_aes": common_aes[:15],
        "sentiment_comparison": {
            row["drug_name"]: {
                "avg_sentiment": float(row["avg_score"] or 0.0),
                "dominant_label": row["dominant_label"],
            }
            for row in sentiment_rows
        },
        "ae_frequency_diff": ae_matrix,
        "post_volume": {row["drug_name"]: int(row["post_volume"]) for row in post_volume_rows},
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    await set_cached_json(cache_key, payload, 300)
    return payload
