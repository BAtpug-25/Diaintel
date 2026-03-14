"""
DiaIntel — Compare Routes
API endpoints for drug comparison.
"""

import time
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pydantic_models import DrugComparison

logger = logging.getLogger("diaintel.routes.compare")
router = APIRouter()


@router.get("/compare", response_model=DrugComparison)
async def compare_drugs(
    drugs: str = Query(..., description="Comma-separated drug names, e.g., metformin,ozempic"),
    db: Session = Depends(get_db),
):
    """
    Compare two or more drugs side-by-side.

    Returns: AE frequency matrix, sentiment comparison, post volume.
    Cache: 300 seconds.

    Implemented in Step 8.
    """
    start_time = time.time()
    drug_list = [d.strip().lower() for d in drugs.split(",") if d.strip()]

    if len(drug_list) < 2:
        raise HTTPException(status_code=400, detail="At least 2 drugs required for comparison")

    # TODO: Implement in Step 8
    # - Query ae_signals for each drug
    # - Build AE frequency matrix
    # - Query sentiment_scores for comparison
    # - Use Redis cache with 300s TTL

    raise HTTPException(
        status_code=501,
        detail=f"Compare endpoint not yet implemented (Step 8). Drugs: {drug_list}"
    )
