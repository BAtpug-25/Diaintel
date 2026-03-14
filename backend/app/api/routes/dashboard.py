"""
DiaIntel — Dashboard Routes
API endpoints for dashboard statistics, trending AEs, traceability, and ingestion.
"""

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pydantic_models import AETrace, DashboardStats, IngestionStatus, TrendingResponse
from app.utils.cache import get_cached_json, set_cached_json

router = APIRouter()


def _trending_query():
    return sql_text(
        """
        SELECT COALESCE(ae_normalized, ae_term) AS ae_term, COUNT(*) AS count
        FROM ae_signals
        WHERE detected_at >= NOW() - INTERVAL '30 days'
        GROUP BY COALESCE(ae_normalized, ae_term)
        ORDER BY count DESC, ae_term
        LIMIT 10
        """
    )


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    start_time = time.time()
    cache_key = "dashboard:stats"

    cached = await get_cached_json(cache_key)
    if cached:
        cached["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached

    total_posts = int(db.execute(sql_text("SELECT COUNT(*) FROM raw_posts")).scalar() or 0)
    total_ae_signals = int(db.execute(sql_text("SELECT COUNT(*) FROM ae_signals")).scalar() or 0)
    total_drugs = int(db.execute(sql_text("SELECT COUNT(DISTINCT drug_normalized) FROM drug_mentions")).scalar() or 0)
    trending_rows = db.execute(_trending_query()).mappings().all()

    sentiment_rows = db.execute(
        sql_text(
            """
            SELECT drug_name, ROUND(AVG(sentiment_score)::numeric, 4) AS avg_sentiment
            FROM sentiment_scores
            GROUP BY drug_name
            ORDER BY avg_sentiment DESC, drug_name
            LIMIT 10
            """
        )
    ).mappings().all()

    payload = {
        "total_posts": total_posts,
        "total_ae_signals": total_ae_signals,
        "total_drugs": total_drugs,
        "trending_aes": [{"ae_term": row["ae_term"], "count": int(row["count"])} for row in trending_rows],
        "sentiment_overview": {
            row["drug_name"]: float(row["avg_sentiment"] or 0.0) for row in sentiment_rows
        },
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    await set_cached_json(cache_key, payload, 60)
    return payload


@router.get("/trending", response_model=TrendingResponse)
async def get_trending_aes(db: Session = Depends(get_db)):
    start_time = time.time()
    cache_key = "dashboard:trending"

    cached = await get_cached_json(cache_key)
    if cached:
        cached["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached

    rows = db.execute(_trending_query()).mappings().all()
    payload = {
        "trending_aes": [{"ae_term": row["ae_term"], "count": int(row["count"])} for row in rows],
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    await set_cached_json(cache_key, payload, 300)
    return payload


@router.get("/ae/trace/{ae_id}", response_model=AETrace)
async def get_ae_trace(ae_id: int, db: Session = Depends(get_db)):
    start_time = time.time()

    row = db.execute(
        sql_text(
            """
            SELECT
                ae.id AS ae_id,
                ae.post_id,
                rp.body AS original_text,
                ae.drug_name,
                ae.ae_term,
                ae.ae_normalized,
                ae.severity,
                ae.confidence,
                ae.temporal_marker,
                rp.subreddit
            FROM ae_signals ae
            JOIN processed_posts pp ON pp.id = ae.post_id
            JOIN raw_posts rp ON rp.id = pp.raw_post_id
            WHERE ae.id = :ae_id
            """
        ),
        {"ae_id": ae_id},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail=f"AE signal {ae_id} not found")

    related_drugs = db.execute(
        sql_text("SELECT DISTINCT drug_normalized FROM drug_mentions WHERE post_id = :post_id"),
        {"post_id": row["post_id"]},
    ).scalars().all()

    payload = {
        "ae_id": row["ae_id"],
        "post_id": str(row["post_id"]),
        "original_text": row["original_text"],
        "drug_name": row["drug_name"],
        "ae_term": row["ae_term"],
        "ae_normalized": row["ae_normalized"],
        "severity": row["severity"],
        "confidence": float(row["confidence"] or 0.0),
        "subreddit": row["subreddit"],
        "temporal_marker": row["temporal_marker"],
        "related_drugs": related_drugs,
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    return payload


@router.get("/ingestion/status", response_model=IngestionStatus)
async def get_ingestion_status(db: Session = Depends(get_db)):
    start_time = time.time()
    rows = db.execute(
        sql_text(
            """
            SELECT filename, records_read, records_inserted, started_at, completed_at, status
            FROM ingestion_log
            ORDER BY started_at DESC, id DESC
            """
        )
    ).mappings().all()

    return {
        "files": [
            {
                "filename": row["filename"],
                "records_read": int(row["records_read"] or 0),
                "records_inserted": int(row["records_inserted"] or 0),
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "status": row["status"],
            }
            for row in rows
        ],
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
