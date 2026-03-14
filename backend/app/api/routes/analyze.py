"""
DiaIntel — Analyze Routes
Live text analysis endpoint using DistilBERT (NOT BioBERT).
"""

import time
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pydantic_models import AnalyzeRequest, AnalyzeResult

logger = logging.getLogger("diaintel.routes.analyze")
router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResult)
async def analyze_text(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Analyze raw patient text in real-time.

    MUST use DistilBERT (NOT BioBERT) for speed.
    MUST complete in under 3 seconds.

    Returns: drugs found, AEs found, sentiment per drug,
    misinfo flag, confidence scores, processing_time_ms.

    No cache — always fresh analysis.

    Implemented in Step 8.
    """
    start_time = time.time()

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    # TODO: Implement in Step 8
    # 1. Drug NER extraction
    # 2. AE extraction using DistilBERT (NOT BioBERT)
    # 3. Sentiment analysis per drug
    # 4. Misinformation detection
    # 5. Generate highlighted text
    # Must complete < 3 seconds

    raise HTTPException(
        status_code=501,
        detail="Analyze endpoint not yet implemented (Step 8)"
    )
