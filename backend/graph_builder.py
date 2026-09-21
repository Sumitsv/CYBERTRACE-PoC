import networkx as nx
from typing import List, Dict, Any
from backend.models import Entity, Relationship

def build_cytoscape_graph(entities: List[Entity], relationships: List[Relationship]) -> Dict[str, List[Dict[str, Any]]]:
    """Builds NetworkX graph and converts to Cytoscape JSON layout structure."""
    G = nx.Graph()

    # Colors per entity type
    type_colors = {
        "PHONE": "#06b6d4",       # Cyan
        "IMEI": "#f97316",        # Orange
        "IMSI": "#a855f7",        # Purple
        "UPI": "#10b981",         # Emerald
        "BANK": "#3b82f6",        # Blue
        "TXN": "#eab308",         # Yellow
        "IP": "#ef4444",          # Red
        "EMAIL": "#ec4899"        # Pink
    }

    for entity in entities:
        G.add_node(
            entity.id,
            label=entity.value,
            type=entity.type,
            color=type_colors.get(entity.type, "#94a3b8")
        )

    for rel in relationships:
        G.add_edge(
            rel.source,
            rel.target,
            relationship=rel.relationship,
            evidence_ids=",".join(rel.evidence_ids),
            is_suspicious=rel.is_suspicious
        )

    nodes = []
    for node_id, data in G.nodes(data=True):
        nodes.append({
            "data": {
                "id": node_id,
                "label": f"{data['type']}\n{data['label']}",
                "type": data['type'],
                "color": data['color']
            }
        })

    edges = []
    for u, v, data in G.edges(data=True):
        edges.append({
            "data": {
                "id": f"{u}--{v}",
                "source": u,
                "target": v,
                "relationship": data['relationship'],
                "evidence_ids": data['evidence_ids'],
                "is_suspicious": data['is_suspicious']
            }
        })

    return {"nodes": nodes, "edges": edges}