"""
DiaIntel — Drug Routes
API endpoints for drug insights, timelines, outcomes, and timeline insights.
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pydantic_models import DrugInsights, DrugTimeline
from app.utils.cache import get_cached_json, set_cached_json

router = APIRouter()


def _month_series(months: int = 12):
    now = datetime.now(timezone.utc)
    series = []
    year = now.year
    month = now.month
    for _ in range(months):
        series.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(series))


@router.get("/drug/{drug_name}/insights", response_model=DrugInsights)
async def get_drug_insights(drug_name: str, db: Session = Depends(get_db)):
    start_time = time.time()
    normalized_drug = drug_name.lower().strip()
    cache_key = f"drug:insights:{normalized_drug}"

    cached = await get_cached_json(cache_key)
    if cached:
        cached["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached

    stats_row = db.execute(
        sql_text(
            """
            SELECT total_posts, top_ae_json, avg_sentiment
            FROM drug_stats_cache
            WHERE drug_name = :drug_name
            """
        ),
        {"drug_name": normalized_drug},
    ).mappings().first()

    ae_rows = db.execute(
        sql_text(
            """
            SELECT
                COALESCE(ae_normalized, ae_term) AS ae_term,
                COUNT(*) AS count,
                ROUND(AVG(confidence)::numeric, 4) AS confidence,
                jsonb_object_agg(severity, severity_count) AS severity_breakdown
            FROM (
                SELECT
                    COALESCE(ae_normalized, ae_term) AS ae_normalized,
                    ae_term,
                    severity,
                    confidence,
                    COUNT(*) OVER (
                        PARTITION BY drug_name, COALESCE(ae_normalized, ae_term), severity
                    ) AS severity_count
                FROM ae_signals
                WHERE drug_name = :drug_name
            ) source
            GROUP BY COALESCE(ae_normalized, ae_term), ae_term
            ORDER BY count DESC, ae_term
            LIMIT 10
            """
        ),
        {"drug_name": normalized_drug},
    ).mappings().all()

    payload = {
        "drug": normalized_drug,
        "adverse_events": [
            {
                "ae_term": row["ae_term"],
                "count": row["count"],
                "confidence": float(row["confidence"] or 0.0),
                "severity_breakdown": row["severity_breakdown"] or {},
            }
            for row in ae_rows
        ],
        "sentiment_score": float(stats_row["avg_sentiment"]) if stats_row else None,
        "confidence": float(sum(row["confidence"] or 0 for row in ae_rows) / len(ae_rows)) if ae_rows else 0.0,
        "total_posts": int(stats_row["total_posts"]) if stats_row else 0,
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }

    await set_cached_json(cache_key, payload, 300)
    return payload


@router.get("/drug/{drug_name}/timeline", response_model=DrugTimeline)
async def get_drug_timeline(drug_name: str, db: Session = Depends(get_db)):
    start_time = time.time()
    normalized_drug = drug_name.lower().strip()
    cache_key = f"drug:timeline:{normalized_drug}"

    cached = await get_cached_json(cache_key)
    if cached:
        cached["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached

    sentiment_rows = db.execute(
        sql_text(
            """
            SELECT TO_CHAR(date_trunc('month', scored_at), 'YYYY-MM') AS month,
                   ROUND(AVG(sentiment_score)::numeric, 4) AS avg_sentiment
            FROM sentiment_scores
            WHERE drug_name = :drug_name
              AND scored_at >= NOW() - INTERVAL '12 months'
            GROUP BY 1
            ORDER BY 1
            """
        ),
        {"drug_name": normalized_drug},
    ).mappings().all()
    sentiment_map = {row["month"]: float(row["avg_sentiment"]) for row in sentiment_rows}

    ae_rows = db.execute(
        sql_text(
            """
            SELECT TO_CHAR(date_trunc('month', detected_at), 'YYYY-MM') AS month,
                   COUNT(*) AS ae_count
            FROM ae_signals
            WHERE drug_name = :drug_name
              AND detected_at >= NOW() - INTERVAL '12 months'
            GROUP BY 1
            ORDER BY 1
            """
        ),
        {"drug_name": normalized_drug},
    ).mappings().all()
    ae_map = {row["month"]: int(row["ae_count"]) for row in ae_rows}

    events = [
        {
            "month": month,
            "avg_sentiment": sentiment_map.get(month, 0.0),
            "ae_count": ae_map.get(month, 0),
        }
        for month in _month_series(12)
    ]

    payload = {
        "drug": normalized_drug,
        "events": events,
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    await set_cached_json(cache_key, payload, 300)
    return payload


@router.get("/drug/{drug_name}/outcomes")
async def get_drug_outcomes(drug_name: str, db: Session = Depends(get_db)):
    start_time = time.time()
    normalized_drug = drug_name.lower().strip()
    cache_key = f"drug:outcomes:{normalized_drug}"

    cached = await get_cached_json(cache_key)
    if cached:
        cached["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached

    rows = db.execute(
        sql_text(
            """
            SELECT outcome_category, polarity, COUNT(*) AS count, ROUND(AVG(confidence)::numeric, 4) AS avg_confidence
            FROM treatment_outcomes
            WHERE drug_name = :drug_name
            GROUP BY outcome_category, polarity
            ORDER BY count DESC, outcome_category
            """
        ),
        {"drug_name": normalized_drug},
    ).mappings().all()

    payload = {
        "drug": normalized_drug,
        "outcomes": [
            {
                "outcome_category": row["outcome_category"],
                "polarity": row["polarity"],
                "count": int(row["count"]),
                "avg_confidence": float(row["avg_confidence"] or 0.0),
            }
            for row in rows
        ],
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    await set_cached_json(cache_key, payload, 300)
    return payload


@router.get("/drug/{drug_name}/timeline-insights")
async def get_timeline_insights(drug_name: str, db: Session = Depends(get_db)):
    start_time = time.time()
    normalized_drug = drug_name.lower().strip()
    cache_key = f"drug:timeline_insights:{normalized_drug}"

    cached = await get_cached_json(cache_key)
    if cached:
        cached["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached

    rows = db.execute(
        sql_text(
            """
            SELECT
                COALESCE(ae_normalized, ae_term) AS ae_term,
                temporal_marker,
                COUNT(*) AS count
            FROM ae_signals
            WHERE drug_name = :drug_name
              AND temporal_marker IS NOT NULL
              AND temporal_marker <> ''
            GROUP BY COALESCE(ae_normalized, ae_term), temporal_marker
            ORDER BY count DESC, ae_term
            LIMIT 25
            """
        ),
        {"drug_name": normalized_drug},
    ).mappings().all()

    payload = {
        "drug": normalized_drug,
        "timeline_insights": [
            {
                "ae_term": row["ae_term"],
                "temporal_marker": row["temporal_marker"],
                "count": int(row["count"]),
            }
            for row in rows
        ],
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    await set_cached_json(cache_key, payload, 300)
    return payload
