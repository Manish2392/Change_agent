# integrations/servicenow_client.py — ServiceNow REST API wrapper with mock mode
#
# HOW MOCK MODE WORKS:
#   Set USE_MOCK_SERVICENOW=true in your .env (or leave blank — it defaults to true).
#   The ServiceNowClient class checks this flag at __init__ and routes every method
#   call to MockServiceNowData instead of making real HTTP requests.
#   The returned dict shape is IDENTICAL in both modes, so pipeline.py never changes.
#
# HOW TO SWITCH TO REAL SERVICENOW:
#   In your .env file set:
#       USE_MOCK_SERVICENOW=false
#       SNOW_INSTANCE=https://your-company.service-now.com
#       SNOW_USERNAME=your_username
#       SNOW_PASSWORD=your_password

import requests
from requests.auth import HTTPBasicAuth
from config import SNOW_INSTANCE, SNOW_USERNAME, SNOW_PASSWORD, USE_MOCK_SERVICENOW


# ══════════════════════════════════════════════════════════════
#  MOCK DATA STORE
#  Realistic HCLTech-style CMDB and Change data for development
#  and demos. Mirrors the exact field names ServiceNow returns.
# ══════════════════════════════════════════════════════════════

class MockServiceNowData:
    """
    In-memory store of realistic mock ServiceNow data.
    Structured to mirror real SNOW API response shapes exactly.
    """

    # ── Mock Change Requests ───────────────────────────────
    CHANGES = {
        "CHG0001001": {
            "sys_id":            "chg_sys_001",
            "number":            "CHG0001001",
            "short_description": "Oracle DB patch - quarterly security update",
            "description":       "Apply Oracle CPU patch Q1-2025 to all production databases. "
                                 "Patch addresses 3 CVEs (CVSS 7.8, 6.5, 5.2). "
                                 "Coordinated downtime window: 02:00–04:00 IST Saturday.",
            "start_date":        "2025-03-15 02:00:00",
            "end_date":          "2025-03-15 04:00:00",
            "state":             "Scheduled",
            "risk":              "High",
            "impact":            "2",
            "category":          "Software",
            "u_environment":     "Production",
            "cmdb_ci":           {"value": "ci_sys_oracle_prd_01", "display_value": "oracle-prd-01"},
        },
        "CHG0001002": {
            "sys_id":            "chg_sys_002",
            "number":            "CHG0001002",
            "short_description": "Network firewall rule update - payment gateway",
            "description":       "Add inbound allow rule for new payment processor IP range 203.0.113.0/24 "
                                 "on port 443. Remove deprecated rule set for old processor.",
            "start_date":        "2025-03-20 22:00:00",
            "end_date":          "2025-03-20 23:00:00",
            "state":             "Scheduled",
            "risk":              "Medium",
            "impact":            "2",
            "category":          "Network",
            "u_environment":     "Production",
            "cmdb_ci":           {"value": "ci_sys_fw_prd_01", "display_value": "fw-prd-core-01"},
        },
        "CHG0001003": {
            "sys_id":            "chg_sys_003",
            "number":            "CHG0001003",
            "short_description": "Deploy microservice v2.4.1 - customer portal API",
            "description":       "Rolling deployment of customer-portal-api v2.4.1. "
                                 "Includes new JWT refresh endpoint and bug fix for session timeout. "
                                 "Zero-downtime deployment using blue-green strategy.",
            "start_date":        "2025-03-22 10:00:00",
            "end_date":          "2025-03-22 11:30:00",
            "state":             "Scheduled",
            "risk":              "Low",
            "impact":            "3",
            "category":          "Software",
            "u_environment":     "Production",
            "cmdb_ci":           {"value": "ci_sys_web_prd_01", "display_value": "web-prd-01"},
        },
        "CHG0001004": {
            "sys_id":            "chg_sys_004",
            "number":            "CHG0001004",
            "short_description": "Storage expansion - DR site SAN upgrade",
            "description":       "Add 50TB capacity to DR site SAN array. "
                                 "Expand LUNs for DB replication volumes. "
                                 "Impact limited to DR site only during window.",
            "start_date":        "2025-03-25 00:00:00",
            "end_date":          "2025-03-25 06:00:00",
            "state":             "Scheduled",
            "risk":              "Medium",
            "impact":            "3",
            "category":          "Hardware",
            "u_environment":     "DR",
            "cmdb_ci":           {"value": "ci_sys_san_dr_01", "display_value": "san-dr-01"},
        },
        "CHG0001005": {
            "sys_id":            "chg_sys_005",
            "number":            "CHG0001005",
            "short_description": "Kubernetes cluster upgrade - QA environment",
            "description":       "Upgrade QA Kubernetes cluster from 1.28 to 1.30. "
                                 "Includes node OS patching. All QA workloads will be unavailable "
                                 "for ~3 hours. No production impact.",
            "start_date":        "2025-03-18 09:00:00",
            "end_date":          "2025-03-18 13:00:00",
            "state":             "Scheduled",
            "risk":              "Low",
            "impact":            "3",
            "category":          "Software",
            "u_environment":     "Non-Production",
            "cmdb_ci":           {"value": "ci_sys_k8s_qa_01", "display_value": "k8s-qa-cluster-01"},
        },
    }

    # ── Mock CMDB CIs ──────────────────────────────────────
    CIS = {
        # Production tier
        "ci_sys_oracle_prd_01": {
            "sys_id": "ci_sys_oracle_prd_01", "name": "oracle-prd-01",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1", "u_business_service": "Core Banking",
        },
        "ci_sys_web_prd_01": {
            "sys_id": "ci_sys_web_prd_01", "name": "web-prd-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1", "u_business_service": "Customer Portal",
        },
        "ci_sys_app_prd_01": {
            "sys_id": "ci_sys_app_prd_01", "name": "app-prd-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1", "u_business_service": "Core Banking",
        },
        "ci_sys_app_prd_02": {
            "sys_id": "ci_sys_app_prd_02", "name": "app-prd-02",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1", "u_business_service": "Core Banking",
        },
        "ci_sys_fw_prd_01": {
            "sys_id": "ci_sys_fw_prd_01", "name": "fw-prd-core-01",
            "sys_class_name": "cmdb_ci_firewall", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1", "u_business_service": "Network Infrastructure",
        },
        # DR tier
        "ci_sys_oracle_dr_01": {
            "sys_id": "ci_sys_oracle_dr_01", "name": "oracle-dr-01",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "DR",
            "operational_status": "1", "u_tier": "Tier-1", "u_business_service": "Core Banking",
        },
        "ci_sys_san_dr_01": {
            "sys_id": "ci_sys_san_dr_01", "name": "san-dr-01",
            "sys_class_name": "cmdb_ci_storage_device", "environment": "DR",
            "operational_status": "1", "u_tier": "Tier-2", "u_business_service": "Storage",
        },
        # Non-prod
        "ci_sys_k8s_qa_01": {
            "sys_id": "ci_sys_k8s_qa_01", "name": "k8s-qa-cluster-01",
            "sys_class_name": "cmdb_ci_kubernetes_cluster", "environment": "Non-Production",
            "operational_status": "1", "u_tier": "Tier-3", "u_business_service": "Dev/QA Platform",
        },
    }

    # ── Mock CI Relationships ──────────────────────────────
    # Each entry: parent CI → child CIs it depends on
    RELATIONSHIPS = {
        "ci_sys_oracle_prd_01": [
            {"parent": {"value": "ci_sys_app_prd_01"},
             "child":  {"value": "ci_sys_oracle_prd_01"},
             "type":   {"display_value": "Depends on::Used by"}},
            {"parent": {"value": "ci_sys_app_prd_02"},
             "child":  {"value": "ci_sys_oracle_prd_01"},
             "type":   {"display_value": "Depends on::Used by"}},
            {"parent": {"value": "ci_sys_oracle_prd_01"},
             "child":  {"value": "ci_sys_oracle_dr_01"},
             "type":   {"display_value": "Replicates to::Replication source"}},
        ],
        "ci_sys_web_prd_01": [
            {"parent": {"value": "ci_sys_web_prd_01"},
             "child":  {"value": "ci_sys_app_prd_01"},
             "type":   {"display_value": "Connects to::Connected from"}},
            {"parent": {"value": "ci_sys_fw_prd_01"},
             "child":  {"value": "ci_sys_web_prd_01"},
             "type":   {"display_value": "Protects::Protected by"}},
        ],
        "ci_sys_fw_prd_01": [
            {"parent": {"value": "ci_sys_fw_prd_01"},
             "child":  {"value": "ci_sys_web_prd_01"},
             "type":   {"display_value": "Protects::Protected by"}},
            {"parent": {"value": "ci_sys_fw_prd_01"},
             "child":  {"value": "ci_sys_app_prd_01"},
             "type":   {"display_value": "Protects::Protected by"}},
        ],
        "ci_sys_san_dr_01": [
            {"parent": {"value": "ci_sys_oracle_dr_01"},
             "child":  {"value": "ci_sys_san_dr_01"},
             "type":   {"display_value": "Runs on::Hosts"}},
        ],
        "ci_sys_k8s_qa_01": [],
    }

    # ── Mock Maintenance Windows ───────────────────────────
    MAINTENANCE = {
        "ci_sys_oracle_prd_01": [
            {"name": "Monthly DB Maintenance", "start_date": "2025-03-15 02:00:00",
             "end_date": "2025-03-15 04:00:00", "schedule": "Monthly"},
        ],
        "ci_sys_fw_prd_01": [
            {"name": "Weekly Firewall Review", "start_date": "2025-03-21 00:00:00",
             "end_date": "2025-03-21 01:00:00", "schedule": "Weekly"},
        ],
    }

    # ── Lookup methods ─────────────────────────────────────

    def get_change(self, chg_number: str) -> dict:
        record = self.CHANGES.get(chg_number.upper())
        if not record:
            # Return a sensible fallback so the pipeline doesn't crash on unknown CHG#
            return {
                "sys_id": f"mock_sys_{chg_number}",
                "number": chg_number,
                "short_description": f"Mock change record for {chg_number}",
                "description": "Auto-generated mock record. Add this CHG to MockServiceNowData.CHANGES for full detail.",
                "start_date": "2025-03-30 02:00:00",
                "end_date":   "2025-03-30 04:00:00",
                "state": "Scheduled", "risk": "Medium", "impact": "2",
                "category": "Software", "u_environment": "Production",
                "cmdb_ci": {"value": "ci_sys_web_prd_01", "display_value": "web-prd-01"},
            }
        return record

    def get_ci_by_id(self, sys_id: str) -> dict:
        return self.CIS.get(sys_id, {
            "sys_id": sys_id, "name": f"mock-ci-{sys_id[:8]}",
            "sys_class_name": "cmdb_ci_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-2", "u_business_service": "Unknown",
        })

    def get_ci_relationships(self, ci_sys_id: str) -> list:
        return self.RELATIONSHIPS.get(ci_sys_id, [])

    def get_maintenance_windows(self, ci_sys_id: str) -> list:
        return self.MAINTENANCE.get(ci_sys_id, [])


# ══════════════════════════════════════════════════════════════
#  REAL SERVICENOW CLIENT
# ══════════════════════════════════════════════════════════════

class _RealServiceNowClient:
    """Makes actual REST calls to a ServiceNow instance."""

    def __init__(self):
        self.base    = SNOW_INSTANCE
        self.auth    = HTTPBasicAuth(SNOW_USERNAME, SNOW_PASSWORD)
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}

    def _get(self, table: str, params: dict) -> list:
        url  = f"{self.base}/api/now/table/{table}"
        resp = requests.get(url, auth=self.auth, headers=self.headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("result", [])

    def get_change(self, chg_number: str) -> dict:
        results = self._get("change_request", {
            "sysparm_query":  f"number={chg_number}",
            "sysparm_fields": "sys_id,number,short_description,description,"
                              "start_date,end_date,state,risk,impact,category,"
                              "u_environment,cmdb_ci",
            "sysparm_limit":  1,
        })
        return results[0] if results else {}

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


# ══════════════════════════════════════════════════════════════
#  PUBLIC FACTORY — this is the only import the rest of the
#  codebase uses.  Routing logic lives here, not in callers.
# ══════════════════════════════════════════════════════════════

def ServiceNowClient():
    """
    Factory function — returns a mock or real client based on config.

    Usage (unchanged from original):
        from integrations.servicenow_client import ServiceNowClient
        client = ServiceNowClient()
        change = client.get_change("CHG0001001")
    """
    if USE_MOCK_SERVICENOW:
        print("[ServiceNow] MOCK MODE — using local test data (set USE_MOCK_SERVICENOW=false to use real SNOW)")
        return MockServiceNowData()
    else:
        print("[ServiceNow] LIVE MODE — connecting to", SNOW_INSTANCE)
        return _RealServiceNowClient()
