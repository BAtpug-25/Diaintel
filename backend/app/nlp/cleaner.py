"""
DiaIntel — Text Cleaner
Pre-processes raw Reddit post text for NLP analysis.

Cleaning steps:
1. Remove URLs
2. Remove special characters (keep medical terms)
3. Remove excessive whitespace
4. Lowercase normalization
5. Remove Reddit formatting (markdown)
6. Filter by minimum length
7. Language detection (English only)

Implemented in Step 3.
"""

import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger("diaintel.nlp.cleaner")


class TextCleaner:
    """Cleans and normalizes raw Reddit post text."""

    def __init__(self, min_length: int = 20):
        self.min_length = min_length
        # Pre-compile regex patterns
        self.url_pattern = re.compile(r'https?://\S+|www\.\S+')
        self.reddit_link_pattern = re.compile(r'\[([^\]]+)\]\([^\)]+\)')
        self.markdown_pattern = re.compile(r'[*_~`#>]')
        self.whitespace_pattern = re.compile(r'\s+')
        self.special_char_pattern = re.compile(r'[^\w\s.,!?;:\'-/()mg%]')
        logger.info("TextCleaner initialized")

    def clean(self, text: str) -> Optional[str]:
        """
        Clean raw text. Returns None if text is invalid.

        Args:
            text: Raw post text

        Returns:
            Cleaned text or None if invalid/too short
        """
        if not text or not isinstance(text, str):
            return None

        # Skip deleted/removed posts
        if text.strip().lower() in ('[deleted]', '[removed]', ''):
            return None

        # TODO: Full implementation in Step 3
        # For now, basic cleaning
        cleaned = text.strip()
        cleaned = self.url_pattern.sub('', cleaned)
        cleaned = self.reddit_link_pattern.sub(r'\1', cleaned)
        cleaned = self.markdown_pattern.sub('', cleaned)
        cleaned = self.whitespace_pattern.sub(' ', cleaned)
        cleaned = cleaned.strip()

        if len(cleaned) < self.min_length:
            return None

        return cleaned

    def clean_batch(self, texts: list) -> list:
        """Clean a batch of texts, filtering out invalid ones."""
        results = []
        for text in texts:
            cleaned = self.clean(text)
            if cleaned:
                results.append(cleaned)
        return results


# Singleton
cleaner = TextCleaner()
