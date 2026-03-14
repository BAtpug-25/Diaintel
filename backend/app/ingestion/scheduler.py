"""
DiaIntel - Scheduler
APScheduler-based task scheduling for data ingestion and NLP processing.
"""

import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.api.websocket import broadcast_processing_progress_sync
from app.config import settings

logger = logging.getLogger("diaintel.ingestion.scheduler")

_scheduler: BackgroundScheduler = None
_startup_lock = threading.Lock()
_startup_complete = False


def _run_initial_ingestion():
    """Run once on startup: load all unprocessed .zst files."""
    global _startup_complete

    with _startup_lock:
        if _startup_complete:
            logger.info("Initial ingestion already completed - skipping")
            return

        logger.info("=" * 60)
        logger.info("Scheduler: Starting initial data ingestion...")
        logger.info("=" * 60)
        broadcast_processing_progress_sync(0.0, "Initial ingestion started")

        try:
            from app.ingestion.pushshift_loader import load_all

            results = load_all(settings.PUSHSHIFT_DATA_DIR)
            total_inserted = sum(r.get("records_inserted", 0) for r in results)
            completed = sum(1 for r in results if r.get("status") in ("completed", "skipped"))

            logger.info("Initial ingestion done: %s/%s files, %s posts inserted", completed, len(results), f"{total_inserted:,}")
            broadcast_processing_progress_sync(100.0, "Initial ingestion complete", {"files": len(results), "posts_inserted": total_inserted})
        except Exception as exc:
            logger.error("Initial ingestion failed: %s", exc, exc_info=True)
            broadcast_processing_progress_sync(100.0, f"Initial ingestion failed: {exc}")

        _startup_complete = True


def _run_nlp_batch():
    """Periodic job: process unprocessed raw_posts through the NLP pipeline."""
    logger.info("Scheduler: Running NLP batch processing...")

    try:
        from app.nlp.pipeline import pipeline
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            processed_count = pipeline.process_batch(db, batch_size=settings.BATCH_SIZE)
            if processed_count > 0:
                logger.info("NLP batch complete: %s posts processed", processed_count)
            else:
                logger.debug("NLP batch: no unprocessed posts found")
        finally:
            db.close()

    except Exception as exc:
        logger.error("NLP batch processing failed: %s", exc, exc_info=True)


def start_scheduler():
    """Start the APScheduler jobs for ingestion and periodic NLP processing."""
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler already running")
        return

    logger.info("Starting scheduler...")

    _scheduler = BackgroundScheduler(
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 300,
        }
    )

    _scheduler.add_job(
        _run_initial_ingestion,
        trigger="date",
        id="initial_ingestion",
        name="Initial .zst Data Ingestion",
        replace_existing=True,
    )

    _scheduler.add_job(
        _run_nlp_batch,
        trigger=IntervalTrigger(minutes=30),
        id="nlp_batch_processing",
        name="NLP Batch Processing",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Scheduler started with 2 jobs:")
    logger.info("  1. Initial ingestion (runs now)")
    logger.info("  2. NLP batch processing (every 30 min)")


def stop_scheduler():
    """Gracefully stop the scheduler."""
    global _scheduler

    if _scheduler is not None:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")
        except Exception as exc:
            logger.warning("Error stopping scheduler: %s", exc)
        finally:
            _scheduler = None


def get_scheduler_status() -> dict:
    """Get current scheduler status and job info."""
    if _scheduler is None:
        return {"running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
        )

    return {
        "running": _scheduler.running,
        "startup_complete": _startup_complete,
        "jobs": jobs,
    }
