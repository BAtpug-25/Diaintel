"""
DiaIntel — Scheduler
APScheduler-based task scheduling for data ingestion and processing.

Startup behavior:
1. Triggers pushshift_loader once to populate database from .zst files
2. NLP pipeline processes loaded posts in batches

Implemented in Step 2.
"""

import logging
from typing import Optional

logger = logging.getLogger("diaintel.ingestion.scheduler")

# Global scheduler reference
_scheduler = None


def start_scheduler():
    """
    Start the APScheduler.

    Scheduled tasks:
    1. On startup: Load unprocessed .zst files (pushshift_loader)
    2. Periodic: Process unprocessed posts through NLP pipeline
    """
    # TODO: Implement in Step 2
    logger.info("Scheduler start called (placeholder)")


def stop_scheduler():
    """Gracefully stop the scheduler."""
    global _scheduler
    if _scheduler:
        try:
            _scheduler.shutdown()
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.warning(f"Error stopping scheduler: {e}")


def get_scheduler_status() -> dict:
    """Get current scheduler status."""
    return {
        "running": _scheduler is not None,
        "jobs": [],
    }
