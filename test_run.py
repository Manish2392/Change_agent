# test_run.py — Creates 5 test CHG reports AND ingests them into FAISS RAG
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
        "dr":      [{"name": "web-dr-01",  "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Online Banking", "env_class": "DR"}],
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
            {"name": "db-dr-01",   "class": "cmdb_ci_database",     "tier": "Tier 1", "business_service": "Core Banking",    "env_class": "DR"},
            {"name": "app-dr-01",  "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Core Banking",    "env_class": "DR"}
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
            {"id": "4", "name": "app-prd-02", "env_class": "PROD", "class": "cmdb_ci_linux_server"},
            {"id": "5", "name": "db-dr-01",   "env_class": "DR",   "class": "cmdb_ci_database"}
        ],
        "edges": [
            {"from": "3", "to": "1", "type": "Connects to"},
            {"from": "4", "to": "2", "type": "Connects to"},
            {"from": "1", "to": "5", "type": "Replicates to"},
            {"from": "2", "to": "5", "type": "Replicates to"}
        ],
        "adjacency": {"3": ["1"], "4": ["2"], "1": ["5"], "2": ["5"]}
    },
    "impact": {
        "severity": "CRITICAL", "estimated_downtime_minutes": 360, "rollback_complexity": "HIGH",
        "affected_business_services": ["Core Banking", "Payments", "Mobile App"],
        "risk_summary": "Critical database upgrade affecting Core Banking and Payments. 6 hour downtime window with HIGH rollback complexity.",
        "potential_failures": ["Data migration failure", "Application compatibility issues", "Replication lag to DR", "Transaction rollback failures"],
        "recommendations": ["Full backup before upgrade", "Test on UAT first", "Keep DBA and app team on standby", "Prepare rollback script", "Customer communication 48hrs prior"],
        "raw_llm_response": "Simulated for testing"
    }
}

# ── CHG 3 — Low risk network change ───────────────────────────
report3 = {
    "meta": {"chg_number": "CHG0012347", "analyzed_at": datetime.now().isoformat(), "elapsed_sec": 8},
    "change": {
        "chg_number": "CHG0012347", "description": "Update firewall rules for new payment gateway",
        "category": "Network", "risk": "Low", "impact": "Low",
        "start_date": "2026-05-21 22:00:00", "end_date": "2026-05-21 23:00:00",
        "state": "Approved", "environment": "Production"
    },
    "ci_summary": {"PROD": 2, "DR": 1, "NON-PROD": 1, "UNKNOWN": 0},
    "ci_details": {
        "prod": [
            {"name": "fw-prd-01", "class": "cmdb_ci_firewall", "tier": "Tier 1", "business_service": "Payments", "env_class": "PROD"},
            {"name": "fw-prd-02", "class": "cmdb_ci_firewall", "tier": "Tier 1", "business_service": "Payments", "env_class": "PROD"}
        ],
        "dr":      [{"name": "fw-dr-01",  "class": "cmdb_ci_firewall", "tier": "Tier 1", "business_service": "Payments", "env_class": "DR"}],
        "nonprod": [{"name": "fw-qa-01",  "class": "cmdb_ci_firewall", "tier": "Tier 2", "business_service": "Payments", "env_class": "NON-PROD"}],
        "unknown": []
    },
    "graph": {
        "nodes": [
            {"id": "1", "name": "fw-prd-01", "env_class": "PROD", "class": "cmdb_ci_firewall"},
            {"id": "2", "name": "fw-prd-02", "env_class": "PROD", "class": "cmdb_ci_firewall"},
            {"id": "3", "name": "fw-dr-01",  "env_class": "DR",   "class": "cmdb_ci_firewall"}
        ],
        "edges": [
            {"from": "1", "to": "2", "type": "Redundant pair"},
            {"from": "1", "to": "3", "type": "Failover to"}
        ],
        "adjacency": {"1": ["2", "3"]}
    },
    "impact": {
        "severity": "LOW", "estimated_downtime_minutes": 0, "rollback_complexity": "LOW",
        "affected_business_services": ["Payments"],
        "risk_summary": "Low risk firewall rule update. No downtime expected. Rollback is simple rule revert.",
        "potential_failures": ["Brief packet drop during rule reload", "New gateway IP not whitelisted correctly"],
        "recommendations": ["Test new rules in QA first", "Monitor payment transactions for 30 mins post-change"],
        "raw_llm_response": "Simulated for testing"
    }
}

# ── CHG 4 — Medium risk middleware update ──────────────────────
report4 = {
    "meta": {"chg_number": "CHG0012348", "analyzed_at": datetime.now().isoformat(), "elapsed_sec": 10},
    "change": {
        "chg_number": "CHG0012348", "description": "Upgrade MQ middleware to version 9.3",
        "category": "Upgrade", "risk": "Medium", "impact": "Medium",
        "start_date": "2026-05-23 01:00:00", "end_date": "2026-05-23 03:00:00",
        "state": "Pending Approval", "environment": "Production"
    },
    "ci_summary": {"PROD": 2, "DR": 1, "NON-PROD": 3, "UNKNOWN": 0},
    "ci_details": {
        "prod": [
            {"name": "mq-prd-01", "class": "cmdb_ci_middleware", "tier": "Tier 2", "business_service": "Payments",     "env_class": "PROD"},
            {"name": "mq-prd-02", "class": "cmdb_ci_middleware", "tier": "Tier 2", "business_service": "Notifications","env_class": "PROD"}
        ],
        "dr":      [{"name": "mq-dr-01",  "class": "cmdb_ci_middleware", "tier": "Tier 2", "business_service": "Payments", "env_class": "DR"}],
        "nonprod": [
            {"name": "mq-uat-01", "class": "cmdb_ci_middleware", "tier": "Tier 2", "business_service": "Payments",     "env_class": "NON-PROD"},
            {"name": "mq-qa-01",  "class": "cmdb_ci_middleware", "tier": "Tier 2", "business_service": "Payments",     "env_class": "NON-PROD"},
            {"name": "mq-dev-01", "class": "cmdb_ci_middleware", "tier": "Tier 3", "business_service": "Payments",     "env_class": "NON-PROD"}
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
            {"from": "1", "to": "2", "type": "Cluster peer"},
            {"from": "1", "to": "3", "type": "Replicates to"}
        ],
        "adjacency": {"1": ["2", "3"]}
    },
    "impact": {
        "severity": "MEDIUM", "estimated_downtime_minutes": 45, "rollback_complexity": "MEDIUM",
        "affected_business_services": ["Payments", "Notifications"],
        "risk_summary": "Middleware upgrade affecting Payments and Notifications queues. 45 min downtime expected during upgrade.",
        "potential_failures": ["Message queue backlog during restart", "Consumer reconnection failures", "Config file incompatibility in v9.3"],
        "recommendations": ["Drain queues before upgrade", "Monitor consumer lag post-upgrade", "Keep v9.2 config as backup"],
        "raw_llm_response": "Simulated for testing"
    }
}

# ── CHG 5 — Critical security patch ───────────────────────────
report5 = {
    "meta": {"chg_number": "CHG0012349", "analyzed_at": datetime.now().isoformat(), "elapsed_sec": 18},
    "change": {
        "chg_number": "CHG0012349", "description": "Emergency security patch — CVE-2026-1234 on all prod servers",
        "category": "Security", "risk": "High", "impact": "Critical",
        "start_date": "2026-05-19 20:00:00", "end_date": "2026-05-19 23:00:00",
        "state": "In Progress", "environment": "Production"
    },
    "ci_summary": {"PROD": 8, "DR": 4, "NON-PROD": 6, "UNKNOWN": 0},
    "ci_details": {
        "prod": [
            {"name": "web-prd-01", "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Online Banking",  "env_class": "PROD"},
            {"name": "web-prd-02", "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Online Banking",  "env_class": "PROD"},
            {"name": "app-prd-01", "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Mobile App",      "env_class": "PROD"},
            {"name": "app-prd-02", "class": "cmdb_ci_linux_server", "tier": "Tier 1", "business_service": "Mobile App",      "env_class": "PROD"},
            {"name": "db-prd-01",  "class": "cmdb_ci_database",     "tier": "Tier 1", "business_service": "Core Banking",    "env_class": "PROD"},
            {"name": "db-prd-02",  "class": "cmdb_ci_database",     "tier": "Tier 1", "business_service": "Core Banking",    "env_class": "PROD"},
            {"name": "mq-prd-01",  "class": "cmdb_ci_middleware",   "tier": "Tier 2", "business_service": "Payments",        "env_class": "PROD"},
            {"name": "lb-prd-01",  "class": "cmdb_ci_lb",           "tier": "Tier 1", "business_service": "Online Banking",  "env_class": "PROD"}
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

# ══════════════════════════════════════════════════════════════
#  STEP 1 — Save all 5 reports to disk
# ══════════════════════════════════════════════════════════════
all_reports = [report1, report2, report3, report4, report5]

print("\nStep 1: Saving 5 CHG reports to reports/ folder...\n")
saved_files = []
for report in all_reports:
    saved_files.append(save_report(report))

# ══════════════════════════════════════════════════════════════
#  STEP 2 — Ingest all reports into FAISS RAG
#  THIS IS THE FIX: previously test_run.py stopped after Step 1,
#  so the RAG index was always empty. Now we call EasyRAG.ingest()
#  for every report so the chatbot has historical context.
# ══════════════════════════════════════════════════════════════
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

# ══════════════════════════════════════════════════════════════
#  SUMMARY
# ══════════════════════════════════════════════════════════════
rag_status = "READY" if rag_ok else "SKIPPED (no API key)"
print(f"""
╔══════════════════════════════════════════════════════╗
║         FlowMaster test data setup complete          ║
╠══════════════════════════════════════════════════════╣
║  CHG0012345 — OS Patching          → HIGH            ║
║  CHG0012346 — Oracle DB Upgrade    → CRITICAL        ║
║  CHG0012347 — Firewall Rules       → LOW             ║
║  CHG0012348 — MQ Middleware        → MEDIUM          ║
║  CHG0012349 — Emergency CVE Patch  → CRITICAL        ║
╠══════════════════════════════════════════════════════╣
║  Reports saved  : reports/                           ║
║  RAG ingestion  : {rag_status:<34}║
╚══════════════════════════════════════════════════════╝

Next step → run: streamlit run app.py
""")
