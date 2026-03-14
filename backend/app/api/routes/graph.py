"""
DiaIntel — Graph Routes
API endpoint for the Drug-AE knowledge graph.
"""

import time
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pydantic_models import KnowledgeGraph

logger = logging.getLogger("diaintel.routes.graph")
router = APIRouter()


@router.get("/graph/drug-ae", response_model=KnowledgeGraph)
async def get_drug_ae_graph(db: Session = Depends(get_db)):
    """
    Get all nodes and edges for the knowledge graph.

    Returns: drug nodes, AE nodes, and weighted edges.
    Cache: 300 seconds.

    Implemented in Step 8.
    """
    start_time = time.time()

    # TODO: Implement in Step 8
    # - Query drug_ae_graph for all edges
    # - Build node list (drugs + AEs)
    # - Calculate node sizes based on connections
    # - Use Redis cache with 300s TTL

    return KnowledgeGraph(
        nodes=[],
        edges=[],
        processing_time_ms=round((time.time() - start_time) * 1000, 2),
    )
