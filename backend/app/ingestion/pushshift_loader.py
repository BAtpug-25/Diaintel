"""
DiaIntel — Pushshift Data Loader
Loads real Reddit posts from Pushshift .zst dump files.

CRITICAL: Does NOT use PRAW or Reddit API.
Uses zstandard library to decompress .zst files.

Implemented in Step 2.
"""

import logging
from typing import Optional

logger = logging.getLogger("diaintel.ingestion.pushshift_loader")


class PushshiftLoader:
    """
    Loads and filters Reddit posts from Pushshift .zst dump files.

    Pipeline:
    1. Decompress .zst files using zstandard
    2. Read line by line (each line = one JSON object)
    3. Extract: id, subreddit, body/selftext, score, num_comments, created_utc
    4. Filter posts mentioning target drugs (case-insensitive)
    5. Skip empty/deleted/[removed] posts
    6. Insert in batches of 1000
    7. Track loaded files in ingestion_log to prevent duplicates
    """

    def __init__(self):
        self.data_dir = None
        self.initialized = False
        logger.info("PushshiftLoader created (not yet initialized)")

    def initialize(self, data_dir: str):
        """Initialize with data directory path."""
        # TODO: Implement in Step 2
        self.data_dir = data_dir
        self.initialized = True
        logger.info(f"PushshiftLoader initialized with dir: {data_dir}")

    def load_all(self):
        """Load all unprocessed .zst files."""
        # TODO: Implement in Step 2
        logger.info("load_all called (placeholder)")

    def load_file(self, filepath: str):
        """Load a single .zst file into the database."""
        # TODO: Implement in Step 2
        logger.info(f"load_file called for {filepath} (placeholder)")

    def get_status(self) -> list:
        """Get loading status of all files."""
        # TODO: Implement in Step 2
        return []


# Singleton
pushshift_loader = PushshiftLoader()
