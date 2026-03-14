"""
DiaIntel — Graph Routes
API endpoint for the Drug-AE knowledge graph.
"""

import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pydantic_models import KnowledgeGraph
from app.nlp.graph_builder import graph_builder
from app.utils.cache import get_cached_json, set_cached_json

router = APIRouter()


@router.get("/graph/drug-ae", response_model=KnowledgeGraph)
async def get_drug_ae_graph(db: Session = Depends(get_db)):
    start_time = time.time()
    cache_key = "graph:drug_ae"

    cached = await get_cached_json(cache_key)
    if cached:
        cached["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached

    graph_builder.build_from_db(db)
    payload = graph_builder.to_json()
    payload["processing_time_ms"] = round((time.time() - start_time) * 1000, 2)

    await set_cached_json(cache_key, payload, 300)
    return payload
