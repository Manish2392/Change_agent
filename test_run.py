# test_run.py — Creates 10 test CHG reports AND ingests them into FAISS RAG
# Reports 1-5: Original CHGs (CHG0012345-349)
# Reports 6-10: New ExaCC real-world CHGs (CHG0003774804, 900, 775100, 776200, 778500)

import json
import os
from datetime import datetime


def save_report(report):
    os.makedirs("reports", exist_ok=True)
    chg      = report["meta"]["chg_number"]
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reports/report_{chg}_{ts}.json"
    with open(filename, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  [saved]   {filename}")
    return filename


# ════════════════════════════════════════════════════════════════
#  ORIGINAL 5 REPORTS (CHG0012345 - CHG0012349)
# ════════════════════════════════════════════════════════════════

# ── CHG 1 — High severity patching ────────────────────────────
report1 = {
    "meta": {"chg_number": "CHG0012345", "analyzed_at": datetime.now().isoformat(), "elapsed_sec": 12},
    "change": {
        "chg_number": "CHG0012345", "description": "Apply OS patches to production web servers",
        "category": "Patching", "risk": "Medium", "impact": "High",
        "start_date": "2026-05-20 02:00:00", "end_date": "2026-05-20 04:00:00",
        "state": "Scheduled", "environment": "Production"
    },
    "ci_summary": {"PROD": 3, "DR": 1, "NON-PROD": 4, "UNKNOWN": 0},
    "ci_details": {
        "prod": [
            {"name": "web-prd-01", "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Online Banking",  "env_class": "PROD"},
            {"name": "web-prd-02", "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Online Banking",  "env_class": "PROD"},
            {"name": "db-prd-01",  "class": "cmdb_ci_database",     "tier": "Tier 1", "business_service": "Mobile App",      "env_class": "PROD"}
        ],
        "dr":      [{"name": "web-dr-01", "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Online Banking", "env_class": "DR"}],
        "nonprod": [
            {"name": "web-qa-01",  "class": "cmdb_ci_linux_server", "tier": "Tier 2", "business_service": "Online Banking",  "env_class": "NON-PROD"},
            {"name": "web-qa-02",  "class": "cmdb_ci_linux_server", "tier": "Tier 2", "business_service": "Online Banking",  "env_class": "NON-PROD"},
            {"name": "web-dev-01", "class": "cmdb_ci_linux_server", "tier": "Tier 3", "business_service": "Internal Tools",  "env_class": "NON-PROD"},
            {"name": "db-dev-01",  "class": "cmdb_ci_database",     "tier": "Tier 3", "business_service": "Internal Tools",  "env_class": "NON-PROD"}
        ],
        "unknown": []
    },
    "graph": {
        "nodes": [
            {"id": "1", "name": "web-prd-01", "env_class": "PROD",     "class": "cmdb_ci_linux_server"},
            {"id": "2", "name": "web-prd-02", "env_class": "PROD",     "class": "cmdb_ci_linux_server"},
            {"id": "3", "name": "db-prd-01",  "env_class": "PROD",     "class": "cmdb_ci_database"},
            {"id": "4", "name": "web-dr-01",  "env_class": "DR",       "class": "cmdb_ci_linux_server"},
            {"id": "5", "name": "web-qa-01",  "env_class": "NON-PROD", "class": "cmdb_ci_linux_server"}
        ],
        "edges": [
            {"from": "1", "to": "3", "type": "Runs on"},
            {"from": "2", "to": "3", "type": "Runs on"},
            {"from": "1", "to": "4", "type": "Failover to"},
            {"from": "5", "to": "3", "type": "Connects to"}
        ],
        "adjacency": {"1": ["3","4"], "2": ["3"], "5": ["3"]}
    },
    "impact": {
        "severity": "HIGH", "estimated_downtime_minutes": 30, "rollback_complexity": "MEDIUM",
        "affected_business_services": ["Online Banking", "Mobile App"],
        "risk_summary": "3 production servers will be offline during patching. Online Banking and Mobile App will be impacted.",
        "potential_failures": ["DB connection timeout", "Load balancer health check failure", "Session loss for active users"],
        "recommendations": ["Pre-notify customers 24hrs before", "Have DBA on standby", "Test rollback procedure beforehand"],
        "raw_llm_response": "Simulated for testing"
    }
}

# ── CHG 2 — Critical database upgrade ─────────────────────────
report2 = {
    "meta": {"chg_number": "CHG0012346", "analyzed_at": datetime.now().isoformat(), "elapsed_sec": 15},
    "change": {
        "chg_number": "CHG0012346", "description": "Upgrade Oracle DB from 19c to 21c on prod",
        "category": "Upgrade", "risk": "High", "impact": "Critical",
        "start_date": "2026-05-22 00:00:00", "end_date": "2026-05-22 06:00:00",
        "state": "Scheduled", "environment": "Production"
    },
    "ci_summary": {"PROD": 5, "DR": 2, "NON-PROD": 3, "UNKNOWN": 1},
    "ci_details": {
        "prod": [
            {"name": "db-prd-01",  "class": "cmdb_ci_database",     "tier": "Tier 1", "business_service": "Core Banking",    "env_class": "PROD"},
            {"name": "db-prd-02",  "class": "cmdb_ci_database",     "tier": "Tier 1", "business_service": "Core Banking",    "env_class": "PROD"},
            {"name": "app-prd-01", "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Core Banking",    "env_class": "PROD"},
            {"name": "app-prd-02", "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Payments",        "env_class": "PROD"},
            {"name": "mq-prd-01",  "class": "cmdb_ci_middleware",   "tier": "Tier 2", "business_service": "Payments",        "env_class": "PROD"}
        ],
        "dr": [
            {"name": "db-dr-01",  "class": "cmdb_ci_database",     "tier": "Tier 1", "business_service": "Core Banking",    "env_class": "DR"},
            {"name": "app-dr-01", "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Core Banking",    "env_class": "DR"}
        ],
        "nonprod": [
            {"name": "db-uat-01",  "class": "cmdb_ci_database",     "tier": "Tier 2", "business_service": "Core Banking",    "env_class": "NON-PROD"},
            {"name": "db-qa-01",   "class": "cmdb_ci_database",     "tier": "Tier 2", "business_service": "Core Banking",    "env_class": "NON-PROD"},
            {"name": "app-dev-01", "class": "cmdb_ci_linux_server", "tier": "Tier 3", "business_service": "Internal Tools",  "env_class": "NON-PROD"}
        ],
        "unknown": [{"name": "legacy-srv-01", "class": "cmdb_ci_server", "tier": "", "business_service": "", "env_class": "UNKNOWN"}]
    },
    "graph": {
        "nodes": [
            {"id": "1", "name": "db-prd-01",  "env_class": "PROD", "class": "cmdb_ci_database"},
            {"id": "2", "name": "db-prd-02",  "env_class": "PROD", "class": "cmdb_ci_database"},
            {"id": "3", "name": "app-prd-01", "env_class": "PROD", "class": "cmdb_ci_linux_server"},
            {"id": "4", "name": "db-dr-01",   "env_class": "DR",   "class": "cmdb_ci_database"}
        ],
        "edges": [
            {"from": "3", "to": "1", "type": "Reads from"},
            {"from": "3", "to": "2", "type": "Reads from"},
            {"from": "1", "to": "4", "type": "Replicates to"}
        ],
        "adjacency": {"3": ["1","2"], "1": ["4"]}
    },
    "impact": {
        "severity": "CRITICAL", "estimated_downtime_minutes": 180, "rollback_complexity": "HIGH",
        "affected_business_services": ["Core Banking", "Payments"],
        "risk_summary": "Major Oracle DB upgrade across 5 PROD servers. Core Banking and Payments offline for up to 3 hours. High rollback complexity.",
        "potential_failures": ["Application compatibility issues with 21c", "Long upgrade duration exceeds window", "Replication gap on DR"],
        "recommendations": ["Full backup before start", "UAT sign-off mandatory", "DBA lead + backup DBA on call", "Rollback plan rehearsed"],
        "raw_llm_response": "Simulated for testing"
    }
}

# ── CHG 3 — Low severity firewall ─────────────────────────────
report3 = {
    "meta": {"chg_number": "CHG0012347", "analyzed_at": datetime.now().isoformat(), "elapsed_sec": 8},
    "change": {
        "chg_number": "CHG0012347", "description": "Add firewall rule for new SaaS integration endpoint",
        "category": "Network", "risk": "Low", "impact": "Low",
        "start_date": "2026-05-21 10:00:00", "end_date": "2026-05-21 10:30:00",
        "state": "Scheduled", "environment": "Production"
    },
    "ci_summary": {"PROD": 1, "DR": 0, "NON-PROD": 0, "UNKNOWN": 0},
    "ci_details": {
        "prod":    [{"name": "fw-prd-core-01", "class": "cmdb_ci_firewall", "tier": "Tier 1", "business_service": "Network Infrastructure", "env_class": "PROD"}],
        "dr":      [], "nonprod": [], "unknown": []
    },
    "graph": {
        "nodes": [{"id": "1", "name": "fw-prd-core-01", "env_class": "PROD", "class": "cmdb_ci_firewall"}],
        "edges": [], "adjacency": {}
    },
    "impact": {
        "severity": "LOW", "estimated_downtime_minutes": 0, "rollback_complexity": "LOW",
        "affected_business_services": ["Network Infrastructure"],
        "risk_summary": "Single firewall rule addition. No downtime expected. Low risk, reversible within minutes.",
        "potential_failures": ["Rule misconfiguration blocking traffic", "Port conflict with existing rules"],
        "recommendations": ["Test in UAT first", "Have rollback rule ready", "Monitor traffic post-change"],
        "raw_llm_response": "Simulated for testing"
    }
}

# ── CHG 4 — Medium severity middleware ────────────────────────
report4 = {
    "meta": {"chg_number": "CHG0012348", "analyzed_at": datetime.now().isoformat(), "elapsed_sec": 10},
    "change": {
        "chg_number": "CHG0012348", "description": "MQ middleware upgrade - IBM MQ 9.2 to 9.3",
        "category": "Upgrade", "risk": "Medium", "impact": "Medium",
        "start_date": "2026-05-24 01:00:00", "end_date": "2026-05-24 03:00:00",
        "state": "Scheduled", "environment": "Production"
    },
    "ci_summary": {"PROD": 2, "DR": 1, "NON-PROD": 2, "UNKNOWN": 0},
    "ci_details": {
        "prod": [
            {"name": "mq-prd-01", "class": "cmdb_ci_middleware", "tier": "Tier 2", "business_service": "Payments",     "env_class": "PROD"},
            {"name": "mq-prd-02", "class": "cmdb_ci_middleware", "tier": "Tier 2", "business_service": "Notifications","env_class": "PROD"}
        ],
        "dr":      [{"name": "mq-dr-01",  "class": "cmdb_ci_middleware", "tier": "Tier 2", "business_service": "Payments", "env_class": "DR"}],
        "nonprod": [
            {"name": "mq-qa-01",  "class": "cmdb_ci_middleware", "tier": "Tier 3", "business_service": "Payments",     "env_class": "NON-PROD"},
            {"name": "mq-uat-01", "class": "cmdb_ci_middleware", "tier": "Tier 2", "business_service": "Payments",     "env_class": "NON-PROD"}
        ],
        "unknown": []
    },
    "graph": {
        "nodes": [
            {"id": "1", "name": "mq-prd-01", "env_class": "PROD", "class": "cmdb_ci_middleware"},
            {"id": "2", "name": "mq-prd-02", "env_class": "PROD", "class": "cmdb_ci_middleware"},
            {"id": "3", "name": "mq-dr-01",  "env_class": "DR",   "class": "cmdb_ci_middleware"}
        ],
        "edges": [
            {"from": "1", "to": "3", "type": "Replicates to"},
            {"from": "1", "to": "2", "type": "Cluster member"}
        ],
        "adjacency": {"1": ["3","2"]}
    },
    "impact": {
        "severity": "MEDIUM", "estimated_downtime_minutes": 45, "rollback_complexity": "MEDIUM",
        "affected_business_services": ["Payments", "Notifications"],
        "risk_summary": "MQ upgrade affects Payments and Notifications queues for ~45 min. Messages will queue during window.",
        "potential_failures": ["Queue depth buildup", "Message format incompatibility in 9.3", "DR replication gap"],
        "recommendations": ["Drain queues before start", "Test with Payments team in UAT", "Monitor queue depth post-upgrade"],
        "raw_llm_response": "Simulated for testing"
    }
}

# ── CHG 5 — Critical emergency CVE ────────────────────────────
report5 = {
    "meta": {"chg_number": "CHG0012349", "analyzed_at": datetime.now().isoformat(), "elapsed_sec": 18},
    "change": {
        "chg_number": "CHG0012349", "description": "Emergency CVE-2025-1234 patch - all production Linux servers",
        "category": "Patching", "risk": "High", "impact": "Critical",
        "start_date": "2026-05-25 23:00:00", "end_date": "2026-05-26 03:00:00",
        "state": "Scheduled", "environment": "Production"
    },
    "ci_summary": {"PROD": 8, "DR": 4, "NON-PROD": 6, "UNKNOWN": 0},
    "ci_details": {
        "prod": [
            {"name": "web-prd-01", "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Online Banking",  "env_class": "PROD"},
            {"name": "web-prd-02", "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Online Banking",  "env_class": "PROD"},
            {"name": "app-prd-01", "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Core Banking",    "env_class": "PROD"},
            {"name": "app-prd-02", "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Payments",        "env_class": "PROD"},
            {"name": "db-prd-01",  "class": "cmdb_ci_database",     "tier": "Tier 1", "business_service": "Core Banking",    "env_class": "PROD"},
            {"name": "db-prd-02",  "class": "cmdb_ci_database",     "tier": "Tier 1", "business_service": "Payments",        "env_class": "PROD"},
            {"name": "lb-prd-01",  "class": "cmdb_ci_lb",           "tier": "Tier 1", "business_service": "Online Banking",  "env_class": "PROD"},
            {"name": "mq-prd-01",  "class": "cmdb_ci_middleware",   "tier": "Tier 2", "business_service": "Payments",        "env_class": "PROD"}
        ],
        "dr": [
            {"name": "web-dr-01",  "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Online Banking",  "env_class": "DR"},
            {"name": "app-dr-01",  "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Mobile App",      "env_class": "DR"},
            {"name": "db-dr-01",   "class": "cmdb_ci_database",     "tier": "Tier 1", "business_service": "Core Banking",    "env_class": "DR"},
            {"name": "lb-dr-01",   "class": "cmdb_ci_lb",           "tier": "Tier 1", "business_service": "Online Banking",  "env_class": "DR"}
        ],
        "nonprod": [
            {"name": "web-qa-01",  "class": "cmdb_ci_linux_server", "tier": "Tier 2", "business_service": "Online Banking",  "env_class": "NON-PROD"},
            {"name": "app-qa-01",  "class": "cmdb_ci_linux_server", "tier": "Tier 2", "business_service": "Mobile App",      "env_class": "NON-PROD"},
            {"name": "db-qa-01",   "class": "cmdb_ci_database",     "tier": "Tier 2", "business_service": "Core Banking",    "env_class": "NON-PROD"},
            {"name": "web-dev-01", "class": "cmdb_ci_linux_server", "tier": "Tier 3", "business_service": "Internal Tools",  "env_class": "NON-PROD"},
            {"name": "app-dev-01", "class": "cmdb_ci_linux_server", "tier": "Tier 3", "business_service": "Internal Tools",  "env_class": "NON-PROD"},
            {"name": "db-dev-01",  "class": "cmdb_ci_database",     "tier": "Tier 3", "business_service": "Internal Tools",  "env_class": "NON-PROD"}
        ],
        "unknown": []
    },
    "graph": {
        "nodes": [
            {"id": "1", "name": "lb-prd-01",  "env_class": "PROD", "class": "cmdb_ci_lb"},
            {"id": "2", "name": "web-prd-01", "env_class": "PROD", "class": "cmdb_ci_linux_server"},
            {"id": "3", "name": "web-prd-02", "env_class": "PROD", "class": "cmdb_ci_linux_server"},
            {"id": "4", "name": "app-prd-01", "env_class": "PROD", "class": "cmdb_ci_linux_server"},
            {"id": "5", "name": "db-prd-01",  "env_class": "PROD", "class": "cmdb_ci_database"},
            {"id": "6", "name": "db-dr-01",   "env_class": "DR",   "class": "cmdb_ci_database"}
        ],
        "edges": [
            {"from": "1", "to": "2", "type": "Routes to"},
            {"from": "1", "to": "3", "type": "Routes to"},
            {"from": "2", "to": "4", "type": "Calls"},
            {"from": "3", "to": "4", "type": "Calls"},
            {"from": "4", "to": "5", "type": "Reads from"},
            {"from": "5", "to": "6", "type": "Replicates to"}
        ],
        "adjacency": {"1": ["2","3"], "2": ["4"], "3": ["4"], "4": ["5"], "5": ["6"]}
    },
    "impact": {
        "severity": "CRITICAL", "estimated_downtime_minutes": 120, "rollback_complexity": "LOW",
        "affected_business_services": ["Online Banking", "Mobile App", "Core Banking", "Payments"],
        "risk_summary": "Emergency security patch across 8 production servers. All major business services affected. Patch is mandatory due to active CVE.",
        "potential_failures": ["Rolling restart may cause brief session drops", "Load balancer health check gaps", "DB replication lag during restart"],
        "recommendations": ["Patch servers in rolling fashion", "Keep DR ready for failover", "Monitor all services post-patch", "Notify security team on completion"],
        "raw_llm_response": "Simulated for testing"
    }
}


# ════════════════════════════════════════════════════════════════
#  NEW ExaCC REPORTS (CHG0003774804, 900, 775100, 776200, 778500)
#  Based on the real ServiceNow ExaCC switchover pattern.
# ════════════════════════════════════════════════════════════════

# ── CHG 6 — ExaCC PRD→DR Switchover (real pattern) ────────────
report6 = {
    "meta": {"chg_number": "CHG0003774804", "analyzed_at": datetime.now().isoformat(), "elapsed_sec": 11},
    "change": {
        "chg_number": "CHG0003774804",
        "description": "Switchover of ExaCC databases currently running as PRD/Primary in one set of data centres to another. "
                       "UK: CDC->WDC | Germany: DCN->DCB | Singapore: 9TS->DSJ | New York: 2PK->CORP | IN: BKC->Tata. "
                       "In case the DB is already running in the target data centre, then no switchover will be performed.",
        "category": "Database", "risk": "Low", "impact": "2",
        "start_date": "2025-04-05 22:00:00", "end_date": "2025-04-05 23:30:00",
        "state": "Scheduled", "environment": "Production"
    },
    "ci_summary": {"PROD": 10, "DR": 5, "NON-PROD": 0, "UNKNOWN": 0},
    "ci_details": {
        "prod": [
            {"name": "exacc-uk-cdc-prd-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform",  "env_class": "PROD"},
            {"name": "exacc-uk-cdc-prd-02",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Risk Management",          "env_class": "PROD"},
            {"name": "exacc-uk-cdc-prd-03",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Regulatory Reporting",      "env_class": "PROD"},
            {"name": "exacc-de-dcn-prd-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform",  "env_class": "PROD"},
            {"name": "exacc-de-dcn-prd-02",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Core Banking Europe",       "env_class": "PROD"},
            {"name": "exacc-sg-9ts-prd-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "APAC Trading Platform",    "env_class": "PROD"},
            {"name": "exacc-sg-9ts-prd-02",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "APAC Risk Management",     "env_class": "PROD"},
            {"name": "exacc-ny-2pk-prd-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Americas Trading Platform","env_class": "PROD"},
            {"name": "exacc-ny-2pk-prd-02",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Americas Risk Management", "env_class": "PROD"},
            {"name": "exacc-in-bkc-prd-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "India Core Banking",       "env_class": "PROD"},
        ],
        "dr": [
            {"name": "exacc-uk-wdc-dr-01",   "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform",  "env_class": "DR"},
            {"name": "exacc-uk-wdc-dr-02",   "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Risk Management",          "env_class": "DR"},
            {"name": "exacc-de-dcb-dr-01",   "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform",  "env_class": "DR"},
            {"name": "exacc-sg-dsj-dr-01",   "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "APAC Trading Platform",    "env_class": "DR"},
            {"name": "exacc-ny-corp-dr-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Americas Trading Platform","env_class": "DR"},
        ],
        "nonprod": [], "unknown": []
    },
    "graph": {
        "nodes": [
            {"id": "1",  "name": "exacc-uk-cdc-prd-01", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
            {"id": "2",  "name": "exacc-uk-wdc-dr-01",  "env_class": "DR",   "class": "cmdb_ci_db_ora_instance"},
            {"id": "3",  "name": "exacc-de-dcn-prd-01", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
            {"id": "4",  "name": "exacc-de-dcb-dr-01",  "env_class": "DR",   "class": "cmdb_ci_db_ora_instance"},
            {"id": "5",  "name": "exacc-sg-9ts-prd-01", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
            {"id": "6",  "name": "exacc-sg-dsj-dr-01",  "env_class": "DR",   "class": "cmdb_ci_db_ora_instance"},
            {"id": "7",  "name": "exacc-ny-2pk-prd-01", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
            {"id": "8",  "name": "exacc-ny-corp-dr-01", "env_class": "DR",   "class": "cmdb_ci_db_ora_instance"},
            {"id": "9",  "name": "exacc-in-bkc-prd-01", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
            {"id": "10", "name": "oracle-dg-broker-global-01", "env_class": "PROD", "class": "cmdb_ci_middleware"}
        ],
        "edges": [
            {"from": "1",  "to": "2",  "type": "Failover target"},
            {"from": "3",  "to": "4",  "type": "Failover target"},
            {"from": "5",  "to": "6",  "type": "Failover target"},
            {"from": "7",  "to": "8",  "type": "Failover target"},
            {"from": "1",  "to": "10", "type": "Managed by"},
            {"from": "3",  "to": "10", "type": "Managed by"},
            {"from": "5",  "to": "10", "type": "Managed by"},
            {"from": "9",  "to": "10", "type": "Managed by"},
        ],
        "adjacency": {"1": ["2","10"], "3": ["4","10"], "5": ["6","10"], "7": ["8"], "9": ["10"]}
    },
    "impact": {
        "severity": "MEDIUM",
        "estimated_downtime_minutes": 30,
        "rollback_complexity": "LOW",
        "affected_business_services": [
            "Global Trading Platform", "Risk Management", "Regulatory Reporting",
            "Core Banking Europe", "APAC Trading Platform", "APAC Risk Management",
            "Americas Trading Platform", "Americas Risk Management", "India Core Banking"
        ],
        "risk_summary": "ExaCC PRD->DR switchover across 5 global data centres using proven Oracle Data Guard DGMGRL commands. "
                        "Max 30 min application downtime per region. Low risk as this is a standard, rehearsed procedure. "
                        "DBA team on standby. If DB is already in target DC, no switchover performed.",
        "potential_failures": [
            "Network latency spike between source and target DC during switchover",
            "Redo log gap if replication lag > threshold at time of switchover",
            "Application reconnection failures if connection pool not drained",
            "Switchover taking >30 min if redo apply is behind",
        ],
        "recommendations": [
            "Verify Data Guard replication is in sync (< 5 min lag) before initiating each region",
            "Pre-notify application teams to expect 30 min DB downtime per region",
            "Have DBA lead (Sanchit Saumay) and backup DBA on bridge call throughout window",
            "Monitor via Oracle Enterprise Manager after each regional switchover",
            "Contact: Exacc_patching_group@list.db.com if issues arise",
        ],
        "raw_llm_response": "Simulated for testing"
    }
}

# ── CHG 7 — ExaCC Infrastructure Patching post-switchover ─────
report7 = {
    "meta": {"chg_number": "CHG0003774900", "analyzed_at": datetime.now().isoformat(), "elapsed_sec": 9},
    "change": {
        "chg_number": "CHG0003774900",
        "description": "OS, GI and Infrastructure patching of ExaCC servers in UK CDC and Germany DCN data centres "
                       "following PRD->DR switchover (CHG0003774804). Databases already moved to WDC/DCB. "
                       "Zero application impact expected as databases are already in DR data centres.",
        "category": "Patching", "risk": "Medium", "impact": "2",
        "start_date": "2025-04-12 22:00:00", "end_date": "2025-04-13 04:00:00",
        "state": "Scheduled", "environment": "Production"
    },
    "ci_summary": {"PROD": 3, "DR": 2, "NON-PROD": 0, "UNKNOWN": 0},
    "ci_details": {
        "prod": [
            {"name": "exacc-uk-cdc-prd-01", "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform", "env_class": "PROD"},
            {"name": "exacc-uk-cdc-prd-02", "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Risk Management",         "env_class": "PROD"},
            {"name": "exacc-de-dcn-prd-01", "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform", "env_class": "PROD"},
        ],
        "dr": [
            {"name": "exacc-uk-wdc-dr-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform", "env_class": "DR"},
            {"name": "exacc-de-dcb-dr-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform", "env_class": "DR"},
        ],
        "nonprod": [], "unknown": []
    },
    "graph": {
        "nodes": [
            {"id": "1", "name": "exacc-uk-cdc-prd-01", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
            {"id": "2", "name": "exacc-uk-wdc-dr-01",  "env_class": "DR",   "class": "cmdb_ci_db_ora_instance"},
            {"id": "3", "name": "exacc-de-dcn-prd-01", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
            {"id": "4", "name": "exacc-de-dcb-dr-01",  "env_class": "DR",   "class": "cmdb_ci_db_ora_instance"},
        ],
        "edges": [
            {"from": "1", "to": "2", "type": "Currently failed over to"},
            {"from": "3", "to": "4", "type": "Currently failed over to"},
        ],
        "adjacency": {"1": ["2"], "3": ["4"]}
    },
    "impact": {
        "severity": "LOW",
        "estimated_downtime_minutes": 0,
        "rollback_complexity": "LOW",
        "affected_business_services": ["Global Trading Platform", "Risk Management"],
        "risk_summary": "ExaCC infrastructure patching with zero application impact. "
                        "Databases already failed over to DR DCs (WDC/DCB). "
                        "Patching the now-idle PRD nodes in UK CDC and Germany DCN. "
                        "Applications connected to DR nodes throughout — no interruption.",
        "potential_failures": [
            "Patch application failure requiring node restart beyond window",
            "GI upgrade rollback needed if cluster resource issue found",
        ],
        "recommendations": [
            "Confirm applications are running from WDC/DCB before starting patches",
            "Do not initiate switchback until all patching verified complete",
            "DBA monitoring of DR node health throughout window",
        ],
        "raw_llm_response": "Simulated for testing"
    }
}

# ── CHG 8 — ExaCC Switchback DR→PRD ───────────────────────────
report8 = {
    "meta": {"chg_number": "CHG0003775100", "analyzed_at": datetime.now().isoformat(), "elapsed_sec": 10},
    "change": {
        "chg_number": "CHG0003775100",
        "description": "Switchback of ExaCC databases from DR back to PRD data centres after infrastructure patching is complete. "
                       "UK: WDC->CDC | Germany: DCB->DCN | Singapore: DSJ->9TS | New York: CORP->2PK | IN: Tata->BKC. "
                       "Switchback takes a maximum of 30 min per region.",
        "category": "Database", "risk": "Low", "impact": "2",
        "start_date": "2025-04-19 22:00:00", "end_date": "2025-04-19 23:30:00",
        "state": "Scheduled", "environment": "Production"
    },
    "ci_summary": {"PROD": 5, "DR": 5, "NON-PROD": 0, "UNKNOWN": 0},
    "ci_details": {
        "prod": [
            {"name": "exacc-uk-cdc-prd-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform",  "env_class": "PROD"},
            {"name": "exacc-de-dcn-prd-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform",  "env_class": "PROD"},
            {"name": "exacc-sg-9ts-prd-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "APAC Trading Platform",    "env_class": "PROD"},
            {"name": "exacc-ny-2pk-prd-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Americas Trading Platform","env_class": "PROD"},
            {"name": "exacc-in-bkc-prd-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "India Core Banking",       "env_class": "PROD"},
        ],
        "dr": [
            {"name": "exacc-uk-wdc-dr-01",   "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform",  "env_class": "DR"},
            {"name": "exacc-de-dcb-dr-01",   "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform",  "env_class": "DR"},
            {"name": "exacc-sg-dsj-dr-01",   "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "APAC Trading Platform",    "env_class": "DR"},
            {"name": "exacc-ny-corp-dr-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Americas Trading Platform","env_class": "DR"},
            {"name": "exacc-in-tata-dr-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "India Core Banking",       "env_class": "DR"},
        ],
        "nonprod": [], "unknown": []
    },
    "graph": {
        "nodes": [
            {"id": "1", "name": "exacc-uk-wdc-dr-01",  "env_class": "DR",   "class": "cmdb_ci_db_ora_instance"},
            {"id": "2", "name": "exacc-uk-cdc-prd-01", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
            {"id": "3", "name": "exacc-de-dcb-dr-01",  "env_class": "DR",   "class": "cmdb_ci_db_ora_instance"},
            {"id": "4", "name": "exacc-de-dcn-prd-01", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
        ],
        "edges": [
            {"from": "1", "to": "2", "type": "Switchback target"},
            {"from": "3", "to": "4", "type": "Switchback target"},
        ],
        "adjacency": {"1": ["2"], "3": ["4"]}
    },
    "impact": {
        "severity": "MEDIUM",
        "estimated_downtime_minutes": 30,
        "rollback_complexity": "LOW",
        "affected_business_services": [
            "Global Trading Platform", "APAC Trading Platform",
            "Americas Trading Platform", "India Core Banking"
        ],
        "risk_summary": "Switchback from DR to PRD post-patching. Max 30 min DB downtime per region. "
                        "Lower risk than initial switchover as patched PRD nodes are already verified. "
                        "Restores normal operational topology.",
        "potential_failures": [
            "Redo log gap if replication not fully in sync after patching",
            "Application reconnection delay",
        ],
        "recommendations": [
            "Verify Data Guard sync status before each regional switchback",
            "Execute switchbacks in same order as switchovers (IN, SG, DE, UK, NY)",
            "Monitor OEM after each switchback before proceeding to next region",
        ],
        "raw_llm_response": "Simulated for testing"
    }
}

# ── CHG 9 — ExaCC Singapore Emergency Failover ────────────────
report9 = {
    "meta": {"chg_number": "CHG0003776200", "analyzed_at": datetime.now().isoformat(), "elapsed_sec": 7},
    "change": {
        "chg_number": "CHG0003776200",
        "description": "Unplanned failover of ExaCC Singapore cluster from 9TS to DSJ due to storage controller failure "
                       "on 9TS-NODE-03. Databases: SG_CORE_DB_01, SG_TRADE_DB_01, SG_RISK_DB_01 impacted. "
                       "DBA team executing manual switchover using proven DGMGRL commands. "
                       "Expected application downtime 15-30 min. "
                       "Root cause: Storage controller firmware bug in ExaCC X9M rack.",
        "category": "Database", "risk": "High", "impact": "1",
        "start_date": "2025-05-03 14:30:00", "end_date": "2025-05-03 15:30:00",
        "state": "In Progress", "environment": "Production"
    },
    "ci_summary": {"PROD": 2, "DR": 1, "NON-PROD": 0, "UNKNOWN": 0},
    "ci_details": {
        "prod": [
            {"name": "exacc-sg-9ts-prd-01", "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "APAC Trading Platform",  "env_class": "PROD"},
            {"name": "exacc-sg-9ts-prd-02", "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "APAC Risk Management",   "env_class": "PROD"},
        ],
        "dr": [
            {"name": "exacc-sg-dsj-dr-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "APAC Trading Platform",  "env_class": "DR"},
        ],
        "nonprod": [], "unknown": []
    },
    "graph": {
        "nodes": [
            {"id": "1", "name": "exacc-sg-9ts-prd-01", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
            {"id": "2", "name": "exacc-sg-9ts-prd-02", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
            {"id": "3", "name": "exacc-sg-dsj-dr-01",  "env_class": "DR",   "class": "cmdb_ci_db_ora_instance"},
        ],
        "edges": [
            {"from": "1", "to": "3", "type": "Emergency failover to"},
            {"from": "2", "to": "3", "type": "Cluster peer"},
        ],
        "adjacency": {"1": ["3"], "2": ["3"]}
    },
    "impact": {
        "severity": "HIGH",
        "estimated_downtime_minutes": 25,
        "rollback_complexity": "MEDIUM",
        "affected_business_services": ["APAC Trading Platform", "APAC Risk Management"],
        "risk_summary": "Unplanned emergency failover due to ExaCC X9M storage controller firmware bug in Singapore 9TS. "
                        "APAC Trading and Risk systems offline 15-30 min during DGMGRL-managed switchover to DSJ. "
                        "Hardware replacement required before switchback.",
        "potential_failures": [
            "Data loss if redo log gap exists at time of storage failure",
            "DSJ node capacity insufficient for full PRD workload",
            "APAC market hours impact (SGX trading session)",
        ],
        "recommendations": [
            "Immediate: Execute DGMGRL switchover to DSJ with DBA lead on call",
            "Notify APAC Trading desk and Risk Management immediately",
            "Engage Oracle support for ExaCC firmware bug — SR to be raised",
            "Do NOT switchback until 9TS storage controller replaced and verified",
            "Root cause: escalate to ExaCC hardware team",
        ],
        "raw_llm_response": "Simulated for testing"
    }
}

# ── CHG 10 — ExaCC Full Quarterly Maintenance (all regions) ───
report10 = {
    "meta": {"chg_number": "CHG0003778500", "analyzed_at": datetime.now().isoformat(), "elapsed_sec": 14},
    "change": {
        "chg_number": "CHG0003778500",
        "description": "Coordinated quarterly ExaCC maintenance across all 5 global regions. "
                       "Includes: OS patching, GI upgrade 19.22->19.23, ExaCC firmware update, storage rebalancing. "
                       "Sequence (rolling): Week1 IN BKC, Week2 SG 9TS, Week3 DE DCN, Week4 UK CDC, Week5 NY 2PK, Week6 All switchbacks. "
                       "Max DB downtime per region: 30 min. Total program: 6 weeks.",
        "category": "Maintenance", "risk": "Medium", "impact": "2",
        "start_date": "2025-06-01 00:00:00", "end_date": "2025-07-12 06:00:00",
        "state": "Scheduled", "environment": "Production"
    },
    "ci_summary": {"PROD": 10, "DR": 5, "NON-PROD": 0, "UNKNOWN": 0},
    "ci_details": {
        "prod": [
            {"name": "exacc-uk-cdc-prd-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform",  "env_class": "PROD"},
            {"name": "exacc-uk-cdc-prd-02",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Risk Management",          "env_class": "PROD"},
            {"name": "exacc-de-dcn-prd-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform",  "env_class": "PROD"},
            {"name": "exacc-de-dcn-prd-02",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Core Banking Europe",       "env_class": "PROD"},
            {"name": "exacc-sg-9ts-prd-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "APAC Trading Platform",    "env_class": "PROD"},
            {"name": "exacc-sg-9ts-prd-02",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "APAC Risk Management",     "env_class": "PROD"},
            {"name": "exacc-ny-2pk-prd-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Americas Trading Platform","env_class": "PROD"},
            {"name": "exacc-ny-2pk-prd-02",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Americas Risk Management", "env_class": "PROD"},
            {"name": "exacc-in-bkc-prd-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "India Core Banking",       "env_class": "PROD"},
            {"name": "exacc-in-bkc-prd-02",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "India Payments",           "env_class": "PROD"},
        ],
        "dr": [
            {"name": "exacc-uk-wdc-dr-01",   "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform",  "env_class": "DR"},
            {"name": "exacc-de-dcb-dr-01",   "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Global Trading Platform",  "env_class": "DR"},
            {"name": "exacc-sg-dsj-dr-01",   "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "APAC Trading Platform",    "env_class": "DR"},
            {"name": "exacc-ny-corp-dr-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "Americas Trading Platform","env_class": "DR"},
            {"name": "exacc-in-tata-dr-01",  "class": "cmdb_ci_db_ora_instance", "tier": "Tier-1", "business_service": "India Core Banking",       "env_class": "DR"},
        ],
        "nonprod": [], "unknown": []
    },
    "graph": {
        "nodes": [
            {"id": "1",  "name": "exacc-uk-cdc-prd-01", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
            {"id": "2",  "name": "exacc-uk-wdc-dr-01",  "env_class": "DR",   "class": "cmdb_ci_db_ora_instance"},
            {"id": "3",  "name": "exacc-de-dcn-prd-01", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
            {"id": "4",  "name": "exacc-de-dcb-dr-01",  "env_class": "DR",   "class": "cmdb_ci_db_ora_instance"},
            {"id": "5",  "name": "exacc-sg-9ts-prd-01", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
            {"id": "6",  "name": "exacc-sg-dsj-dr-01",  "env_class": "DR",   "class": "cmdb_ci_db_ora_instance"},
            {"id": "7",  "name": "exacc-ny-2pk-prd-01", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
            {"id": "8",  "name": "exacc-ny-corp-dr-01", "env_class": "DR",   "class": "cmdb_ci_db_ora_instance"},
            {"id": "9",  "name": "exacc-in-bkc-prd-01", "env_class": "PROD", "class": "cmdb_ci_db_ora_instance"},
            {"id": "10", "name": "exacc-in-tata-dr-01", "env_class": "DR",   "class": "cmdb_ci_db_ora_instance"},
        ],
        "edges": [
            {"from": "1", "to": "2",  "type": "Failover target"},
            {"from": "3", "to": "4",  "type": "Failover target"},
            {"from": "5", "to": "6",  "type": "Failover target"},
            {"from": "7", "to": "8",  "type": "Failover target"},
            {"from": "9", "to": "10", "type": "Failover target"},
        ],
        "adjacency": {"1": ["2"], "3": ["4"], "5": ["6"], "7": ["8"], "9": ["10"]}
    },
    "impact": {
        "severity": "MEDIUM",
        "estimated_downtime_minutes": 30,
        "rollback_complexity": "LOW",
        "affected_business_services": [
            "Global Trading Platform", "Risk Management", "Core Banking Europe",
            "APAC Trading Platform", "APAC Risk Management",
            "Americas Trading Platform", "Americas Risk Management",
            "India Core Banking", "India Payments"
        ],
        "risk_summary": "Full quarterly ExaCC maintenance across all 5 global data centres. "
                        "Rolling 6-week program. Each region has 30 min DB downtime during switchover only. "
                        "GI upgrade 19.22->19.23 is well-tested. Firmware update is standard ExaCC process. "
                        "Primary risk is coordination complexity across regions and time zones.",
        "potential_failures": [
            "GI upgrade rollback needed if cluster resource issue in one region delays program",
            "Firmware update failure requiring Oracle hardware support engagement",
            "Cumulative schedule slip if any region overruns its window",
            "Cross-region replication gap if network latency spikes during maintenance",
        ],
        "recommendations": [
            "Establish a 6-week change calendar with regional CAB sign-offs for each week",
            "Run IN region first as pilot — smallest risk, lessons applied to remaining regions",
            "Bridge call with all regional DBA leads every Sunday during program",
            "Keep CHG0003774804 as the reference template for per-region switchover procedure",
            "Full program sign-off from global.database@db.com and oracloud-team-ops@list.db.com",
        ],
        "raw_llm_response": "Simulated for testing"
    }
}


# ════════════════════════════════════════════════════════════════
#  STEP 1 — Save all 10 reports to disk
# ════════════════════════════════════════════════════════════════
all_reports = [report1, report2, report3, report4, report5,
               report6, report7, report8, report9, report10]

print("\nStep 1: Saving 10 CHG reports to reports/ folder...\n")
saved_files = []
for report in all_reports:
    saved_files.append(save_report(report))


# ════════════════════════════════════════════════════════════════
#  STEP 2 — Ingest all reports into FAISS RAG
# ════════════════════════════════════════════════════════════════
print("\nStep 2: Ingesting reports into FAISS vector store (RAG)...")
print("  (This calls the Gemini embedding API — needs GEMINI_API_KEY)\n")

try:
    from rag.easy_rag import EasyRAG
    rag = EasyRAG()

    for report in all_reports:
        chg = report["meta"]["chg_number"]
        rag.ingest(report)

    stats = rag.get_stats()
    print(f"\n  RAG index now contains {stats['indexed_changes']} vectors")
    rag_ok = True

except Exception as e:
    print(f"\n  [WARNING] RAG ingestion skipped: {e}")
    print("  Reports are saved to disk — run this script again once GEMINI_API_KEY is set.")
    rag_ok = False


# ════════════════════════════════════════════════════════════════
#  SUMMARY
# ════════════════════════════════════════════════════════════════
rag_status = "READY" if rag_ok else "SKIPPED (no API key)"
print(f"""
╔══════════════════════════════════════════════════════════════╗
║          FlowMaster test data setup complete (v2)            ║
╠══════════════════════════════════════════════════════════════╣
║  ORIGINAL 5 CHGs:                                            ║
║  CHG0012345 — OS Patching               → HIGH              ║
║  CHG0012346 — Oracle DB Upgrade         → CRITICAL          ║
║  CHG0012347 — Firewall Rules            → LOW               ║
║  CHG0012348 — MQ Middleware             → MEDIUM            ║
║  CHG0012349 — Emergency CVE Patch       → CRITICAL          ║
╠══════════════════════════════════════════════════════════════╣
║  NEW ExaCC REAL-WORLD CHGs:                                  ║
║  CHG0003774804 — ExaCC PRD→DR Switchover   → MEDIUM         ║
║  CHG0003774900 — ExaCC Infra Patching      → LOW            ║
║  CHG0003775100 — ExaCC DR→PRD Switchback   → MEDIUM         ║
║  CHG0003776200 — SG Emergency Failover     → HIGH           ║
║  CHG0003778500 — Full Quarterly Maintenance → MEDIUM        ║
╠══════════════════════════════════════════════════════════════╣
║  Reports saved  : reports/                                   ║
║  RAG ingestion  : {rag_status:<42}║
╚══════════════════════════════════════════════════════════════╝

Next step → run: streamlit run app.py

Try these in the chatbot:
  CHG0003774804  — ExaCC DB switchover (matches your real SNOW screenshot)
  CHG0003776200  — Singapore emergency failover
  CHG0003778500  — Full quarterly maintenance program
""")
