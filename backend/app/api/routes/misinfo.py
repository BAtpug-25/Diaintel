"""
DiaIntel — Misinformation Routes
API endpoints for the misinformation monitor feed and review workflow.
"""

import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pydantic_models import MisinfoFeed
from app.utils.cache import get_cached_json, set_cached_json

router = APIRouter()


@router.get("/misinfo/feed", response_model=MisinfoFeed)
async def get_misinfo_feed(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence filter"),
    reviewed: bool = Query(None, description="Filter by reviewed status"),
    db: Session = Depends(get_db),
):
    start_time = time.time()
    reviewed_key = "all" if reviewed is None else str(reviewed).lower()
    cache_key = f"misinfo:feed:{page}:{page_size}:{min_confidence}:{reviewed_key}"

    cached = await get_cached_json(cache_key)
    if cached:
        cached["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached

    conditions = ["mf.confidence >= :min_confidence"]
    params = {
        "min_confidence": min_confidence,
        "limit": page_size,
        "offset": (page - 1) * page_size,
    }
    if reviewed is not None:
        conditions.append("mf.reviewed = :reviewed")
        params["reviewed"] = reviewed

    where_clause = " AND ".join(conditions)
    total = int(
        db.execute(
            sql_text(f"SELECT COUNT(*) FROM misinfo_flags mf WHERE {where_clause}"),
            params,
        ).scalar()
        or 0
    )

    rows = db.execute(
        sql_text(
            f"""
            SELECT
                mf.id,
                mf.post_id,
                mf.claim_text,
                mf.flag_reason,
                mf.confidence,
                mf.flagged_at,
                mf.reviewed,
                LEFT(pp.cleaned_text, 280) AS excerpt
            FROM misinfo_flags mf
            JOIN processed_posts pp ON pp.id = mf.post_id
            WHERE {where_clause}
            ORDER BY mf.flagged_at DESC, mf.id DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    payload = {
        "flags": [
            {
                "id": row["id"],
                "post_id": row["post_id"],
                "claim_text": row["claim_text"],
                "flag_reason": row["flag_reason"],
                "confidence": float(row["confidence"] or 0.0),
                "flagged_at": row["flagged_at"],
                "reviewed": bool(row["reviewed"]),
                "excerpt": row["excerpt"],
            }
            for row in rows
        ],
        "total": total,
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    await set_cached_json(cache_key, payload, 60)
    return payload


@router.patch("/misinfo/{flag_id}/review")
async def mark_as_reviewed(flag_id: int, db: Session = Depends(get_db)):
    start_time = time.time()
    updated = db.execute(
        sql_text(
            """
            UPDATE misinfo_flags
            SET reviewed = TRUE
            WHERE id = :flag_id
            RETURNING id
            """
        ),
        {"flag_id": flag_id},
    ).first()
    if not updated:
        raise HTTPException(status_code=404, detail=f"Misinformation flag {flag_id} not found")

    db.commit()
    return {
        "flag_id": flag_id,
        "reviewed": True,
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
