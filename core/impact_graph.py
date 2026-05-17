# core/impact_graph.py — Step 4: ImpactGraph Builder
# Builds a nodes + edges dependency graph from the classified CI list.

from integrations.servicenow_client import ServiceNowClient


def build_impact_graph(ci_list: list) -> dict:
    """
    Builds dependency graph for all CIs.
    Returns: { nodes, edges, adjacency }
    """
    client    = ServiceNowClient()
    ci_ids    = {ci["sys_id"] for ci in ci_list}
    nodes     = []
    edges     = []
    adjacency = {ci["sys_id"]: [] for ci in ci_list}
    seen_edges = set()

    print(f"[ImpactGraph] Building graph for {len(ci_list)} CIs...")

    for ci in ci_list:
        nodes.append({
            "id":              ci["sys_id"],
            "name":            ci["name"],
            "class":           ci.get("class", ""),
            "env_class":       ci.get("env_class", "UNKNOWN"),
            "environment":     ci.get("environment", ""),
            "tier":            ci.get("tier", ""),
            "business_service": ci.get("business_service", ""),
        })

        for rel in client.get_ci_relationships(ci["sys_id"]):
            parent   = rel.get("parent", {})
            child    = rel.get("child",  {})
            rel_type = rel.get("type",   {})
            from_id  = parent.get("value") if isinstance(parent,   dict) else parent
            to_id    = child.get("value")  if isinstance(child,    dict) else child
            label    = rel_type.get("display_value", "") if isinstance(rel_type, dict) else str(rel_type)

            if from_id in ci_ids and to_id in ci_ids:
                key = f"{from_id}→{to_id}"
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append({"from": from_id, "to": to_id, "type": label})
                    adjacency.setdefault(from_id, []).append(to_id)

    print(f"[ImpactGraph] ✓ {len(nodes)} nodes, {len(edges)} edges")
    return {"nodes": nodes, "edges": edges, "adjacency": adjacency}


def graph_to_text(graph: dict) -> str:
    """Human-readable graph text for LLM prompt consumption."""
    if not graph.get("edges"):
        return "No CI dependency relationships found."
    name_map = {n["id"]: n["name"] for n in graph["nodes"]}
    lines    = ["=== CI Dependency Graph ==="]
    for edge in graph["edges"]:
        frm   = name_map.get(edge["from"], edge["from"])
        to    = name_map.get(edge["to"],   edge["to"])
        etype = edge.get("type", "relates to")
        lines.append(f"  {frm}  --[{etype}]-->  {to}")
    return "\n".join(lines)
