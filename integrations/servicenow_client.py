# integrations/servicenow_client.py — ServiceNow REST API wrapper
import requests
from requests.auth import HTTPBasicAuth
from config import SNOW_INSTANCE, SNOW_USERNAME, SNOW_PASSWORD


class ServiceNowClient:
    """Handles all ServiceNow REST API calls."""

    def __init__(self):
        self.base    = SNOW_INSTANCE
        self.auth    = HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD)
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}

    def _get(self, table: str, params: dict) -> list:
        url  = f"{self.base}/api/now/table/{table}"
        resp = requests.get(url, auth=self.auth, headers=self.headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("result", [])

    # ── Change Management ──────────────────────────────────
    def get_change(self, chg_number: str) -> dict:
        results = self._get("change_request", {
            "sysparm_query":  f"number={chg_number}",
            "sysparm_fields": "sys_id,number,short_description,description,"
                              "start_date,end_date,state,risk,impact,category,"
                              "u_environment,cmdb_ci",
            "sysparm_limit":  1,
        })
        return results[0] if results else {}

    # ── CMDB ───────────────────────────────────────────────
    def get_ci_by_id(self, sys_id: str) -> dict:
        results = self._get("cmdb_ci", {
            "sysparm_query":  f"sys_id={sys_id}",
            "sysparm_fields": "sys_id,name,sys_class_name,environment,"
                              "operational_status,u_tier,u_business_service",
            "sysparm_limit":  1,
        })
        return results[0] if results else {}

    def get_ci_relationships(self, ci_sys_id: str) -> list:
        return self._get("cmdb_rel_ci", {
            "sysparm_query":  f"parent={ci_sys_id}^ORchild={ci_sys_id}",
            "sysparm_fields": "parent,child,type",
            "sysparm_limit":  500,
        })

    def get_maintenance_windows(self, ci_sys_id: str) -> list:
        return self._get("cmdb_maintenance_schedule", {
            "sysparm_query":  f"cmdb_ci={ci_sys_id}",
            "sysparm_fields": "name,start_date,end_date,schedule",
            "sysparm_limit":  10,
        })
