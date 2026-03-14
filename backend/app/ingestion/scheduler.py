"""
DiaIntel — Scheduler
APScheduler-based task scheduling for data ingestion and NLP processing.

Startup behavior:
1. Triggers pushshift_loader once to load all unprocessed .zst files
2. Schedules NLP pipeline batch processing every 30 minutes

Uses BackgroundScheduler so it runs in a separate thread
and doesn't block the FastAPI event loop.
"""

import logging
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger("diaintel.ingestion.scheduler")

# Global scheduler reference
_scheduler: BackgroundScheduler = None
_startup_lock = threading.Lock()
_startup_complete = False


def _run_initial_ingestion():
    """
    Run on startup: load all unprocessed .zst files.

    This runs in a background thread so it doesn't block
    the FastAPI application startup.
    """
    global _startup_complete

    with _startup_lock:
        if _startup_complete:
            logger.info("Initial ingestion already completed — skipping")
            return

        logger.info("=" * 60)
        logger.info("Scheduler: Starting initial data ingestion...")
        logger.info("=" * 60)

        try:
            from app.ingestion.pushshift_loader import load_all
            results = load_all(settings.PUSHSHIFT_DATA_DIR)

            total_inserted = sum(r.get("records_inserted", 0) for r in results)
            completed = sum(1 for r in results if r.get("status") in ("completed", "skipped"))

            logger.info(f"Initial ingestion done: {completed}/{len(results)} files, {total_inserted:,} posts inserted")

        except Exception as e:
            logger.error(f"Initial ingestion failed: {e}", exc_info=True)

        _startup_complete = True


def _run_nlp_batch():
    """
    Periodic job: process unprocessed raw_posts through the NLP pipeline.

    Runs every 30 minutes after initial ingestion.
    """
    logger.info("Scheduler: Running NLP batch processing...")

    try:
        from app.nlp.pipeline import pipeline
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            processed_count = pipeline.process_batch(db, batch_size=settings.BATCH_SIZE)
            if processed_count > 0:
                logger.info(f"NLP batch complete: {processed_count} posts processed")
            else:
                logger.debug("NLP batch: no unprocessed posts found")
        finally:
            db.close()

    except Exception as e:
        logger.error(f"NLP batch processing failed: {e}", exc_info=True)


def start_scheduler():
    """
    Start the APScheduler with:
    1. Initial data ingestion job (runs once on startup, in background thread)
    2. NLP batch processing job (runs every 30 minutes)
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("Scheduler already running")
        return

    logger.info("Starting scheduler...")

    _scheduler = BackgroundScheduler(
        job_defaults={
            "coalesce": True,         # Combine missed runs into one
            "max_instances": 1,       # Only one instance of each job at a time
            "misfire_grace_time": 300, # 5 minute grace for missed jobs
        }
    )

    # Job 1: Initial data ingestion (run once, 5 seconds after startup)
    _scheduler.add_job(
        _run_initial_ingestion,
        trigger="date",  # One-time trigger
        id="initial_ingestion",
        name="Initial .zst Data Ingestion",
        replace_existing=True,
    )

    # Job 2: NLP batch processing (every 30 minutes)
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
        except Exception as e:
            logger.warning(f"Error stopping scheduler: {e}")
        finally:
            _scheduler = None


def get_scheduler_status() -> dict:
    """Get current scheduler status and job info."""
    if _scheduler is None:
        return {"running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })

    return {
        "running": _scheduler.running,
        "startup_complete": _startup_complete,
        "jobs": jobs,
    }
