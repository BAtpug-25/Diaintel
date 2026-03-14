"""
DiaIntel - Drug routes.
API endpoints for drug insights, timelines, outcomes, and timeline insights.
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pydantic_models import DrugInsights, DrugOutcomes, DrugTimeline, DrugTimelineInsights
from app.utils.cache import get_cached_json, set_cached_json
from app.utils.drug_catalog import get_drug_metadata, normalize_drug_name

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


def _label_from_score(score: float) -> str:
    if score >= 0.15:
        return "positive"
    if score <= -0.15:
        return "negative"
    return "neutral"


@router.get("/drug/{drug_name}/insights", response_model=DrugInsights)
async def get_drug_insights(drug_name: str, db: Session = Depends(get_db)):
    start_time = time.time()
    normalized_drug = normalize_drug_name(drug_name)
    metadata = get_drug_metadata(normalized_drug)
    cache_key = f"drug:insights:{normalized_drug}"

    cached = await get_cached_json(cache_key)
    if cached:
        cached["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached

    total_posts = int(
        db.execute(
            sql_text(
                """
                SELECT COUNT(DISTINCT post_id)
                FROM drug_mentions
                WHERE drug_normalized = :drug_name
                """
            ),
            {"drug_name": normalized_drug},
        ).scalar()
        or 0
    )

    sentiment_score = float(
        db.execute(
            sql_text(
                """
                SELECT COALESCE(ROUND(AVG(sentiment_score)::numeric, 4), 0.0)
                FROM sentiment_scores
                WHERE drug_name = :drug_name
                """
            ),
            {"drug_name": normalized_drug},
        ).scalar()
        or 0.0
    )

    last_signal_time = db.execute(
        sql_text("SELECT MAX(detected_at) FROM ae_signals WHERE drug_name = :drug_name"),
        {"drug_name": normalized_drug},
    ).scalar()

    ae_rows = db.execute(
        sql_text(
            """
            SELECT
                COALESCE(ae_normalized, ae_term) AS ae_term,
                COUNT(*) AS count,
                ROUND(AVG(confidence)::numeric, 4) AS confidence,
                SUM(CASE WHEN severity = 'mild' THEN 1 ELSE 0 END) AS mild_count,
                SUM(CASE WHEN severity = 'moderate' THEN 1 ELSE 0 END) AS moderate_count,
                SUM(CASE WHEN severity = 'severe' THEN 1 ELSE 0 END) AS severe_count
            FROM ae_signals
            WHERE drug_name = :drug_name
            GROUP BY COALESCE(ae_normalized, ae_term)
            ORDER BY count DESC, ae_term
            LIMIT 10
            """
        ),
        {"drug_name": normalized_drug},
    ).mappings().all()

    severity_row = db.execute(
        sql_text(
            """
            SELECT
                SUM(CASE WHEN severity = 'mild' THEN 1 ELSE 0 END) AS mild_count,
                SUM(CASE WHEN severity = 'moderate' THEN 1 ELSE 0 END) AS moderate_count,
                SUM(CASE WHEN severity = 'severe' THEN 1 ELSE 0 END) AS severe_count
            FROM ae_signals
            WHERE drug_name = :drug_name
            """
        ),
        {"drug_name": normalized_drug},
    ).mappings().first() or {}

    payload = {
        "drug_name": normalized_drug,
        "display_name": metadata["display_name"],
        "total_posts": total_posts,
        "overall_sentiment": sentiment_score,
        "sentiment_label": _label_from_score(sentiment_score),
        "top_adverse_events": [
            {
                "ae_term": row["ae_term"],
                "count": int(row["count"]),
                "confidence": float(row["confidence"] or 0.0),
                "severity_breakdown": {
                    "mild": int(row["mild_count"] or 0),
                    "moderate": int(row["moderate_count"] or 0),
                    "severe": int(row["severe_count"] or 0),
                },
            }
            for row in ae_rows
        ],
        "severity_breakdown": {
            "mild": int(severity_row.get("mild_count") or 0),
            "moderate": int(severity_row.get("moderate_count") or 0),
            "severe": int(severity_row.get("severe_count") or 0),
        },
        "last_signal_time": last_signal_time,
        "drug_class": metadata["drug_class"],
        "brand_names": metadata["brand_names"],
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }

    await set_cached_json(cache_key, payload, 300)
    return payload


@router.get("/drug/{drug_name}/timeline", response_model=DrugTimeline)
async def get_drug_timeline(drug_name: str, db: Session = Depends(get_db)):
    start_time = time.time()
    normalized_drug = normalize_drug_name(drug_name)
    metadata = get_drug_metadata(normalized_drug)
    cache_key = f"drug:timeline:{normalized_drug}"

    cached = await get_cached_json(cache_key)
    if cached:
        cached["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached

    sentiment_rows = db.execute(
        sql_text(
            """
            SELECT
                TO_CHAR(date_trunc('month', scored_at), 'YYYY-MM') AS month,
                sentiment_label,
                COUNT(*) AS label_count
            FROM sentiment_scores
            WHERE drug_name = :drug_name
              AND scored_at >= NOW() - INTERVAL '12 months'
            GROUP BY 1, sentiment_label
            ORDER BY 1, sentiment_label
            """
        ),
        {"drug_name": normalized_drug},
    ).mappings().all()

    sentiment_map = {}
    for row in sentiment_rows:
        sentiment_map.setdefault(row["month"], {"positive": 0, "negative": 0, "neutral": 0})
        sentiment_map[row["month"]][row["sentiment_label"]] = int(row["label_count"] or 0)

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
    ae_map = {row["month"]: int(row["ae_count"] or 0) for row in ae_rows}

    post_rows = db.execute(
        sql_text(
            """
            SELECT TO_CHAR(date_trunc('month', detected_at), 'YYYY-MM') AS month,
                   COUNT(DISTINCT post_id) AS post_count
            FROM drug_mentions
            WHERE drug_normalized = :drug_name
              AND detected_at >= NOW() - INTERVAL '12 months'
            GROUP BY 1
            ORDER BY 1
            """
        ),
        {"drug_name": normalized_drug},
    ).mappings().all()
    post_map = {row["month"]: int(row["post_count"] or 0) for row in post_rows}

    timeline = []
    for month in _month_series(12):
        month_sentiment = sentiment_map.get(month, {})
        timeline.append(
            {
                "month": month,
                "positive_count": int(month_sentiment.get("positive", 0)),
                "negative_count": int(month_sentiment.get("negative", 0)),
                "neutral_count": int(month_sentiment.get("neutral", 0)),
                "ae_count": ae_map.get(month, 0),
                "post_count": post_map.get(month, 0),
            }
        )

    payload = {
        "drug_name": normalized_drug,
        "display_name": metadata["display_name"],
        "timeline": timeline,
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    await set_cached_json(cache_key, payload, 300)
    return payload


@router.get("/drug/{drug_name}/outcomes", response_model=DrugOutcomes)
async def get_drug_outcomes(drug_name: str, db: Session = Depends(get_db)):
    start_time = time.time()
    normalized_drug = normalize_drug_name(drug_name)
    metadata = get_drug_metadata(normalized_drug)
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

    summary = {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
    for row in rows:
        count = int(row["count"] or 0)
        summary[row["polarity"]] = summary.get(row["polarity"], 0) + count
        summary["total"] += count

    payload = {
        "drug_name": normalized_drug,
        "display_name": metadata["display_name"],
        "summary": summary,
        "top_categories": [
            {
                "outcome_category": row["outcome_category"],
                "polarity": row["polarity"],
                "count": int(row["count"] or 0),
                "avg_confidence": float(row["avg_confidence"] or 0.0),
            }
            for row in rows
        ],
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    await set_cached_json(cache_key, payload, 300)
    return payload


@router.get("/drug/{drug_name}/timeline-insights", response_model=DrugTimelineInsights)
async def get_timeline_insights(drug_name: str, db: Session = Depends(get_db)):
    start_time = time.time()
    normalized_drug = normalize_drug_name(drug_name)
    metadata = get_drug_metadata(normalized_drug)
    cache_key = f"drug:timeline_insights:{normalized_drug}"

    cached = await get_cached_json(cache_key)
    if cached:
        cached["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached

    ae_rows = db.execute(
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

    outcome_rows = db.execute(
        sql_text(
            """
            SELECT outcome_category, duration, COUNT(*) AS count
            FROM treatment_outcomes
            WHERE drug_name = :drug_name
              AND duration IS NOT NULL
              AND duration <> ''
            GROUP BY outcome_category, duration
            ORDER BY count DESC, outcome_category
            LIMIT 25
            """
        ),
        {"drug_name": normalized_drug},
    ).mappings().all()

    payload = {
        "drug_name": normalized_drug,
        "display_name": metadata["display_name"],
        "ae_timelines": [
            {
                "name": row["ae_term"],
                "temporal_marker": row["temporal_marker"],
                "count": int(row["count"] or 0),
                "kind": "ae",
            }
            for row in ae_rows
        ],
        "outcome_timelines": [
            {
                "name": row["outcome_category"],
                "temporal_marker": row["duration"],
                "count": int(row["count"] or 0),
                "kind": "outcome",
            }
            for row in outcome_rows
        ],
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
    }
    await set_cached_json(cache_key, payload, 300)
    return payload
