"""
DiaIntel - Dashboard routes.
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


def _build_trending(rows):
    aggregated = {}
    for row in rows:
        ae_term = row["ae_term"]
        entry = aggregated.setdefault(
            ae_term,
            {"current_count": 0, "previous_count": 0, "drug_counts": {}},
        )
        current_count = int(row["current_count"] or 0)
        previous_count = int(row["previous_count"] or 0)
        entry["current_count"] += current_count
        entry["previous_count"] += previous_count
        entry["drug_counts"][row["drug_name"]] = entry["drug_counts"].get(row["drug_name"], 0) + current_count

    trending = []
    for ae_term, data in aggregated.items():
        current_count = data["current_count"]
        previous_count = data["previous_count"]
        if current_count == 0:
            continue
        baseline = previous_count or 1
        change_percent = round(((current_count - previous_count) / baseline) * 100, 2)
        top_drugs = [
            drug
            for drug, _ in sorted(data["drug_counts"].items(), key=lambda item: (-item[1], item[0]))[:3]
        ]
        trending.append(
            {
                "ae_term": ae_term,
                "current_count": current_count,
                "previous_count": previous_count,
                "change_percent": change_percent,
                "top_drugs": top_drugs,
            }
        )

    trending.sort(key=lambda item: (item["change_percent"], item["current_count"]), reverse=True)
    return trending[:10]


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
    last_updated = db.execute(sql_text("SELECT MAX(detected_at) FROM ae_signals")).scalar()

    trending_rows = db.execute(
        sql_text(
            """
            SELECT
                COALESCE(ae_normalized, ae_term) AS ae_term,
                drug_name,
                COUNT(*) FILTER (WHERE detected_at >= NOW() - INTERVAL '30 days') AS current_count,
                COUNT(*) FILTER (
                    WHERE detected_at >= NOW() - INTERVAL '60 days'
                      AND detected_at < NOW() - INTERVAL '30 days'
                ) AS previous_count
            FROM ae_signals
            GROUP BY COALESCE(ae_normalized, ae_term), drug_name
            """
        )
    ).mappings().all()
    trending = _build_trending(trending_rows)

    recent_rows = db.execute(
        sql_text(
            """
            SELECT id, drug_name, COALESCE(ae_normalized, ae_term) AS ae_term, confidence, severity, detected_at
            FROM ae_signals
            ORDER BY detected_at DESC, id DESC
            LIMIT 10
            """
        )
    ).mappings().all()

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
        "total_drugs_tracked": total_drugs,
        "last_updated": last_updated,
        "trending_aes": [
            {
                "ae_term": row["ae_term"],
                "count": int(row["current_count"]),
                "change_percent": float(row["change_percent"]),
            }
            for row in trending[:5]
        ],
        "recent_signals": [
            {
                "id": int(row["id"]),
                "drug_name": row["drug_name"],
                "ae_term": row["ae_term"],
                "confidence": float(row["confidence"] or 0.0),
                "severity": row["severity"],
                "detected_at": row["detected_at"],
            }
            for row in recent_rows
        ],
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

    rows = db.execute(
        sql_text(
            """
            SELECT
                COALESCE(ae_normalized, ae_term) AS ae_term,
                drug_name,
                COUNT(*) FILTER (WHERE detected_at >= NOW() - INTERVAL '30 days') AS current_count,
                COUNT(*) FILTER (
                    WHERE detected_at >= NOW() - INTERVAL '60 days'
                      AND detected_at < NOW() - INTERVAL '30 days'
                ) AS previous_count
            FROM ae_signals
            GROUP BY COALESCE(ae_normalized, ae_term), drug_name
            """
        )
    ).mappings().all()

    payload = {
        "trending": _build_trending(rows),
        "period_days": 30,
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
                ae.detected_at,
                rp.subreddit,
                rp.created_utc
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
        sql_text("SELECT DISTINCT drug_normalized FROM drug_mentions WHERE post_id = :post_id ORDER BY drug_normalized"),
        {"post_id": row["post_id"]},
    ).scalars().all()

    payload = {
        "ae_id": int(row["ae_id"]),
        "post_id": str(row["post_id"]),
        "original_text": row["original_text"],
        "drug_name": row["drug_name"],
        "ae_term": row["ae_term"],
        "ae_normalized": row["ae_normalized"],
        "severity": row["severity"],
        "confidence": float(row["confidence"] or 0.0),
        "subreddit": row["subreddit"],
        "temporal_marker": row["temporal_marker"],
        "post_timestamp": row["created_utc"],
        "detected_at": row["detected_at"],
        "related_drugs": list(related_drugs),
        "highlighted_entities": {
            "drugs": list(related_drugs),
            "adverse_events": [row["ae_term"], row["ae_normalized"]] if row["ae_normalized"] else [row["ae_term"]],
        },
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

    total_records_loaded = sum(int(row["records_inserted"] or 0) for row in rows)
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
        "total_records_loaded": total_records_loaded,
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
