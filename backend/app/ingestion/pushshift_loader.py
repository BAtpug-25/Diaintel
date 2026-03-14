"""
DiaIntel — Pushshift Data Loader
Loads real Reddit posts from Pushshift .zst dump files into PostgreSQL.

CRITICAL: Does NOT use PRAW or Reddit API.
Uses zstandard library to decompress .zst files line by line.

Pipeline:
1. Scan data directory for .zst files
2. Check ingestion_log to skip already-processed files
3. Decompress each .zst file using zstandard streaming reader
4. Parse each line as JSON (one Reddit post per line)
5. Extract: id, subreddit, body/selftext, score, num_comments, created_utc
6. Filter posts mentioning target drugs (case-insensitive)
7. Skip empty, deleted, [removed], and short posts
8. Insert filtered posts into raw_posts in batches of 1000
9. Log progress every 1000 records processed
10. Write completion entry to ingestion_log
"""

import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Generator, List

import zstandard as zstd
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import SessionLocal
from app.config import settings

logger = logging.getLogger("diaintel.ingestion.pushshift_loader")

# ============================================================
# Drug filter — all target drugs + variants (lowercased)
# ============================================================
DRUG_VARIANTS = [
    # Metformin
    "metformin", "glucophage", "glumetza", "fortamet",
    # Ozempic / Semaglutide
    "ozempic", "semaglutide", "wegovy",
    # Jardiance / Empagliflozin
    "jardiance", "empagliflozin",
    # Januvia / Sitagliptin
    "januvia", "sitagliptin",
    # Farxiga / Dapagliflozin
    "farxiga", "dapagliflozin",
    # Trulicity / Dulaglutide
    "trulicity", "dulaglutide",
    # Victoza / Liraglutide
    "victoza", "liraglutide",
    # Glipizide
    "glipizide", "glucotrol",
]

# Pre-lowercased for fast substring matching
DRUG_VARIANTS_LOWER = [d.lower() for d in DRUG_VARIANTS]

# Posts to skip
SKIP_BODIES = {"", "[deleted]", "[removed]"}
MIN_POST_LENGTH = 20
BATCH_SIZE = 1000


def _contains_target_drug(text: str) -> bool:
    """Fast check if text mentions any target drug using simple substring match."""
    text_lower = text.lower()
    return any(drug in text_lower for drug in DRUG_VARIANTS_LOWER)


def _extract_body(record: dict) -> Optional[str]:
    """Extract the post body from a Pushshift record.

    Comments have 'body', submissions have 'selftext'.
    Returns None if the body is empty/deleted/removed/too short.
    """
    body = record.get("body") or record.get("selftext") or ""
    body = body.strip()

    if body.lower() in SKIP_BODIES:
        return None
    if len(body) < MIN_POST_LENGTH:
        return None

    return body


def _parse_timestamp(record: dict) -> datetime:
    """Parse created_utc from Pushshift record.

    Can be int (epoch), float, or string.
    """
    ts = record.get("created_utc", 0)
    try:
        if isinstance(ts, str):
            ts = float(ts)
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        return datetime.now(timezone.utc)


def _stream_zst_lines(filepath: str) -> Generator[bytes, None, None]:
    """Stream decompressed lines from a .zst file.

    Uses zstandard streaming reader for memory efficiency —
    never loads entire file into memory.
    """
    dctx = zstd.ZstdDecompressor(max_window_size=2**31)
    with open(filepath, "rb") as fh:
        with dctx.stream_reader(fh) as reader:
            buffer = b""
            while True:
                chunk = reader.read(65536)  # 64KB chunks
                if not chunk:
                    if buffer:
                        yield buffer
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line.strip():
                        yield line


def _is_file_already_loaded(db: Session, filename: str) -> bool:
    """Check if a file has already been successfully loaded."""
    result = db.execute(
        text("SELECT COUNT(*) FROM ingestion_log WHERE filename = :fn AND status = 'completed'"),
        {"fn": filename}
    ).scalar()
    return result > 0


def _create_ingestion_entry(db: Session, filename: str) -> int:
    """Create an ingestion_log entry and return its ID."""
    result = db.execute(
        text("""
            INSERT INTO ingestion_log (filename, records_read, records_inserted, started_at, status)
            VALUES (:fn, 0, 0, NOW(), 'running')
            RETURNING id
        """),
        {"fn": filename}
    )
    db.commit()
    return result.scalar()


def _update_ingestion_entry(db: Session, log_id: int, records_read: int, records_inserted: int, status: str):
    """Update an ingestion_log entry with results."""
    db.execute(
        text("""
            UPDATE ingestion_log
            SET records_read = :read, records_inserted = :inserted,
                completed_at = NOW(), status = :status
            WHERE id = :id
        """),
        {"read": records_read, "inserted": records_inserted, "status": status, "id": log_id}
    )
    db.commit()


def _insert_batch(db: Session, batch: List[dict], filename: str) -> int:
    """Insert a batch of posts into raw_posts. Returns count of newly inserted rows."""
    if not batch:
        return 0

    inserted = 0
    for post in batch:
        try:
            result = db.execute(
                text("""
                    INSERT INTO raw_posts (reddit_id, subreddit, body, score, comment_count, created_utc, scraped_at, processed, source_file)
                    VALUES (:reddit_id, :subreddit, :body, :score, :comment_count, :created_utc, NOW(), FALSE, :source_file)
                    ON CONFLICT (reddit_id) DO NOTHING
                """),
                {
                    "reddit_id": post["reddit_id"],
                    "subreddit": post["subreddit"],
                    "body": post["body"],
                    "score": post["score"],
                    "comment_count": post["comment_count"],
                    "created_utc": post["created_utc"],
                    "source_file": filename,
                }
            )
            inserted += result.rowcount
        except Exception as e:
            logger.warning(f"Failed to insert post {post.get('reddit_id', '?')}: {e}")
            continue

    db.commit()
    return inserted


def load_file(filepath: str) -> dict:
    """
    Load a single .zst file into the database.

    Returns dict with:
        filename, records_read, records_inserted, status, duration_seconds
    """
    filename = os.path.basename(filepath)
    logger.info(f"{'='*60}")
    logger.info(f"Loading: {filename}")
    logger.info(f"Path: {filepath}")
    logger.info(f"{'='*60}")

    db = SessionLocal()
    start_time = time.time()
    records_read = 0
    records_inserted = 0
    batch: List[dict] = []

    try:
        # Check if already loaded
        if _is_file_already_loaded(db, filename):
            logger.info(f"  ✓ Already loaded — skipping {filename}")
            return {
                "filename": filename,
                "records_read": 0,
                "records_inserted": 0,
                "status": "skipped",
                "duration_seconds": 0,
            }

        # Create ingestion log entry
        log_id = _create_ingestion_entry(db, filename)

        # Stream and process lines
        for line_bytes in _stream_zst_lines(filepath):
            records_read += 1

            # Parse JSON
            try:
                record = json.loads(line_bytes)
            except (json.JSONDecodeError, UnicodeDecodeError):
                if records_read % 50000 == 0:
                    logger.debug(f"  Skipped malformed JSON at line {records_read}")
                continue

            # Extract body
            body = _extract_body(record)
            if body is None:
                continue

            # Check for target drug mentions
            if not _contains_target_drug(body):
                continue

            # Extract fields
            reddit_id = str(record.get("id", f"unk_{records_read}"))
            subreddit = record.get("subreddit", "unknown")
            score = int(record.get("score", 0)) if record.get("score") is not None else 0
            num_comments = int(record.get("num_comments", 0)) if record.get("num_comments") is not None else 0
            created_utc = _parse_timestamp(record)

            batch.append({
                "reddit_id": reddit_id,
                "subreddit": subreddit,
                "body": body,
                "score": score,
                "comment_count": num_comments,
                "created_utc": created_utc,
            })

            # Insert batch when full
            if len(batch) >= BATCH_SIZE:
                inserted = _insert_batch(db, batch, filename)
                records_inserted += inserted
                batch.clear()
                logger.info(
                    f"  Progress: {records_read:,} read | {records_inserted:,} inserted | "
                    f"batch of {inserted}"
                )

        # Insert remaining records
        if batch:
            inserted = _insert_batch(db, batch, filename)
            records_inserted += inserted
            batch.clear()

        duration = time.time() - start_time

        # Update ingestion log
        _update_ingestion_entry(db, log_id, records_read, records_inserted, "completed")

        logger.info(f"  ✓ Completed: {filename}")
        logger.info(f"    Records read: {records_read:,}")
        logger.info(f"    Records inserted: {records_inserted:,}")
        logger.info(f"    Duration: {duration:.1f}s")

        return {
            "filename": filename,
            "records_read": records_read,
            "records_inserted": records_inserted,
            "status": "completed",
            "duration_seconds": round(duration, 1),
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"  ✗ Failed: {filename} — {e}")

        # Try to update ingestion log with failure
        try:
            if 'log_id' in locals():
                _update_ingestion_entry(db, log_id, records_read, records_inserted, f"failed: {str(e)[:200]}")
        except Exception:
            pass

        return {
            "filename": filename,
            "records_read": records_read,
            "records_inserted": records_inserted,
            "status": f"failed: {str(e)[:200]}",
            "duration_seconds": round(duration, 1),
        }

    finally:
        db.close()


def load_all(data_dir: str = None) -> List[dict]:
    """
    Load all unprocessed .zst files from the data directory.

    Scans data_dir for .zst files, checks ingestion_log for each,
    and loads any files not yet successfully processed.

    Returns list of result dicts, one per file.
    """
    if data_dir is None:
        data_dir = settings.PUSHSHIFT_DATA_DIR

    logger.info("=" * 60)
    logger.info("DiaIntel — Pushshift Loader: Starting bulk load")
    logger.info(f"Data directory: {data_dir}")
    logger.info("=" * 60)

    # Find all .zst files
    zst_files = sorted(
        [f for f in os.listdir(data_dir) if f.endswith(".zst")]
    )

    if not zst_files:
        logger.warning(f"No .zst files found in {data_dir}")
        return []

    logger.info(f"Found {len(zst_files)} .zst files: {', '.join(zst_files)}")

    results = []
    total_read = 0
    total_inserted = 0
    total_start = time.time()

    for i, filename in enumerate(zst_files, 1):
        filepath = os.path.join(data_dir, filename)
        logger.info(f"\n[{i}/{len(zst_files)}] Processing {filename}...")

        result = load_file(filepath)
        results.append(result)
        total_read += result["records_read"]
        total_inserted += result["records_inserted"]

    total_duration = time.time() - total_start

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("Pushshift Loader — Summary")
    logger.info("=" * 60)
    for r in results:
        status_icon = "✓" if r["status"] in ("completed", "skipped") else "✗"
        logger.info(f"  {status_icon} {r['filename']}: {r['records_inserted']:,} inserted ({r['status']})")
    logger.info(f"\nTotal: {total_read:,} read, {total_inserted:,} inserted in {total_duration:.1f}s")
    logger.info("=" * 60)

    return results


def get_status() -> List[dict]:
    """Get loading status of all files from ingestion_log."""
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT filename, records_read, records_inserted, started_at, completed_at, status FROM ingestion_log ORDER BY started_at DESC")
        )
        return [
            {
                "filename": row[0],
                "records_read": row[1],
                "records_inserted": row[2],
                "started_at": row[3].isoformat() if row[3] else None,
                "completed_at": row[4].isoformat() if row[4] else None,
                "status": row[5],
            }
            for row in result
        ]
    finally:
        db.close()
