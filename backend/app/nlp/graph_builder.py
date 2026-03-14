"""
DiaIntel — Knowledge Graph Builder
Builds and maintains a Drug-Adverse Event knowledge graph using NetworkX.

Nodes:
- Drug nodes (type: "drug")
- AE nodes (type: "ae")

Edges:
- Drug → AE with weight = frequency count

Implemented in Step 7.
"""

import logging
from typing import Dict, List, Tuple, Optional

import networkx as nx

logger = logging.getLogger("diaintel.nlp.graph_builder")


class GraphBuilder:
    """Builds and queries the Drug-AE knowledge graph."""

    def __init__(self):
        self.graph = nx.Graph()
        logger.info("GraphBuilder initialized with empty graph")

    def build_from_db(self, db_session) -> nx.Graph:
        """
        Build graph from drug_ae_graph table in database.

        Returns the NetworkX graph.
        """
        # TODO: Implement in Step 7
        logger.info("Building graph from database (placeholder)")
        return self.graph

    def add_edge(self, drug: str, ae: str, weight: int = 1):
        """Add or update an edge between a drug and an AE."""
        if self.graph.has_edge(drug, ae):
            self.graph[drug][ae]["weight"] += weight
        else:
            self.graph.add_node(drug, type="drug")
            self.graph.add_node(ae, type="ae")
            self.graph.add_edge(drug, ae, weight=weight)

    def get_drug_aes(self, drug: str) -> List[Tuple[str, int]]:
        """Get all AEs connected to a drug with weights."""
        if drug not in self.graph:
            return []
        neighbors = []
        for ae in self.graph.neighbors(drug):
            weight = self.graph[drug][ae].get("weight", 1)
            neighbors.append((ae, weight))
        return sorted(neighbors, key=lambda x: x[1], reverse=True)

    def get_ae_drugs(self, ae: str) -> List[Tuple[str, int]]:
        """Get all drugs connected to an AE with weights."""
        if ae not in self.graph:
            return []
        neighbors = []
        for drug in self.graph.neighbors(ae):
            weight = self.graph[drug][ae].get("weight", 1)
            neighbors.append((drug, weight))
        return sorted(neighbors, key=lambda x: x[1], reverse=True)

    def to_json(self) -> Dict:
        """Convert graph to JSON format for API response."""
        nodes = []
        for node, data in self.graph.nodes(data=True):
            node_type = data.get("type", "unknown")
            degree = self.graph.degree(node)
            nodes.append({
                "id": node,
                "label": node,
                "type": node_type,
                "size": degree,
            })

        edges = []
        for source, target, data in self.graph.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                "weight": data.get("weight", 1),
            })

        return {"nodes": nodes, "edges": edges}

    def get_stats(self) -> Dict:
        """Get graph statistics."""
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "drug_nodes": sum(1 for _, d in self.graph.nodes(data=True) if d.get("type") == "drug"),
            "ae_nodes": sum(1 for _, d in self.graph.nodes(data=True) if d.get("type") == "ae"),
        }


# Singleton
graph_builder = GraphBuilder()
