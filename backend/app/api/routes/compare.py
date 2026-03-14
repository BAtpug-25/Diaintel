"""
DiaIntel - Compare routes.
API endpoints for side-by-side drug comparison.
"""

import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pydantic_models import DrugComparison
from app.utils.cache import get_cached_json, set_cached_json
from app.utils.drug_catalog import get_drug_metadata, normalize_drug_name

router = APIRouter()


@router.get("/compare", response_model=DrugComparison)
async def compare_drugs(
    drugs: str = Query(..., description="Comma-separated drug names, e.g., metformin,ozempic"),
    db: Session = Depends(get_db),
):
    start_time = time.time()
    drug_list = [normalize_drug_name(drug.strip()) for drug in drugs.split(",") if drug.strip()]
    if len(drug_list) != 2:
        raise HTTPException(status_code=400, detail="Exactly 2 drugs are required for comparison")

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
        ae_matrix.setdefault(row["ae_term"], {drug_list[0]: 0, drug_list[1]: 0})
        ae_matrix[row["ae_term"]][row["drug_name"]] = int(row["count"] or 0)

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
    sentiment_map = {
        row["drug_name"]: {
            "score": float(row["avg_score"] or 0.0),
            "label": row["dominant_label"] or "neutral",
        }
        for row in sentiment_rows
    }

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
    post_volume_map = {row["drug_name"]: int(row["post_volume"] or 0) for row in post_volume_rows}

    payload = {
        "drugs": [
            {
                "drug_name": drug_name,
                "display_name": get_drug_metadata(drug_name)["display_name"],
                "total_posts": post_volume_map.get(drug_name, 0),
                "sentiment_score": sentiment_map.get(drug_name, {}).get("score", 0.0),
                "dominant_label": sentiment_map.get(drug_name, {}).get("label", "neutral"),
            }
            for drug_name in drug_list
        ],
        "ae_matrix": [
            {"ae_term": ae_term, "counts": counts}
            for ae_term, counts in sorted(
                ae_matrix.items(),
                key=lambda item: sum(item[1].values()),
                reverse=True,
            )[:20]
        ],
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    await set_cached_json(cache_key, payload, 300)
    return payload
