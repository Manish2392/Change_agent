# core/ci_mapper.py — Step 2: CI Mapper
# BFS traversal of CMDB CI relationships to find all impacted CIs.

from langchain.tools import tool
from integrations.servicenow_client import ServiceNowClient
from config import MAX_CI_DEPTH


@tool
def map_impacted_cis_tool(primary_ci_id: str) -> list:
    """Traverses CMDB relationships from a primary CI to find all impacted CIs."""
    return map_impacted_cis(primary_ci_id)


def map_impacted_cis(primary_ci_id: str) -> list:
    """
    BFS traversal of CI relationships up to MAX_CI_DEPTH levels.
    Returns deduplicated flat list of all impacted CI dicts.
    """
    client  = ServiceNowClient()
    visited = set()
    ci_map  = {}
    queue   = [(primary_ci_id, 0)]

    print(f"[CI Mapper] Starting BFS from CI: {primary_ci_id}")

    while queue:
        ci_id, depth = queue.pop(0)
        if ci_id in visited or depth > MAX_CI_DEPTH:
            continue
        visited.add(ci_id)

        ci_detail = client.get_ci_by_id(ci_id)
        if not ci_detail:
            continue

        ci_entry = {
            "sys_id":             ci_detail.get("sys_id", ci_id),
            "name":               ci_detail.get("name", "Unknown"),
            "class":              ci_detail.get("sys_class_name", ""),
            "environment":        ci_detail.get("environment", ""),
            "operational_status": ci_detail.get("operational_status", ""),
            "tier":               ci_detail.get("u_tier", ""),
            "business_service":   ci_detail.get("u_business_service", ""),
            "depth":              depth,
        }
        ci_map[ci_id] = ci_entry
        print(f"[CI Mapper]   Depth {depth} → {ci_entry['name']} ({ci_entry['class']})")

        if depth < MAX_CI_DEPTH:
            for rel in client.get_ci_relationships(ci_id):
                parent    = rel.get("parent", {})
                child     = rel.get("child", {})
                parent_id = parent.get("value") if isinstance(parent, dict) else parent
                child_id  = child.get("value")  if isinstance(child,  dict) else child
                if parent_id and parent_id not in visited:
                    queue.append((parent_id, depth + 1))
                if child_id and child_id not in visited:
                    queue.append((child_id,  depth + 1))

    result = list(ci_map.values())
    print(f"[CI Mapper] ✓ Total CIs found: {len(result)}")
    return result
