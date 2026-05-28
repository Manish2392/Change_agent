# core/change_miner.py — Step 1: ChangeMiner
# LangChain Tool wrapper around ServiceNow CHG fetch.
# Updated to capture ExaCC-specific fields: change_reason, contact_list,
# contact_instructions, risk_description, user_service_impact.

from langchain.tools import tool
from integrations.servicenow_client import ServiceNowClient


@tool
def fetch_change_tool(chg_number: str) -> dict:
    """Fetches a ServiceNow Change Record by CHG number. Returns structured change data."""
    return fetch_change(chg_number)


def fetch_change(chg_number: str) -> dict:
    """
    Fetches CHG record from ServiceNow.
    Returns structured dict with change metadata + primary CI sys_id.
    Now includes ExaCC-specific fields where present.
    """
    client = ServiceNowClient()
    print(f"[ChangeMiner] Fetching: {chg_number}")

    record = client.get_change(chg_number)
    if not record:
        raise ValueError(f"No change found for {chg_number}")

    # cmdb_ci field is a reference object: {"value": sys_id, "link": ...}
    primary_ci_id = ""
    if isinstance(record.get("cmdb_ci"), dict):
        primary_ci_id = record["cmdb_ci"].get("value", "")
    elif isinstance(record.get("cmdb_ci"), str):
        primary_ci_id = record["cmdb_ci"]

    change_data = {
        "chg_number":             record.get("number", chg_number),
        "description":            record.get("short_description", ""),
        "long_desc":              record.get("description", ""),
        "change_reason":          record.get("change_reason", ""),
        "start_date":             record.get("start_date", ""),
        "end_date":               record.get("end_date", ""),
        "state":                  record.get("state", ""),
        "risk":                   record.get("risk", ""),
        "impact":                 record.get("impact", ""),
        "category":               record.get("category", ""),
        "environment":            record.get("u_environment", ""),
        "contact_list":           record.get("u_contact_list", ""),
        "contact_instructions":   record.get("u_contact_instructions", ""),
        "risk_description":       record.get("u_risk_description", ""),
        "user_service_impact":    record.get("u_user_service_impact", ""),
        "primary_ci_id":          primary_ci_id,
        "raw":                    record,
    }

    print(f"[ChangeMiner] ✓ {change_data['description']}")
    print(f"[ChangeMiner]   Window: {change_data['start_date']} → {change_data['end_date']}")
    if change_data["contact_list"]:
        print(f"[ChangeMiner]   Contact: {change_data['contact_list']}")
    return change_data
