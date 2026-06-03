# ingest_historical.py
# ─────────────────────────────────────────────────────────────────────────────
# Run once to populate your FAISS RAG index with 25 rich historical change
# records that cover every scenario FlowMaster needs for good similarity search.
#
# Usage:
#   python ingest_historical.py
#
# Requirements:
#   - GEMINI_API_KEY set in your .env (uses gemini-embedding-001)
#   - run from the project root (same folder as config.py)
#
# What it does:
#   1. Builds 25 Document objects matching EasyRAG._report_to_text() format
#   2. Calls EasyRAG.ingest() for each → embeds + saves to faiss_index/
#   3. Prints final stats
#
# These records are APPEND-ONLY — re-running does NOT delete existing vectors.
# To start fresh: delete rag/faiss_index/ then re-run.
# ─────────────────────────────────────────────────────────────────────────────

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from rag.easy_rag import EasyRAG

# ─────────────────────────────────────────────────────────────────────────────
#  HISTORICAL RECORDS
#  Each dict maps directly to the fields EasyRAG._report_to_text() reads:
#    change   → chg_number, description, category, risk, impact, state, environment
#    ci_summary → PROD, DR, NON-PROD
#    impact   → severity, estimated_downtime_minutes, rollback_complexity,
#               affected_business_services, risk_summary,
#               potential_failures, recommendations
# ─────────────────────────────────────────────────────────────────────────────

HISTORICAL_RECORDS = [

    # ── 1. CRITICAL: RSP full PROD DB outage — Oracle RAC node failure ────────
    {
        "meta": {"chg_number": "CHG0002001", "analyzed_at": "2024-06-15T03:45:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002001",
            "description": "RSP Oracle RAC node failure — emergency failover PROD",
            "category": "Database",
            "risk": "Critical",
            "impact": "1",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 3, "DR": 1, "NON-PROD": 0, "UNKNOWN": 0},
        "impact": {
            "severity": "CRITICAL",
            "estimated_downtime_minutes": 95,
            "rollback_complexity": "HIGH",
            "affected_business_services": ["RSP"],
            "risk_summary": (
                "RAC node 2 of oracle-prd-01 crashed due to storage multipath failure. "
                "RSP transactions suspended for 95 minutes while DBA executed TAF failover "
                "and brought node back online. Data integrity confirmed via SCN cross-check."
            ),
            "potential_failures": [
                "TAF failover not completing — app sessions hung",
                "Data block corruption on failed node",
                "DR replication gap if redo shipping paused > threshold",
            ],
            "recommendations": [
                "Enable TAF for all RSP connection pools — eliminates manual failover",
                "Set multipath I/O timeout to 30s — prevented auto-recovery here",
                "Add automated SCN consistency check post-recovery to runbook",
                "Alert DBA pager at first ORA-04031 — do not wait for app timeout",
            ],
        },
    },

    # ── 2. CRITICAL: UK-Axiom SSL cert expiry — all HTTPS sessions dropped ───
    {
        "meta": {"chg_number": "CHG0002002", "analyzed_at": "2024-09-01T00:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002002",
            "description": "UK-Axiom SSL certificate expired — emergency renewal PROD",
            "category": "Security",
            "risk": "Critical",
            "impact": "1",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 2, "DR": 1, "NON-PROD": 0, "UNKNOWN": 0},
        "impact": {
            "severity": "CRITICAL",
            "estimated_downtime_minutes": 45,
            "rollback_complexity": "LOW",
            "affected_business_services": ["UK-Axiom"],
            "risk_summary": (
                "UK-Axiom customer-facing portal went down when wildcard SSL cert expired "
                "at midnight. All HTTPS connections rejected. Emergency Let's Encrypt renewal "
                "deployed to web-prd-01 and web-dr-01 within 45 minutes. "
                "Root cause: cert rotation reminder email routed to wrong distribution list."
            ),
            "potential_failures": [
                "Load balancer health check fails — drops all SSL traffic",
                "DR cert not renewed in sync — failover also unavailable",
                "HSTS header prevents fallback to HTTP for browser clients",
            ],
            "recommendations": [
                "Implement auto-renewal via ACM or Certbot 30 days before expiry",
                "Add cert expiry monitoring alert at 60, 30, and 7 days",
                "Ensure DR cert renewed atomically with PROD",
                "Add cert expiry dashboard to daily ops review",
            ],
        },
    },

    # ── 3. HIGH: SRC collateral DB index rebuild — planned maintenance ────────
    {
        "meta": {"chg_number": "CHG0002003", "analyzed_at": "2024-07-20T22:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002003",
            "description": "SRC collateral DB index rebuild and stats collection — planned maintenance",
            "category": "Database",
            "risk": "High",
            "impact": "2",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 2, "DR": 1, "NON-PROD": 0, "UNKNOWN": 0},
        "impact": {
            "severity": "HIGH",
            "estimated_downtime_minutes": 0,
            "rollback_complexity": "LOW",
            "affected_business_services": ["SRC"],
            "risk_summary": (
                "Online index rebuild on SRC_COLLATERAL_DB. No application downtime — "
                "online rebuild keeps indexes accessible throughout. "
                "Risk is query slowdown during rebuild due to buffer cache pressure. "
                "Stats collection in DBMS_STATS runs post-rebuild in low-risk window."
            ),
            "potential_failures": [
                "Rebuild consuming excess I/O causing collateral calculation latency",
                "ORA-08104 if rebuild interrupted — index unusable until re-run",
                "Stats collection causing plan flips on key SRC margin queries",
            ],
            "recommendations": [
                "Run PARALLEL 4 for rebuild — halves duration, acceptable I/O",
                "Monitor v$session_longops during rebuild",
                "Gather stats with NO_INVALIDATE=FALSE only after business hours",
                "Keep old stats snapshot via DBMS_STATS.EXPORT_TABLE_STATS as rollback",
            ],
        },
    },

    # ── 4. HIGH: CAD JP Oracle DB major version upgrade 19c → 21c ────────────
    {
        "meta": {"chg_number": "CHG0002004", "analyzed_at": "2024-10-05T20:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002004",
            "description": "CAD JP Oracle DB upgrade 19c to 21c — planned major version upgrade",
            "category": "Database",
            "risk": "High",
            "impact": "2",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 2, "DR": 1, "NON-PROD": 2, "UNKNOWN": 0},
        "impact": {
            "severity": "HIGH",
            "estimated_downtime_minutes": 180,
            "rollback_complexity": "HIGH",
            "affected_business_services": ["CAD JP"],
            "risk_summary": (
                "CAD JP trading DB upgraded from Oracle 19c to 21c on New York 2PK node. "
                "3-hour maintenance window. DBUA used for upgrade. "
                "Full RMAN backup taken pre-upgrade. UAT environment validated for 2 weeks prior. "
                "Rollback path: restore RMAN backup (est. 90 min)."
            ),
            "potential_failures": [
                "DBUA fails mid-upgrade leaving DB in invalid state",
                "Timezone file version mismatch post-upgrade",
                "CAD JP application incompatibility with 21c JDBC driver",
                "Data dictionary inconsistency requiring catuppst.sql re-run",
            ],
            "recommendations": [
                "Full RMAN backup mandatory before DBUA — verify backup 30 min before window",
                "Test CAD JP app with 21c driver in UAT for minimum 2 weeks",
                "Run utlrp.sql and check dba_objects invalid count post-upgrade",
                "Keep 19c Oracle Home available for 30 days in case of app issues",
            ],
        },
    },

    # ── 5. HIGH: RCL India BKC load balancer failover — planned maintenance ──
    {
        "meta": {"chg_number": "CHG0002005", "analyzed_at": "2024-08-10T01:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002005",
            "description": "RCL India BKC load balancer failover and firmware upgrade",
            "category": "Network",
            "risk": "High",
            "impact": "2",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 3, "DR": 1, "NON-PROD": 0, "UNKNOWN": 0},
        "impact": {
            "severity": "HIGH",
            "estimated_downtime_minutes": 10,
            "rollback_complexity": "MEDIUM",
            "affected_business_services": ["RCL"],
            "risk_summary": (
                "RCL India BKC active load balancer (F5-BKC-PRD-01) failed over to standby "
                "for firmware upgrade. 10-min connection drop while VIP fails over. "
                "RCL India Payments routing disrupted for active sessions. "
                "Passive F5-BKC-PRD-02 promoted to active without issues."
            ),
            "potential_failures": [
                "VIP failover not completing — both nodes go passive",
                "Active sessions not gracefully drained before failover",
                "RCL India Payments in-flight transactions lost during 10-min window",
                "Firmware rollback required if new version has known F5 bug",
            ],
            "recommendations": [
                "Drain active connections 5 min before failover using F5 graceful shutdown",
                "Confirm standby node health (CPU, memory, sessions) before failover",
                "Notify RCL India Payments team — warn of 10-min connection disruption",
                "Validate VIP responds within 30s after failover completes",
            ],
        },
    },

    # ── 6. MEDIUM: RSP MQ middleware upgrade — planned ────────────────────────
    {
        "meta": {"chg_number": "CHG0002006", "analyzed_at": "2024-05-18T22:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002006",
            "description": "RSP IBM MQ middleware upgrade 9.2 to 9.3 — planned",
            "category": "Middleware",
            "risk": "Medium",
            "impact": "2",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 2, "DR": 1, "NON-PROD": 1, "UNKNOWN": 0},
        "impact": {
            "severity": "MEDIUM",
            "estimated_downtime_minutes": 20,
            "rollback_complexity": "MEDIUM",
            "affected_business_services": ["RSP"],
            "risk_summary": (
                "RSP IBM MQ queue manager on mq-prd-01 upgraded from 9.2 to 9.3. "
                "20-min MQ downtime — RSP trade booking queue paused during upgrade. "
                "In-flight messages drained to disk before stop. "
                "No message loss reported. RSP reconnected within 2 min post-upgrade."
            ),
            "potential_failures": [
                "MQ channel not reconnecting — RSP trade bookings stuck",
                "Message loss if drain incomplete before queue manager stop",
                "9.3 TLS cipher suite change breaking RSP connector config",
            ],
            "recommendations": [
                "Drain RSP trade booking queue to depth 0 before MQ stop",
                "Confirm RSP MQ connection factory points to correct port post-upgrade",
                "Test 9.3 cipher suites in UAT — RSP uses TLS_RSA_WITH_AES_256_CBC_SHA",
                "Keep 9.2 MQ installer available for rollback for 7 days",
            ],
        },
    },

    # ── 7. MEDIUM: UK-Axiom WAF rule update — security ────────────────────────
    {
        "meta": {"chg_number": "CHG0002007", "analyzed_at": "2024-04-22T21:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002007",
            "description": "UK-Axiom WAF rule update — block new OWASP Top 10 attack patterns",
            "category": "Security",
            "risk": "Medium",
            "impact": "3",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 2, "DR": 1, "NON-PROD": 1, "UNKNOWN": 0},
        "impact": {
            "severity": "MEDIUM",
            "estimated_downtime_minutes": 0,
            "rollback_complexity": "LOW",
            "affected_business_services": ["UK-Axiom"],
            "risk_summary": (
                "UK-Axiom WAF updated with 12 new OWASP Top 10 2021 blocking rules. "
                "No downtime — WAF rule push is zero-impact on traffic. "
                "Risk is false-positive blocking of legitimate UK-Axiom API calls "
                "if rule regex matches valid request payloads."
            ),
            "potential_failures": [
                "New SQLi rule blocking UK-Axiom search API — contains SQL-like syntax in payload",
                "XSS rule false positive on UK-Axiom rich text editor content",
                "WAF in detect-only mode missed in staging — block mode causes prod issues",
            ],
            "recommendations": [
                "Deploy in detect-only mode for 24 hours before switching to block",
                "Review WAF logs for false positives against UK-Axiom API traffic patterns",
                "Coordinate with UK-Axiom dev team to whitelist known-safe payload patterns",
                "Rollback single rule via WAF API — no full deployment needed",
            ],
        },
    },

    # ── 8. MEDIUM: SRC Germany DCN network switch replacement ─────────────────
    {
        "meta": {"chg_number": "CHG0002008", "analyzed_at": "2024-11-03T02:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002008",
            "description": "SRC Germany DCN core network switch replacement — planned hardware",
            "category": "Hardware",
            "risk": "Medium",
            "impact": "2",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 4, "DR": 2, "NON-PROD": 0, "UNKNOWN": 0},
        "impact": {
            "severity": "MEDIUM",
            "estimated_downtime_minutes": 15,
            "rollback_complexity": "HIGH",
            "affected_business_services": ["SRC"],
            "risk_summary": (
                "Core Cisco Catalyst switch in SRC Germany DCN replaced due to EOL. "
                "15-min network interruption to all DCN rack servers during cable migration. "
                "SRC Europe collateral and margin calculations offline during window. "
                "Config pre-loaded on replacement switch — cut-over was clean."
            ),
            "potential_failures": [
                "Spanning tree reconvergence longer than expected — extends outage",
                "LACP bond not re-forming on new switch — servers network isolated",
                "SRC app not reconnecting automatically after network restore",
            ],
            "recommendations": [
                "Pre-stage full switch config and validate against network diagram before window",
                "Disable STP portfast on trunk ports to prevent topology change floods",
                "Confirm all LACP bonds UP within 3 min of cable migration completing",
                "SRC app team on standby to restart connection pools if needed",
            ],
        },
    },

    # ── 9. MEDIUM: CAD JP Singapore 9TS planned DB patching ──────────────────
    {
        "meta": {"chg_number": "CHG0002009", "analyzed_at": "2024-03-16T22:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002009",
            "description": "CAD JP Singapore 9TS Oracle DB quarterly CPU patch — planned",
            "category": "Database",
            "risk": "Medium",
            "impact": "2",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 2, "DR": 1, "NON-PROD": 0, "UNKNOWN": 0},
        "impact": {
            "severity": "MEDIUM",
            "estimated_downtime_minutes": 60,
            "rollback_complexity": "MEDIUM",
            "affected_business_services": ["CAD JP"],
            "risk_summary": (
                "CAD JP Singapore Oracle DB quarterly CPU patch applied to 9TS-DB-PRD-01. "
                "60-min planned downtime. Switchover to DSJ DR executed before patch, "
                "patch applied to idle PRD node, then switchback. "
                "CAD JP APAC trading sessions offline during window."
            ),
            "potential_failures": [
                "Patch rollback required if OPatch fails mid-apply on 9TS",
                "Switchback lag — CAD JP reconnects to wrong node",
                "Oracle listener not restarting post-patch",
            ],
            "recommendations": [
                "Execute DGMGRL switchover to DSJ 30 min before patching",
                "Validate DSJ listener and service registration before starting patch",
                "Notify CAD JP APAC trading desk of 60-min window start time",
                "Test via tnsping and select 1 from dual before switchback",
            ],
        },
    },

    # ── 10. MEDIUM: RCL India BKC Oracle DB tablespace extension ─────────────
    {
        "meta": {"chg_number": "CHG0002010", "analyzed_at": "2024-02-14T21:30:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002010",
            "description": "RCL India BKC Oracle DB tablespace extension — USERS and INDX tablespaces near capacity",
            "category": "Database",
            "risk": "Medium",
            "impact": "3",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 1, "DR": 1, "NON-PROD": 0, "UNKNOWN": 0},
        "impact": {
            "severity": "MEDIUM",
            "estimated_downtime_minutes": 0,
            "rollback_complexity": "LOW",
            "affected_business_services": ["RCL"],
            "risk_summary": (
                "RCL India BKC DB USERS tablespace at 94% and INDX tablespace at 91%. "
                "Extended both by adding 50GB datafiles online — no downtime. "
                "Risk: if extension delayed, ORA-01653 (unable to extend table) "
                "would halt RCL India Payments processing."
            ),
            "potential_failures": [
                "Storage array out of space — datafile add fails",
                "ORA-01653 before change window if growth faster than expected",
            ],
            "recommendations": [
                "Add AUTOEXTEND ON as permanent fix — prevents manual intervention next quarter",
                "Set alert threshold at 80% — current 94% threshold is too late",
                "Check ASM diskgroup free space before adding datafiles",
                "Replicate extension to DR (BKC-DR-01) in same window",
            ],
        },
    },

    # ── 11. LOW: RSP SSL/TLS certificate rotation — planned ──────────────────
    {
        "meta": {"chg_number": "CHG0002011", "analyzed_at": "2024-01-20T02:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002011",
            "description": "RSP SSL/TLS certificate rotation — annual planned renewal",
            "category": "Security",
            "risk": "Low",
            "impact": "3",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 2, "DR": 1, "NON-PROD": 1, "UNKNOWN": 0},
        "impact": {
            "severity": "LOW",
            "estimated_downtime_minutes": 0,
            "rollback_complexity": "LOW",
            "affected_business_services": ["RSP"],
            "risk_summary": (
                "Annual RSP PROD and DR SSL/TLS certificate rotation on app-prd-01 and app-dr-01. "
                "Zero downtime — hot-swap via nginx reload (no restart). "
                "New 2-year SHA-256 cert from DigiCert installed and validated. "
                "Old cert kept on disk for 7 days as rollback."
            ),
            "potential_failures": [
                "nginx config reload fails — RSP SSL down until manual fix",
                "Intermediate cert chain incomplete — browser trust error",
                "DR cert not rotated in sync — failover would serve expired cert",
            ],
            "recommendations": [
                "Validate full chain via openssl s_client before going live",
                "Rotate DR cert atomically in same window as PROD",
                "Add cert SHA to monitoring dashboard — auto-alert if cert changes unexpectedly",
                "Run nginx -t before reload to catch config syntax errors",
            ],
        },
    },

    # ── 12. LOW: UK-Axiom DR backup restore validation ────────────────────────
    {
        "meta": {"chg_number": "CHG0002012", "analyzed_at": "2024-12-07T23:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002012",
            "description": "UK-Axiom DR backup restore validation — quarterly DR drill",
            "category": "DR",
            "risk": "Low",
            "impact": "3",
            "state": "Closed",
            "environment": "DR",
        },
        "ci_summary": {"PROD": 0, "DR": 3, "NON-PROD": 0, "UNKNOWN": 0},
        "impact": {
            "severity": "LOW",
            "estimated_downtime_minutes": 0,
            "rollback_complexity": "LOW",
            "affected_business_services": ["UK-Axiom"],
            "risk_summary": (
                "Quarterly DR backup restore drill for UK-Axiom on WDC DR nodes. "
                "RMAN backup from CDC PROD restored to isolated DR test instance. "
                "Zero PROD impact — DR test environment is air-gapped from production network. "
                "RTO measured at 47 minutes against 60-minute SLA — PASS."
            ),
            "potential_failures": [
                "RMAN restore slower than expected — misses 60-min RTO SLA",
                "DR test instance not air-gapped — test writes replicate to PROD",
                "Backup corrupt — RMAN validate block check fails",
            ],
            "recommendations": [
                "Run RMAN validate database before restore to catch backup corruption early",
                "Document RTO result and compare trend across quarters",
                "Confirm DR test network VLAN is isolated before starting restore",
                "Extend DR test to include application connectivity check post-restore",
            ],
        },
    },

    # ── 13. LOW: SRC UAT environment K8s namespace cleanup ────────────────────
    {
        "meta": {"chg_number": "CHG0002013", "analyzed_at": "2024-11-15T10:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002013",
            "description": "SRC UAT K8s namespace cleanup — decommission stale test environments",
            "category": "Software",
            "risk": "Low",
            "impact": "3",
            "state": "Closed",
            "environment": "Non-Production",
        },
        "ci_summary": {"PROD": 0, "DR": 0, "NON-PROD": 4, "UNKNOWN": 0},
        "impact": {
            "severity": "LOW",
            "estimated_downtime_minutes": 0,
            "rollback_complexity": "LOW",
            "affected_business_services": ["SRC"],
            "risk_summary": (
                "12 stale SRC UAT K8s namespaces decommissioned on k8s-qa-cluster-01. "
                "Namespaces unused for > 90 days. Zero PROD or DR impact. "
                "PVCs deleted after confirming no active data. "
                "Freed 480GB storage and 24 vCPUs on QA cluster."
            ),
            "potential_failures": [
                "Active SRC test run using a namespace marked stale — work lost",
                "PVC deleted that contained a UAT dataset needed for regression",
            ],
            "recommendations": [
                "Confirm with SRC QA team all listed namespaces are unused before delete",
                "Tag PVCs with last-active date — automate staleness detection",
                "Run kubectl describe ns before delete — check last pod start time",
            ],
        },
    },

    # ── 14. LOW: CAD JP New York 2PK storage array firmware update ───────────
    {
        "meta": {"chg_number": "CHG0002014", "analyzed_at": "2024-08-24T01:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002014",
            "description": "CAD JP New York 2PK storage array firmware update — planned",
            "category": "Hardware",
            "risk": "Low",
            "impact": "3",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 2, "DR": 1, "NON-PROD": 0, "UNKNOWN": 0},
        "impact": {
            "severity": "LOW",
            "estimated_downtime_minutes": 0,
            "rollback_complexity": "LOW",
            "affected_business_services": ["CAD JP"],
            "risk_summary": (
                "CAD JP New York 2PK HPE storage array firmware updated from 9.00.03 to 9.00.06. "
                "Non-disruptive upgrade — both controllers updated in rolling fashion. "
                "No DB or application downtime. I/O handled by alternate controller during each controller update."
            ),
            "potential_failures": [
                "Controller failover not completing cleanly — brief I/O pause",
                "Firmware rollback if new version has known issue with ExaCC compatibility",
            ],
            "recommendations": [
                "Verify both controllers are healthy (green) before starting firmware update",
                "Monitor I/O latency during controller failover — threshold alert at 50ms",
                "Confirm HPE advisory for firmware 9.00.06 covers ExaCC X9M compatibility",
            ],
        },
    },

    # ── 15. LOW: RSP PROD Linux OS kernel patch rolling update ────────────────
    {
        "meta": {"chg_number": "CHG0002015", "analyzed_at": "2024-06-01T01:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002015",
            "description": "RSP PROD Linux OS kernel patch — rolling reboot all app servers",
            "category": "Software",
            "risk": "Low",
            "impact": "3",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 4, "DR": 2, "NON-PROD": 2, "UNKNOWN": 0},
        "impact": {
            "severity": "LOW",
            "estimated_downtime_minutes": 0,
            "rollback_complexity": "LOW",
            "affected_business_services": ["RSP"],
            "risk_summary": (
                "CVE-2024-1086 kernel patch applied to all RSP PROD app servers via rolling reboot. "
                "Load balancer drains each node before reboot — zero user impact. "
                "4 app servers patched and back in rotation in 2.5 hours. "
                "DR servers patched in separate window following day."
            ),
            "potential_failures": [
                "App server not re-registering with load balancer post-reboot",
                "RSP startup script hanging — node stays out of rotation",
                "Kernel module incompatibility with RSP JVM version",
            ],
            "recommendations": [
                "Patch one node, validate load balancer health check passes before proceeding",
                "Set load balancer removal timeout to 120s — RSP needs 90s to drain sessions",
                "Confirm RSP JVM startup within 60s post-reboot — add startup health endpoint",
            ],
        },
    },

    # ── 16. HIGH: UK-Axiom PROD database connection pool exhaustion — incident
    {
        "meta": {"chg_number": "CHG0002016", "analyzed_at": "2024-10-28T09:15:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002016",
            "description": "UK-Axiom PROD DB connection pool exhaustion — emergency config change",
            "category": "Software",
            "risk": "High",
            "impact": "1",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 2, "DR": 1, "NON-PROD": 0, "UNKNOWN": 0},
        "impact": {
            "severity": "HIGH",
            "estimated_downtime_minutes": 35,
            "rollback_complexity": "LOW",
            "affected_business_services": ["UK-Axiom"],
            "risk_summary": (
                "UK-Axiom PROD hit ORA-12519 (TNS: no appropriate handler found) during peak usage. "
                "Max DB connections (300) exhausted by session leak from v2.4.0 deployment the day prior. "
                "Emergency fix: increase max_processes to 500 in Oracle DB init parameters, "
                "restart connection pool on app-prd-01 and app-prd-02."
            ),
            "potential_failures": [
                "DB restart required if SGA must be resized to accommodate 500 connections",
                "Session leak root cause not fixed — pool exhaustion recurs",
                "Connection pool restart drops all active UK-Axiom sessions",
            ],
            "recommendations": [
                "Root cause: v2.4.0 missing connection.close() in error path — raise defect immediately",
                "Set ORA_POOL_MIN=10, ORA_POOL_MAX=100 per app server — prevents unbounded growth",
                "Add DBA alert at 80% connection utilisation — catch before exhaustion",
                "Test connection pool behaviour under load in UAT before each release",
            ],
        },
    },

    # ── 17. MEDIUM: RSP PROD API gateway config update — rate limiting ────────
    {
        "meta": {"chg_number": "CHG0002017", "analyzed_at": "2024-09-14T20:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002017",
            "description": "RSP PROD API gateway rate limiting config update",
            "category": "Network",
            "risk": "Medium",
            "impact": "3",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 2, "DR": 1, "NON-PROD": 1, "UNKNOWN": 0},
        "impact": {
            "severity": "MEDIUM",
            "estimated_downtime_minutes": 0,
            "rollback_complexity": "LOW",
            "affected_business_services": ["RSP"],
            "risk_summary": (
                "RSP Kong API gateway rate limit on /trade/booking endpoint increased from "
                "500 to 1200 req/min to accommodate new algorithmic trading client. "
                "Zero downtime — Kong admin API update is hot-reload. "
                "Risk: other tenants on shared gateway may see latency if RSP saturates gateway."
            ),
            "potential_failures": [
                "RSP algo trading client bursts past 1200 req/min — gateway CPU spike",
                "Other tenants sharing gateway experience 429 errors unintentionally",
                "Config drift if DR gateway not updated in same window",
            ],
            "recommendations": [
                "Apply same rate limit change to DR Kong gateway (app-dr-01) atomically",
                "Monitor gateway CPU and p99 latency for 30 min after change",
                "Set burst limit to 1500 req/min with 1200 sustained to absorb peaks",
                "Isolate RSP algo trading to dedicated gateway upstream if load increases further",
            ],
        },
    },

    # ── 18. LOW: SRC PROD log rotation and archival — housekeeping ───────────
    {
        "meta": {"chg_number": "CHG0002018", "analyzed_at": "2024-07-06T23:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002018",
            "description": "SRC PROD application log rotation and archival to cold storage",
            "category": "Maintenance",
            "risk": "Low",
            "impact": "3",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 2, "DR": 0, "NON-PROD": 0, "UNKNOWN": 0},
        "impact": {
            "severity": "LOW",
            "estimated_downtime_minutes": 0,
            "rollback_complexity": "LOW",
            "affected_business_services": ["SRC"],
            "risk_summary": (
                "SRC PROD /var/log/src-app on both PROD servers at 89% disk. "
                "Logs older than 90 days compressed and moved to cold storage S3. "
                "Active log handles not interrupted — logrotate copytruncate used. "
                "Freed 340GB. No application impact."
            ),
            "potential_failures": [
                "Active log file rotated mid-write — SRC app loses log handle",
                "S3 transfer incomplete — disk still full after rotation",
                "Archived logs needed for ongoing regulatory audit — must not be deleted",
            ],
            "recommendations": [
                "Use copytruncate option in logrotate — prevents app losing file handle",
                "Confirm S3 transfer complete before removing local compressed files",
                "Check with compliance: SRC log retention policy is 7 years — archive, do not delete",
                "Set disk alert at 75% — 89% is too late for non-urgent scheduling",
            ],
        },
    },

    # ── 19. MEDIUM: UK-Axiom new microservice PROD deployment ────────────────
    {
        "meta": {"chg_number": "CHG0002019", "analyzed_at": "2024-05-04T21:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002019",
            "description": "UK-Axiom new notification microservice PROD deployment v1.0.0",
            "category": "Software",
            "risk": "Medium",
            "impact": "3",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 3, "DR": 1, "NON-PROD": 2, "UNKNOWN": 0},
        "impact": {
            "severity": "MEDIUM",
            "estimated_downtime_minutes": 0,
            "rollback_complexity": "MEDIUM",
            "affected_business_services": ["UK-Axiom"],
            "risk_summary": (
                "New UK-Axiom notification microservice (email + SMS alerts for trade execution) "
                "deployed to PROD Kubernetes cluster. New service, not a replacement — "
                "no downtime risk. Risk is in integration: connects to existing UK-Axiom "
                "trade event Kafka topic and external SMTP relay."
            ),
            "potential_failures": [
                "Kafka consumer group offset conflict — duplicate notifications sent to customers",
                "SMTP relay IP not whitelisted — notification emails silently dropped",
                "K8s resource limit too low — OOMKill under notification burst",
            ],
            "recommendations": [
                "Set Kafka consumer group to 'notification-svc-prod' — unique, not shared",
                "Whitelist notification-svc PROD egress IPs in SMTP relay firewall rule",
                "Set memory limit 512Mi request 256Mi — based on UAT profiling",
                "Monitor DLQ (dead letter queue) depth for first 24 hours post-deploy",
            ],
        },
    },

    # ── 20. HIGH: CAD JP PROD emergency rollback after bad release ────────────
    {
        "meta": {"chg_number": "CHG0002020", "analyzed_at": "2024-04-09T14:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002020",
            "description": "CAD JP PROD emergency rollback — v3.2.1 position calc regression",
            "category": "Software",
            "risk": "High",
            "impact": "1",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 2, "DR": 1, "NON-PROD": 2, "UNKNOWN": 0},
        "impact": {
            "severity": "HIGH",
            "estimated_downtime_minutes": 20,
            "rollback_complexity": "LOW",
            "affected_business_services": ["CAD JP"],
            "risk_summary": (
                "CAD JP v3.2.1 deployed at 09:00 introduced a rounding error in JPY position "
                "calculations discovered by traders at 14:00. Emergency rollback to v3.2.0 "
                "executed in 20 minutes. Kubernetes rolling deployment made rollback clean. "
                "All JPY positions recalculated from source after rollback."
            ),
            "potential_failures": [
                "DB schema migration from v3.2.1 not reversible — rollback fails",
                "Active CAD JP trading sessions lost during pod restart",
                "Incorrect positions reported to risk system between 09:00 and 14:00",
            ],
            "recommendations": [
                "Mandate DB migration reversibility review in deployment checklist",
                "Add automated position calculation regression test to CI pipeline",
                "Trading desk must be in deployment approval chain for any release touching calc engine",
                "Post-mortem: 5-hour gap between deploy and discovery — add real-time calc diff alert",
            ],
        },
    },

    # ── 21. MEDIUM: RCL India BKC Oracle RMAN backup performance tuning ───────
    {
        "meta": {"chg_number": "CHG0002021", "analyzed_at": "2024-03-02T23:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002021",
            "description": "RCL India BKC Oracle RMAN backup performance tuning — parallelism increase",
            "category": "Database",
            "risk": "Medium",
            "impact": "3",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 1, "DR": 1, "NON-PROD": 0, "UNKNOWN": 0},
        "impact": {
            "severity": "MEDIUM",
            "estimated_downtime_minutes": 0,
            "rollback_complexity": "LOW",
            "affected_business_services": ["RCL"],
            "risk_summary": (
                "RCL India BKC RMAN full backup exceeding 8-hour window, breaching SLA. "
                "PARALLELISM increased from 2 to 6 channels. Backup duration reduced to 4.5 hours. "
                "Risk: increased I/O load during backup window competing with batch processing."
            ),
            "potential_failures": [
                "RCL India batch jobs slowing due to I/O contention during backup",
                "RMAN failing with ORA-27037 if additional channels exceed ASM I/O limit",
            ],
            "recommendations": [
                "Schedule RMAN backup to start after RCL India batch completes (post 23:30)",
                "Monitor ASM I/O throughput — cap channels at 4 if latency > 20ms",
                "Test parallelism change in UAT with production-equivalent data volume",
            ],
        },
    },

    # ── 22. LOW: RSP PROD DNS record update — new DR endpoint ────────────────
    {
        "meta": {"chg_number": "CHG0002022", "analyzed_at": "2024-02-18T20:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002022",
            "description": "RSP PROD DNS record update — add DR endpoint for automatic failover",
            "category": "Network",
            "risk": "Low",
            "impact": "3",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 1, "DR": 1, "NON-PROD": 1, "UNKNOWN": 0},
        "impact": {
            "severity": "LOW",
            "estimated_downtime_minutes": 0,
            "rollback_complexity": "LOW",
            "affected_business_services": ["RSP"],
            "risk_summary": (
                "New DNS CNAME rsp-dr.internal → app-dr-01.internal added to enable "
                "automatic RSP DR failover without manual DNS change. "
                "TTL set to 60s to allow fast cutover. Zero impact on existing PROD DNS records. "
                "Tested in UAT before PROD push."
            ),
            "potential_failures": [
                "TTL too low — DNS cache refresh storms during normal operation",
                "CNAME pointing to wrong DR endpoint — failover routes to wrong server",
            ],
            "recommendations": [
                "Validate new CNAME resolves correctly from all internal DNS zones before completing",
                "Document DR DNS failover procedure — who triggers and how",
                "Test failover DNS switch in next quarterly DR drill",
            ],
        },
    },

    # ── 23. HIGH: UK-Axiom + RSP shared Redis cache cluster upgrade ───────────
    {
        "meta": {"chg_number": "CHG0002023", "analyzed_at": "2024-12-14T01:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002023",
            "description": "Shared Redis cache cluster upgrade 6.2 to 7.2 — RSP and UK-Axiom",
            "category": "Software",
            "risk": "High",
            "impact": "2",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 3, "DR": 2, "NON-PROD": 2, "UNKNOWN": 0},
        "impact": {
            "severity": "HIGH",
            "estimated_downtime_minutes": 30,
            "rollback_complexity": "MEDIUM",
            "affected_business_services": ["RSP", "UK-Axiom"],
            "risk_summary": (
                "Shared Redis 6.2 cluster serving RSP session cache and UK-Axiom token store "
                "upgraded to 7.2. 30-min cache flush during upgrade — RSP sessions expire, "
                "UK-Axiom users re-authenticate. Applications handle cache miss gracefully "
                "by falling back to DB. Peak hour avoided."
            ),
            "potential_failures": [
                "RSP not handling Redis READONLY error during slot migration gracefully",
                "UK-Axiom JWT token store flush forces mass re-auth — login spike hits auth DB",
                "Redis 7.2 breaking change in ACL config — apps lose connection post-upgrade",
            ],
            "recommendations": [
                "Validate RSP and UK-Axiom handle Redis connection errors without user impact",
                "Upgrade Redis client libraries to 7.x compatible version in UAT first",
                "Pre-warm cache with top 1000 RSP session keys post-upgrade to reduce DB fallback",
                "Monitor auth DB connection count for 15 min post-upgrade — UK-Axiom re-auth spike",
            ],
        },
    },

    # ── 24. MEDIUM: SRC PROD new regulatory reporting DB view deployment ──────
    {
        "meta": {"chg_number": "CHG0002024", "analyzed_at": "2024-11-23T21:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002024",
            "description": "SRC PROD new EMIR regulatory reporting DB view deployment",
            "category": "Database",
            "risk": "Medium",
            "impact": "3",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 1, "DR": 1, "NON-PROD": 1, "UNKNOWN": 0},
        "impact": {
            "severity": "MEDIUM",
            "estimated_downtime_minutes": 0,
            "rollback_complexity": "LOW",
            "affected_business_services": ["SRC"],
            "risk_summary": (
                "New DB views V_EMIR_TRADE_REPORT and V_EMIR_COUNTERPARTY_DETAIL created "
                "in SRC PROD schema for EMIR Refit compliance reporting. "
                "DDL only — no DML changes, no downtime. "
                "Views join 6 existing tables. Execution plan validated in UAT."
            ),
            "potential_failures": [
                "View query plan uses full table scan on SRC_TRADE (500M rows) — regulator report times out",
                "Missing grant to SRC_REPORT_USER role — reporting user cannot select from view",
                "View references a column renamed in a recent schema migration — invalid view",
            ],
            "recommendations": [
                "Validate execution plan in PROD during off-peak before regulators run reports",
                "Grant SELECT on both views to SRC_REPORT_USER and SRC_READONLY roles explicitly",
                "Add view to schema validation script — fails CI if referenced columns change",
            ],
        },
    },

    # ── 25. HIGH: All-apps PROD Cisco BGP routing update — DC interconnect ────
    {
        "meta": {"chg_number": "CHG0002025", "analyzed_at": "2024-10-19T03:00:00", "source": "historical"},
        "change": {
            "chg_number": "CHG0002025",
            "description": "Global DC BGP routing update — inter-DC MPLS path optimisation all regions",
            "category": "Network",
            "risk": "High",
            "impact": "1",
            "state": "Closed",
            "environment": "Production",
        },
        "ci_summary": {"PROD": 10, "DR": 5, "NON-PROD": 0, "UNKNOWN": 0},
        "impact": {
            "severity": "HIGH",
            "estimated_downtime_minutes": 5,
            "rollback_complexity": "MEDIUM",
            "affected_business_services": ["RSP", "UK-Axiom", "SRC", "CAD JP", "RCL"],
            "risk_summary": (
                "BGP route updates on 4 Cisco ASR 9000 routers across UK, DE, SG, NY DCs "
                "to optimise inter-DC MPLS paths. 5-min BGP reconvergence expected per router. "
                "All 5 apps (RSP, UK-Axiom, SRC, CAD JP, RCL) share these inter-DC paths "
                "for DR replication and cross-region API calls."
            ),
            "potential_failures": [
                "BGP reconvergence longer than 5 min — inter-DC replication lag for all apps",
                "Misconfigured AS path — traffic black-holed for one region",
                "Oracle DG redo shipping interrupted — DR replication gap for RSP and UK-Axiom",
            ],
            "recommendations": [
                "Update one router at a time — validate BGP adjacencies before moving to next",
                "Monitor Oracle DG apply lag (target < 60s) throughout routing update",
                "Use BFD (Bidirectional Forwarding Detection) to accelerate failure detection",
                "Network team and DBA team on bridge call — DBA validates DG sync after each router",
            ],
        },
    },

]


# ─────────────────────────────────────────────────────────────────────────────
#  INGEST
# ─────────────────────────────────────────────────────────────────────────────

def run():
    print()
    print("=" * 65)
    print("  FlowMaster — Historical data ingestion into FAISS RAG")
    print("=" * 65)
    print(f"\n  Records to ingest : {len(HISTORICAL_RECORDS)}")
    print(f"  Embedding model   : gemini-embedding-001")
    print(f"  FAISS index path  : rag/faiss_index/")
    print()
    print("  NOTE: This APPENDS to the existing index.")
    print("  To start fresh: delete rag/faiss_index/ then re-run.\n")

    rag = EasyRAG()
    ok  = 0
    failed = []

    for record in HISTORICAL_RECORDS:
        chg = record["meta"]["chg_number"]
        sev = record["impact"]["severity"]
        cat = record["change"]["category"]
        print(f"  Ingesting {chg}  [{cat}]  severity={sev} ...", end=" ", flush=True)
        try:
            rag.ingest(record)
            print("✓")
            ok += 1
        except Exception as e:
            print(f"✗  ({type(e).__name__}: {str(e)[:60]})")
            failed.append((chg, str(e)))

    stats = rag.get_stats()

    print()
    print("=" * 65)
    print(f"  Ingested : {ok} / {len(HISTORICAL_RECORDS)} records")
    print(f"  Failed   : {len(failed)}")
    if failed:
        for chg, err in failed:
            print(f"    {chg}: {err[:70]}")
    print(f"  Total vectors in FAISS index: {stats.get('indexed_changes', '?')}")
    print()
    print("  Coverage summary:")

    categories = {}
    severities = {}
    apps       = {}
    for r in HISTORICAL_RECORDS:
        c = r["change"]["category"]
        s = r["impact"]["severity"]
        categories[c] = categories.get(c, 0) + 1
        severities[s] = severities.get(s, 0) + 1
        for app in r["impact"]["affected_business_services"]:
            apps[app] = apps.get(app, 0) + 1

    print(f"  By category : {dict(sorted(categories.items()))}")
    print(f"  By severity : {dict(sorted(severities.items()))}")
    print(f"  By app      : {dict(sorted(apps.items()))}")
    print()
    print("  Done. Start the app: streamlit run app.py")
    print("  Try: CHG0001001 → ask 'show similar past changes'")
    print("=" * 65)
    print()


if __name__ == "__main__":
    run()