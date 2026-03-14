"""
DiaIntel - Combination routes.
API endpoints for treatment combination insights.
"""

import time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pydantic_models import CombinationList
from app.utils.cache import get_cached_json, set_cached_json
from app.utils.drug_catalog import normalize_drug_name

router = APIRouter()


def _serialize_rows(rows):
    return [
        {
            "drug_1": row["drug_1"],
            "drug_2": row["drug_2"],
            "post_count": int(row["post_count"] or 0),
            "concurrency_score": float(row["concurrency_score"] or 0.0),
            "example_post_id": row["example_post_id"],
            "first_detected": row["first_detected"],
            "last_updated": row["last_updated"],
        }
        for row in rows
    ]


@router.get("/combinations", response_model=CombinationList)
async def get_combinations(
    min_count: int = Query(1, ge=1, description="Minimum co-report count"),
    db: Session = Depends(get_db),
):
    start_time = time.time()
    cache_key = f"combinations:all:{min_count}"

    cached = await get_cached_json(cache_key)
    if cached:
        cached["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached

    rows = db.execute(
        sql_text(
            """
            SELECT drug_1, drug_2, post_count, concurrency_score, example_post_id, first_detected, last_updated
            FROM drug_combinations
            WHERE post_count >= :min_count
            ORDER BY post_count DESC, drug_1, drug_2
            """
        ),
        {"min_count": min_count},
    ).mappings().all()

    payload = {
        "combinations": _serialize_rows(rows),
        "total": len(rows),
        "drug_name": None,
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    await set_cached_json(cache_key, payload, 300)
    return payload


@router.get("/combinations/{drug_name}", response_model=CombinationList)
async def get_combinations_for_drug(drug_name: str, db: Session = Depends(get_db)):
    start_time = time.time()
    normalized_drug = normalize_drug_name(drug_name)
    cache_key = f"combinations:{normalized_drug}"

    cached = await get_cached_json(cache_key)
    if cached:
        cached["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached

    rows = db.execute(
        sql_text(
            """
            SELECT drug_1, drug_2, post_count, concurrency_score, example_post_id, first_detected, last_updated
            FROM drug_combinations
            WHERE drug_1 = :drug_name OR drug_2 = :drug_name
            ORDER BY post_count DESC, drug_1, drug_2
            """
        ),
        {"drug_name": normalized_drug},
    ).mappings().all()

    payload = {
        "combinations": _serialize_rows(rows),
        "total": len(rows),
        "drug_name": normalized_drug,
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    await set_cached_json(cache_key, payload, 300)
    return payload
