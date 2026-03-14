"""
DiaIntel — Knowledge Graph Builder
Maintains the Drug-AE graph in memory and in drug_ae_graph.
"""

import logging
from typing import Dict, List, Tuple

import networkx as nx
from sqlalchemy import text as sql_text

logger = logging.getLogger("diaintel.nlp.graph_builder")


class GraphBuilder:
    """Builds and queries the Drug-AE knowledge graph."""

    def __init__(self):
        self.graph = nx.Graph()
        logger.info("GraphBuilder initialized with empty graph")

    def build_from_db(self, db_session) -> nx.Graph:
        self.graph.clear()
        rows = db_session.execute(
            sql_text(
                """
                SELECT drug_name, ae_term, edge_weight
                FROM drug_ae_graph
                ORDER BY edge_weight DESC, drug_name, ae_term
                """
            )
        ).mappings().all()

        for row in rows:
            self.add_edge(row["drug_name"], row["ae_term"], row["edge_weight"])
        return self.graph

    def add_edge(self, drug: str, ae: str, weight: int = 1):
        if self.graph.has_edge(drug, ae):
            self.graph[drug][ae]["weight"] += weight
        else:
            self.graph.add_node(drug, type="drug")
            self.graph.add_node(ae, type="ae")
            self.graph.add_edge(drug, ae, weight=weight)

    def update_graph_for_post(self, post_id: int, db_session) -> int:
        rows = db_session.execute(
            sql_text(
                """
                SELECT drug_name, COALESCE(ae_normalized, ae_term) AS ae_term, COUNT(*) AS cnt
                FROM ae_signals
                WHERE post_id = :post_id
                GROUP BY drug_name, COALESCE(ae_normalized, ae_term)
                """
            ),
            {"post_id": post_id},
        ).mappings().all()

        if not rows:
            return 0

        db_session.execute(
            sql_text(
                """
                INSERT INTO drug_ae_graph (drug_name, ae_term, edge_weight, first_detected, last_updated)
                VALUES (:drug_name, :ae_term, :edge_weight, NOW(), NOW())
                ON CONFLICT (drug_name, ae_term) DO UPDATE
                SET edge_weight = drug_ae_graph.edge_weight + EXCLUDED.edge_weight,
                    last_updated = NOW()
                """
            ),
            [
                {
                    "drug_name": row["drug_name"],
                    "ae_term": row["ae_term"],
                    "edge_weight": row["cnt"],
                }
                for row in rows
            ],
        )

        for row in rows:
            self.add_edge(row["drug_name"], row["ae_term"], row["cnt"])

        return len(rows)

    def get_drug_aes(self, drug: str) -> List[Tuple[str, int]]:
        if drug not in self.graph:
            return []
        neighbors = []
        for ae in self.graph.neighbors(drug):
            neighbors.append((ae, self.graph[drug][ae].get("weight", 1)))
        return sorted(neighbors, key=lambda item: item[1], reverse=True)

    def get_ae_drugs(self, ae: str) -> List[Tuple[str, int]]:
        if ae not in self.graph:
            return []
        neighbors = []
        for drug in self.graph.neighbors(ae):
            neighbors.append((drug, self.graph[drug][ae].get("weight", 1)))
        return sorted(neighbors, key=lambda item: item[1], reverse=True)

    def to_json(self) -> Dict:
        nodes = []
        for node, data in self.graph.nodes(data=True):
            nodes.append(
                {
                    "id": node,
                    "label": node,
                    "type": data.get("type", "unknown"),
                    "size": self.graph.degree(node),
                }
            )

        edges = []
        for source, target, data in self.graph.edges(data=True):
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "weight": data.get("weight", 1),
                }
            )

        return {"nodes": nodes, "edges": edges}

    def get_stats(self) -> Dict:
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "drug_nodes": sum(1 for _, data in self.graph.nodes(data=True) if data.get("type") == "drug"),
            "ae_nodes": sum(1 for _, data in self.graph.nodes(data=True) if data.get("type") == "ae"),
        }


graph_builder = GraphBuilder()
