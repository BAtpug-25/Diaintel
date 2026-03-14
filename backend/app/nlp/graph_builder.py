"""
DiaIntel - Knowledge Graph Builder
Maintains the treatment intelligence graph in memory and exposes JSON for the API.
"""

import logging
from typing import Dict, List, Tuple

import networkx as nx
from sqlalchemy import text as sql_text

logger = logging.getLogger("diaintel.nlp.graph_builder")


class GraphBuilder:
    """Builds and queries the DiaIntel knowledge graph."""

    def __init__(self):
        self.graph = nx.Graph()
        logger.info("GraphBuilder initialized with empty graph")

    def build_from_db(self, db_session) -> nx.Graph:
        self.graph.clear()

        ae_rows = db_session.execute(
            sql_text(
                """
                SELECT drug_name, ae_term, edge_weight
                FROM drug_ae_graph
                ORDER BY edge_weight DESC, drug_name, ae_term
                """
            )
        ).mappings().all()
        for row in ae_rows:
            self._add_typed_edge(
                row["drug_name"],
                row["ae_term"],
                int(row["edge_weight"] or 0),
                edge_type="drug_ae",
                source_type="drug",
                target_type="ae",
            )

        outcome_rows = db_session.execute(
            sql_text(
                """
                SELECT drug_name, outcome_category, COUNT(*) AS weight
                FROM treatment_outcomes
                GROUP BY drug_name, outcome_category
                ORDER BY weight DESC, drug_name, outcome_category
                """
            )
        ).mappings().all()
        for row in outcome_rows:
            self._add_typed_edge(
                row["drug_name"],
                row["outcome_category"],
                int(row["weight"] or 0),
                edge_type="drug_outcome",
                source_type="drug",
                target_type="outcome",
            )

        combo_rows = db_session.execute(
            sql_text(
                """
                SELECT drug_1, drug_2, post_count
                FROM drug_combinations
                ORDER BY post_count DESC, drug_1, drug_2
                """
            )
        ).mappings().all()
        for row in combo_rows:
            self._add_typed_edge(
                row["drug_1"],
                row["drug_2"],
                int(row["post_count"] or 0),
                edge_type="drug_combination",
                source_type="drug",
                target_type="drug",
            )

        return self.graph

    def _add_typed_edge(
        self,
        source: str,
        target: str,
        weight: int,
        *,
        edge_type: str,
        source_type: str,
        target_type: str,
    ):
        self.graph.add_node(source, type=source_type)
        self.graph.add_node(target, type=target_type)

        if self.graph.has_edge(source, target):
            self.graph[source][target]["weight"] += weight
            self.graph[source][target]["type"] = edge_type
        else:
            self.graph.add_edge(source, target, weight=weight, type=edge_type)

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
            self._add_typed_edge(
                row["drug_name"],
                row["ae_term"],
                int(row["cnt"] or 0),
                edge_type="drug_ae",
                source_type="drug",
                target_type="ae",
            )

        return len(rows)

    def get_drug_aes(self, drug: str) -> List[Tuple[str, int]]:
        if drug not in self.graph:
            return []
        neighbors = []
        for node in self.graph.neighbors(drug):
            edge = self.graph[drug][node]
            if edge.get("type") == "drug_ae":
                neighbors.append((node, edge.get("weight", 1)))
        return sorted(neighbors, key=lambda item: item[1], reverse=True)

    def to_json(self) -> Dict:
        nodes = []
        for node, data in self.graph.nodes(data=True):
            nodes.append(
                {
                    "id": node,
                    "label": node,
                    "type": data.get("type", "ae"),
                    "size": max(1, self.graph.degree(node)),
                }
            )

        edges = []
        for source, target, data in self.graph.edges(data=True):
            edges.append(
                {
                    "source": source,
                    "target": target,
                    "weight": int(data.get("weight", 1)),
                    "type": data.get("type", "drug_ae"),
                }
            )

        return {"nodes": nodes, "edges": edges, "stats": self.get_stats()}

    def get_stats(self) -> Dict:
        stats = {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "drug_nodes": 0,
            "ae_nodes": 0,
            "outcome_nodes": 0,
            "drug_combination_edges": 0,
        }
        for _, data in self.graph.nodes(data=True):
            node_type = data.get("type")
            if node_type == "drug":
                stats["drug_nodes"] += 1
            elif node_type == "ae":
                stats["ae_nodes"] += 1
            elif node_type == "outcome":
                stats["outcome_nodes"] += 1

        for _, _, data in self.graph.edges(data=True):
            if data.get("type") == "drug_combination":
                stats["drug_combination_edges"] += 1
        return stats


graph_builder = GraphBuilder()
