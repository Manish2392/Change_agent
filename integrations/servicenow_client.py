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
#  Based on real HCLTech/Deutsche Bank ExaCC ServiceNow patterns.
#  CHG0003774804 mirrors the actual change record (ExaCC DB
#  switchover PRD→DR across 5 global data centres).
#  All field names match real SNOW REST API response shapes.
# ══════════════════════════════════════════════════════════════

class MockServiceNowData:
    """
    In-memory store of realistic mock ServiceNow data.
    Structured to mirror real SNOW API response shapes exactly.
    """

    # ── Mock Change Requests ───────────────────────────────────
    CHANGES = {

        # ── ORIGINAL 5 CHANGES (kept for backward compatibility) ──

        "CHG0001001": {
            "sys_id":            "chg_sys_001",
            "number":            "CHG0001001",
            "short_description": "Oracle DB patch - quarterly security update",
            "description":       "Apply Oracle CPU patch Q1-2025 to all production databases. "
                                 "Patch addresses 3 CVEs (CVSS 7.8, 6.5, 5.2). "
                                 "Coordinated downtime window: 02:00-04:00 IST Saturday.",
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

        # ── NEW ExaCC / REAL-WORLD CHANGES ─────────────────────────────────────
        # Based on the actual CHG0003774804 record (ExaCC DB switchover PRD→DR).
        # Multi-region: UK, Germany, Singapore, New York, India.

        "CHG0003774804": {
            "sys_id":            "chg_sys_exacc_001",
            "number":            "CHG0003774804",
            "short_description": "Switchover of databases from one data centre to another as part of standard ExaCC maintenance",
            "description":       "Switchover of ExaCC databases currently running as PRD/Primary in one set of data centres to another. "
                                 "The source and target data centres are stated below.\n"
                                 "From data centre -> To data centre\n"
                                 "Switchover PRD -> DR\n"
                                 "UK:        CDC -> WDC\n"
                                 "Germany:   DCN -> DCB\n"
                                 "Singapore: 9TS -> DSJ\n"
                                 "New York:  2PK -> CORP\n"
                                 "IN:        BKC -> Tata\n\n"
                                 "In case the DB is already running in the target data centre, then no switchover will be performed.\n\n"
                                 "**PCM_AP**\n"
                                 "Switchover Src -> Tgt\n"
                                 "UK: CDC -> WDC | Germany: DCN -> DCB | Singapore: 9TS -> DSJ | "
                                 "New York: 2PK -> CORP | IN: BKC -> Tata",
            "change_reason":     "The databases are being switched from one regional data center to the other, "
                                 "to enable OS, GI and Infrastructure patching of the ExaCC servers on a subsequent weekend "
                                 "in the data center that no longer has the active databases so as to reduce the impact of "
                                 "the patching to zero for the applications. If this switchover is not done, then the applications "
                                 "will undergo more impact as the patching takes longer than the switchover. "
                                 "The switchover takes a maximum of 30 min.",
            "start_date":        "2025-04-05 22:00:00",
            "end_date":          "2025-04-05 23:30:00",
            "state":             "Scheduled",
            "risk":              "Low",
            "impact":            "2",
            "category":          "Database",
            "u_environment":     "Production",
            "u_contact_list":    "Sanchit Saumay",
            "u_contact_instructions": "Sumit-x-A Garg, Seema Kumari, Tara Greenbaum, Exacc_patching_group@list.db.com, "
                                      "global.database@db.com, oracloud-team-ops@list.db.com",
            "u_risk_description":     "The risk of performing a database failover is generally considered as low as this is a "
                                      "relatively simple task using proven commands/scripts. In the event of any issues during "
                                      "the fallback, the DBA will be notified and take the appropriate corrective actions.",
            "u_user_service_impact":  "The switchover requires database downtime of a max. of 30 min. Therefore, applications "
                                      "will sustain a loss of service during the switchover of a max. of 30 min.",
            "cmdb_ci":           {"value": "ci_exacc_uk_cdc_prd_01", "display_value": "exacc-uk-cdc-prd-01"},
        },

        "CHG0003774900": {
            "sys_id":            "chg_sys_exacc_002",
            "number":            "CHG0003774900",
            "short_description": "ExaCC infrastructure patching - UK CDC and Germany DCN post-switchover",
            "description":       "OS, GI and Infrastructure patching of ExaCC servers in UK CDC and Germany DCN data centres "
                                 "following PRD->DR switchover (CHG0003774804). Databases already moved to WDC/DCB. "
                                 "Patching window: UK CDC nodes 1-4, Germany DCN nodes 1-6. "
                                 "Zero application impact expected as databases are already in DR data centres.",
            "start_date":        "2025-04-12 22:00:00",
            "end_date":          "2025-04-13 04:00:00",
            "state":             "Scheduled",
            "risk":              "Medium",
            "impact":            "2",
            "category":          "Patching",
            "u_environment":     "Production",
            "u_contact_list":    "Sanchit Saumay",
            "u_contact_instructions": "Exacc_patching_group@list.db.com, oracloud-team-ops@list.db.com",
            "cmdb_ci":           {"value": "ci_exacc_uk_cdc_prd_01", "display_value": "exacc-uk-cdc-prd-01"},
        },

        "CHG0003775100": {
            "sys_id":            "chg_sys_exacc_003",
            "number":            "CHG0003775100",
            "short_description": "ExaCC database switchback DR->PRD after infrastructure patching completion",
            "description":       "Switchback of ExaCC databases from DR back to PRD data centres after infrastructure patching is complete. "
                                 "Reverse of CHG0003774804. All data centres restored to original PRD configuration.\n"
                                 "Switchback DR -> PRD\n"
                                 "UK:        WDC -> CDC\n"
                                 "Germany:   DCB -> DCN\n"
                                 "Singapore: DSJ -> 9TS\n"
                                 "New York:  CORP -> 2PK\n"
                                 "IN:        Tata -> BKC\n"
                                 "Switchback takes a maximum of 30 min per region.",
            "start_date":        "2025-04-19 22:00:00",
            "end_date":          "2025-04-19 23:30:00",
            "state":             "Scheduled",
            "risk":              "Low",
            "impact":            "2",
            "category":          "Database",
            "u_environment":     "Production",
            "u_contact_list":    "Sanchit Saumay",
            "u_contact_instructions": "Exacc_patching_group@list.db.com, oracloud-team-ops@list.db.com",
            "cmdb_ci":           {"value": "ci_exacc_uk_wdc_dr_01", "display_value": "exacc-uk-wdc-dr-01"},
        },

        "CHG0003776200": {
            "sys_id":            "chg_sys_exacc_004",
            "number":            "CHG0003776200",
            "short_description": "ExaCC Singapore 9TS emergency DB failover - node failure",
            "description":       "Unplanned failover of ExaCC Singapore cluster from 9TS to DSJ due to storage controller failure "
                                 "on 9TS-NODE-03. Databases: SG_CORE_DB_01, SG_TRADE_DB_01, SG_RISK_DB_01 impacted. "
                                 "DBA team executing manual switchover using proven DGMGRL commands. "
                                 "Expected application downtime 15-30 min. "
                                 "Root cause: Storage controller firmware bug in ExaCC X9M rack.",
            "start_date":        "2025-05-03 14:30:00",
            "end_date":          "2025-05-03 15:30:00",
            "state":             "In Progress",
            "risk":              "High",
            "impact":            "1",
            "category":          "Database",
            "u_environment":     "Production",
            "u_contact_list":    "Sanchit Saumay",
            "u_contact_instructions": "global.database@db.com, oracloud-team-ops@list.db.com",
            "cmdb_ci":           {"value": "ci_exacc_sg_9ts_prd_01", "display_value": "exacc-sg-9ts-prd-01"},
        },

        "CHG0003778500": {
            "sys_id":            "chg_sys_exacc_005",
            "number":            "CHG0003778500",
            "short_description": "ExaCC full-stack quarterly maintenance - all 5 regions coordinated",
            "description":       "Coordinated quarterly ExaCC maintenance across all 5 global regions. "
                                 "Includes: OS patching, GI (Grid Infrastructure) upgrade 19.22->19.23, "
                                 "ExaCC firmware update, storage rebalancing.\n"
                                 "Sequence (rolling, one region at a time):\n"
                                 "Week 1: IN BKC -> switch to Tata, patch BKC\n"
                                 "Week 2: Singapore 9TS -> switch to DSJ, patch 9TS\n"
                                 "Week 3: Germany DCN -> switch to DCB, patch DCN\n"
                                 "Week 4: UK CDC -> switch to WDC, patch CDC\n"
                                 "Week 5: New York 2PK -> switch to CORP, patch 2PK\n"
                                 "Week 6: All switchbacks.\n"
                                 "Total maintenance window per region: 6 hours. Max DB downtime per region: 30 min.",
            "start_date":        "2025-06-01 00:00:00",
            "end_date":          "2025-07-12 06:00:00",
            "state":             "Scheduled",
            "risk":              "Medium",
            "impact":            "2",
            "category":          "Maintenance",
            "u_environment":     "Production",
            "u_contact_list":    "Sanchit Saumay",
            "u_contact_instructions": "Exacc_patching_group@list.db.com, global.database@db.com, oracloud-team-ops@list.db.com",
            "cmdb_ci":           {"value": "ci_exacc_in_bkc_prd_01", "display_value": "exacc-in-bkc-prd-01"},
        },
    }

    # ── Mock CMDB CIs ──────────────────────────────────────────
    CIS = {
        # ── Original CIs (kept for backward compatibility) ────────
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
        "ci_sys_k8s_qa_01": {
            "sys_id": "ci_sys_k8s_qa_01", "name": "k8s-qa-cluster-01",
            "sys_class_name": "cmdb_ci_kubernetes_cluster", "environment": "Non-Production",
            "operational_status": "1", "u_tier": "Tier-3", "u_business_service": "Dev/QA Platform",
        },

        # ── ExaCC Production CIs — UK Region ─────────────────────
        "ci_exacc_uk_cdc_prd_01": {
            "sys_id": "ci_exacc_uk_cdc_prd_01", "name": "exacc-uk-cdc-prd-01",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "Global Trading Platform",
            "u_datacenter": "CDC", "u_region": "UK", "u_rack": "ExaCC-X9M-CDC-01",
        },
        "ci_exacc_uk_cdc_prd_02": {
            "sys_id": "ci_exacc_uk_cdc_prd_02", "name": "exacc-uk-cdc-prd-02",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "Risk Management",
            "u_datacenter": "CDC", "u_region": "UK", "u_rack": "ExaCC-X9M-CDC-01",
        },
        "ci_exacc_uk_cdc_prd_03": {
            "sys_id": "ci_exacc_uk_cdc_prd_03", "name": "exacc-uk-cdc-prd-03",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "Regulatory Reporting",
            "u_datacenter": "CDC", "u_region": "UK", "u_rack": "ExaCC-X9M-CDC-02",
        },
        # ExaCC DR CIs — UK Region (target after switchover)
        "ci_exacc_uk_wdc_dr_01": {
            "sys_id": "ci_exacc_uk_wdc_dr_01", "name": "exacc-uk-wdc-dr-01",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "DR",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "Global Trading Platform",
            "u_datacenter": "WDC", "u_region": "UK", "u_rack": "ExaCC-X9M-WDC-01",
        },
        "ci_exacc_uk_wdc_dr_02": {
            "sys_id": "ci_exacc_uk_wdc_dr_02", "name": "exacc-uk-wdc-dr-02",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "DR",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "Risk Management",
            "u_datacenter": "WDC", "u_region": "UK", "u_rack": "ExaCC-X9M-WDC-01",
        },

        # ── ExaCC Production CIs — Germany Region ─────────────────
        "ci_exacc_de_dcn_prd_01": {
            "sys_id": "ci_exacc_de_dcn_prd_01", "name": "exacc-de-dcn-prd-01",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "Global Trading Platform",
            "u_datacenter": "DCN", "u_region": "Germany", "u_rack": "ExaCC-X9M-DCN-01",
        },
        "ci_exacc_de_dcn_prd_02": {
            "sys_id": "ci_exacc_de_dcn_prd_02", "name": "exacc-de-dcn-prd-02",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "Core Banking Europe",
            "u_datacenter": "DCN", "u_region": "Germany", "u_rack": "ExaCC-X9M-DCN-02",
        },
        # ExaCC DR CIs — Germany
        "ci_exacc_de_dcb_dr_01": {
            "sys_id": "ci_exacc_de_dcb_dr_01", "name": "exacc-de-dcb-dr-01",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "DR",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "Global Trading Platform",
            "u_datacenter": "DCB", "u_region": "Germany", "u_rack": "ExaCC-X9M-DCB-01",
        },

        # ── ExaCC Production CIs — Singapore Region ───────────────
        "ci_exacc_sg_9ts_prd_01": {
            "sys_id": "ci_exacc_sg_9ts_prd_01", "name": "exacc-sg-9ts-prd-01",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "APAC Trading Platform",
            "u_datacenter": "9TS", "u_region": "Singapore", "u_rack": "ExaCC-X9M-9TS-01",
        },
        "ci_exacc_sg_9ts_prd_02": {
            "sys_id": "ci_exacc_sg_9ts_prd_02", "name": "exacc-sg-9ts-prd-02",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "APAC Risk Management",
            "u_datacenter": "9TS", "u_region": "Singapore", "u_rack": "ExaCC-X9M-9TS-01",
        },
        # ExaCC DR CIs — Singapore
        "ci_exacc_sg_dsj_dr_01": {
            "sys_id": "ci_exacc_sg_dsj_dr_01", "name": "exacc-sg-dsj-dr-01",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "DR",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "APAC Trading Platform",
            "u_datacenter": "DSJ", "u_region": "Singapore", "u_rack": "ExaCC-X9M-DSJ-01",
        },

        # ── ExaCC Production CIs — New York Region ────────────────
        "ci_exacc_ny_2pk_prd_01": {
            "sys_id": "ci_exacc_ny_2pk_prd_01", "name": "exacc-ny-2pk-prd-01",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "Americas Trading Platform",
            "u_datacenter": "2PK", "u_region": "New York", "u_rack": "ExaCC-X9M-2PK-01",
        },
        "ci_exacc_ny_2pk_prd_02": {
            "sys_id": "ci_exacc_ny_2pk_prd_02", "name": "exacc-ny-2pk-prd-02",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "Americas Risk Management",
            "u_datacenter": "2PK", "u_region": "New York", "u_rack": "ExaCC-X9M-2PK-02",
        },
        # ExaCC DR CIs — New York
        "ci_exacc_ny_corp_dr_01": {
            "sys_id": "ci_exacc_ny_corp_dr_01", "name": "exacc-ny-corp-dr-01",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "DR",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "Americas Trading Platform",
            "u_datacenter": "CORP", "u_region": "New York", "u_rack": "ExaCC-X9M-CORP-01",
        },

        # ── ExaCC Production CIs — India Region ───────────────────
        "ci_exacc_in_bkc_prd_01": {
            "sys_id": "ci_exacc_in_bkc_prd_01", "name": "exacc-in-bkc-prd-01",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "India Core Banking",
            "u_datacenter": "BKC", "u_region": "India", "u_rack": "ExaCC-X9M-BKC-01",
        },
        "ci_exacc_in_bkc_prd_02": {
            "sys_id": "ci_exacc_in_bkc_prd_02", "name": "exacc-in-bkc-prd-02",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "India Payments",
            "u_datacenter": "BKC", "u_region": "India", "u_rack": "ExaCC-X9M-BKC-01",
        },
        # ExaCC DR CIs — India
        "ci_exacc_in_tata_dr_01": {
            "sys_id": "ci_exacc_in_tata_dr_01", "name": "exacc-in-tata-dr-01",
            "sys_class_name": "cmdb_ci_db_ora_instance", "environment": "DR",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "India Core Banking",
            "u_datacenter": "Tata", "u_region": "India", "u_rack": "ExaCC-X9M-Tata-01",
        },

        # ── Shared network / infrastructure CIs (all regions) ─────
        "ci_exacc_global_oci_gw_01": {
            "sys_id": "ci_exacc_global_oci_gw_01", "name": "oci-exacc-gateway-global-01",
            "sys_class_name": "cmdb_ci_network_adapter", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "OCI ExaCC Management",
        },
        "ci_exacc_global_dg_broker_01": {
            "sys_id": "ci_exacc_global_dg_broker_01", "name": "oracle-dg-broker-global-01",
            "sys_class_name": "cmdb_ci_middleware", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "Oracle Data Guard",
        },
    }

    # ── Mock CI Relationships ──────────────────────────────────
    RELATIONSHIPS = {
        # Original relationships (kept)
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

        # ── ExaCC UK CDC PRD — switchover to WDC DR ────────────────
        "ci_exacc_uk_cdc_prd_01": [
            {"parent": {"value": "ci_exacc_uk_cdc_prd_01"},
             "child":  {"value": "ci_exacc_uk_wdc_dr_01"},
             "type":   {"display_value": "Failover target::Failover source"}},
            {"parent": {"value": "ci_exacc_uk_cdc_prd_02"},
             "child":  {"value": "ci_exacc_uk_cdc_prd_01"},
             "type":   {"display_value": "Cluster member::Cluster member"}},
            {"parent": {"value": "ci_exacc_uk_cdc_prd_01"},
             "child":  {"value": "ci_exacc_global_dg_broker_01"},
             "type":   {"display_value": "Managed by::Manages"}},
            {"parent": {"value": "ci_exacc_uk_cdc_prd_01"},
             "child":  {"value": "ci_exacc_de_dcn_prd_01"},
             "type":   {"display_value": "Cross-region peer::Cross-region peer"}},
        ],
        "ci_exacc_uk_cdc_prd_02": [
            {"parent": {"value": "ci_exacc_uk_cdc_prd_02"},
             "child":  {"value": "ci_exacc_uk_wdc_dr_02"},
             "type":   {"display_value": "Failover target::Failover source"}},
            {"parent": {"value": "ci_exacc_uk_cdc_prd_01"},
             "child":  {"value": "ci_exacc_uk_cdc_prd_02"},
             "type":   {"display_value": "Cluster member::Cluster member"}},
        ],
        "ci_exacc_uk_wdc_dr_01": [
            {"parent": {"value": "ci_exacc_uk_cdc_prd_01"},
             "child":  {"value": "ci_exacc_uk_wdc_dr_01"},
             "type":   {"display_value": "Failover target::Failover source"}},
            {"parent": {"value": "ci_exacc_uk_wdc_dr_01"},
             "child":  {"value": "ci_exacc_uk_wdc_dr_02"},
             "type":   {"display_value": "Cluster member::Cluster member"}},
        ],

        # ── ExaCC Germany DCN PRD — switchover to DCB DR ───────────
        "ci_exacc_de_dcn_prd_01": [
            {"parent": {"value": "ci_exacc_de_dcn_prd_01"},
             "child":  {"value": "ci_exacc_de_dcb_dr_01"},
             "type":   {"display_value": "Failover target::Failover source"}},
            {"parent": {"value": "ci_exacc_de_dcn_prd_02"},
             "child":  {"value": "ci_exacc_de_dcn_prd_01"},
             "type":   {"display_value": "Cluster member::Cluster member"}},
            {"parent": {"value": "ci_exacc_de_dcn_prd_01"},
             "child":  {"value": "ci_exacc_global_dg_broker_01"},
             "type":   {"display_value": "Managed by::Manages"}},
        ],

        # ── ExaCC Singapore 9TS PRD — switchover to DSJ DR ─────────
        "ci_exacc_sg_9ts_prd_01": [
            {"parent": {"value": "ci_exacc_sg_9ts_prd_01"},
             "child":  {"value": "ci_exacc_sg_dsj_dr_01"},
             "type":   {"display_value": "Failover target::Failover source"}},
            {"parent": {"value": "ci_exacc_sg_9ts_prd_02"},
             "child":  {"value": "ci_exacc_sg_9ts_prd_01"},
             "type":   {"display_value": "Cluster member::Cluster member"}},
            {"parent": {"value": "ci_exacc_sg_9ts_prd_01"},
             "child":  {"value": "ci_exacc_global_dg_broker_01"},
             "type":   {"display_value": "Managed by::Manages"}},
        ],

        # ── ExaCC New York 2PK PRD — switchover to CORP DR ─────────
        "ci_exacc_ny_2pk_prd_01": [
            {"parent": {"value": "ci_exacc_ny_2pk_prd_01"},
             "child":  {"value": "ci_exacc_ny_corp_dr_01"},
             "type":   {"display_value": "Failover target::Failover source"}},
            {"parent": {"value": "ci_exacc_ny_2pk_prd_02"},
             "child":  {"value": "ci_exacc_ny_2pk_prd_01"},
             "type":   {"display_value": "Cluster member::Cluster member"}},
        ],

        # ── ExaCC India BKC PRD — switchover to Tata DR ────────────
        "ci_exacc_in_bkc_prd_01": [
            {"parent": {"value": "ci_exacc_in_bkc_prd_01"},
             "child":  {"value": "ci_exacc_in_tata_dr_01"},
             "type":   {"display_value": "Failover target::Failover source"}},
            {"parent": {"value": "ci_exacc_in_bkc_prd_02"},
             "child":  {"value": "ci_exacc_in_bkc_prd_01"},
             "type":   {"display_value": "Cluster member::Cluster member"}},
            {"parent": {"value": "ci_exacc_in_bkc_prd_01"},
             "child":  {"value": "ci_exacc_global_dg_broker_01"},
             "type":   {"display_value": "Managed by::Manages"}},
        ],
    }

    # ── Mock Maintenance Windows ───────────────────────────────
    MAINTENANCE = {
        "ci_sys_oracle_prd_01": [
            {"name": "Monthly DB Maintenance", "start_date": "2025-03-15 02:00:00",
             "end_date": "2025-03-15 04:00:00", "schedule": "Monthly"},
        ],
        "ci_sys_fw_prd_01": [
            {"name": "Weekly Firewall Review", "start_date": "2025-03-21 00:00:00",
             "end_date": "2025-03-21 01:00:00", "schedule": "Weekly"},
        ],
        "ci_exacc_uk_cdc_prd_01": [
            {"name": "ExaCC Quarterly Maintenance", "start_date": "2025-04-05 22:00:00",
             "end_date": "2025-04-05 23:30:00", "schedule": "Quarterly"},
        ],
        "ci_exacc_sg_9ts_prd_01": [
            {"name": "ExaCC Quarterly Maintenance APAC", "start_date": "2025-06-14 22:00:00",
             "end_date": "2025-06-14 23:30:00", "schedule": "Quarterly"},
        ],
    }

    # ── Application-wise CIs ─────────────────────────────────
    # Change 2: Application-to-CI mapping for RSP, UK-Axiom, SRC, CAD JP, RCL
    # These allow the LLM to answer "is PROD impacted for RSP?"
    APP_CIS = {
        "ci_app_rsp_uk_prd_01": {
            "sys_id": "ci_app_rsp_uk_prd_01", "name": "rsp-uk-app-prd-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "RSP", "u_application": "RSP",
            "u_datacenter": "CDC", "u_region": "UK",
        },
        "ci_app_rsp_uk_prd_02": {
            "sys_id": "ci_app_rsp_uk_prd_02", "name": "rsp-uk-app-prd-02",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "RSP", "u_application": "RSP",
            "u_datacenter": "CDC", "u_region": "UK",
        },
        "ci_app_rsp_uk_dr_01": {
            "sys_id": "ci_app_rsp_uk_dr_01", "name": "rsp-uk-app-dr-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "DR",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "RSP", "u_application": "RSP",
            "u_datacenter": "WDC", "u_region": "UK",
        },
        "ci_app_rsp_de_prd_01": {
            "sys_id": "ci_app_rsp_de_prd_01", "name": "rsp-de-app-prd-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "RSP", "u_application": "RSP",
            "u_datacenter": "DCN", "u_region": "Germany",
        },

        # UK-Axiom — UK fixed income trading platform
        "ci_app_ukaxiom_prd_01": {
            "sys_id": "ci_app_ukaxiom_prd_01", "name": "uk-axiom-app-prd-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "UK-Axiom", "u_application": "UK-Axiom",
            "u_datacenter": "CDC", "u_region": "UK",
        },
        "ci_app_ukaxiom_prd_02": {
            "sys_id": "ci_app_ukaxiom_prd_02", "name": "uk-axiom-app-prd-02",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "UK-Axiom", "u_application": "UK-Axiom",
            "u_datacenter": "CDC", "u_region": "UK",
        },
        "ci_app_ukaxiom_dr_01": {
            "sys_id": "ci_app_ukaxiom_dr_01", "name": "uk-axiom-app-dr-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "DR",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "UK-Axiom", "u_application": "UK-Axiom",
            "u_datacenter": "WDC", "u_region": "UK",
        },
        "ci_app_ukaxiom_nonprod_01": {
            "sys_id": "ci_app_ukaxiom_nonprod_01", "name": "uk-axiom-app-uat-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Non-Production",
            "operational_status": "1", "u_tier": "Tier-2",
            "u_business_service": "UK-Axiom", "u_application": "UK-Axiom",
            "u_datacenter": "CDC", "u_region": "UK",
        },

        # SRC — Securities Reference & Collateral (Singapore + UK)
        "ci_app_src_sg_prd_01": {
            "sys_id": "ci_app_src_sg_prd_01", "name": "src-sg-app-prd-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "SRC", "u_application": "SRC",
            "u_datacenter": "9TS", "u_region": "Singapore",
        },
        "ci_app_src_sg_prd_02": {
            "sys_id": "ci_app_src_sg_prd_02", "name": "src-sg-app-prd-02",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "SRC", "u_application": "SRC",
            "u_datacenter": "9TS", "u_region": "Singapore",
        },
        "ci_app_src_sg_dr_01": {
            "sys_id": "ci_app_src_sg_dr_01", "name": "src-sg-app-dr-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "DR",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "SRC", "u_application": "SRC",
            "u_datacenter": "DSJ", "u_region": "Singapore",
        },
        "ci_app_src_uk_prd_01": {
            "sys_id": "ci_app_src_uk_prd_01", "name": "src-uk-app-prd-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "SRC", "u_application": "SRC",
            "u_datacenter": "CDC", "u_region": "UK",
        },

        # CAD JP — Canadian/Japan clearing & derivatives (New York + Singapore)
        "ci_app_cadjp_ny_prd_01": {
            "sys_id": "ci_app_cadjp_ny_prd_01", "name": "cadjp-ny-app-prd-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "CAD JP", "u_application": "CAD JP",
            "u_datacenter": "2PK", "u_region": "New York",
        },
        "ci_app_cadjp_ny_prd_02": {
            "sys_id": "ci_app_cadjp_ny_prd_02", "name": "cadjp-ny-app-prd-02",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "CAD JP", "u_application": "CAD JP",
            "u_datacenter": "2PK", "u_region": "New York",
        },
        "ci_app_cadjp_ny_dr_01": {
            "sys_id": "ci_app_cadjp_ny_dr_01", "name": "cadjp-ny-app-dr-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "DR",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "CAD JP", "u_application": "CAD JP",
            "u_datacenter": "CORP", "u_region": "New York",
        },
        "ci_app_cadjp_sg_prd_01": {
            "sys_id": "ci_app_cadjp_sg_prd_01", "name": "cadjp-sg-app-prd-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "CAD JP", "u_application": "CAD JP",
            "u_datacenter": "9TS", "u_region": "Singapore",
        },
        "ci_app_cadjp_nonprod_01": {
            "sys_id": "ci_app_cadjp_nonprod_01", "name": "cadjp-ny-app-qa-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Non-Production",
            "operational_status": "1", "u_tier": "Tier-2",
            "u_business_service": "CAD JP", "u_application": "CAD JP",
            "u_datacenter": "2PK", "u_region": "New York",
        },

        # RCL — Regulatory Compliance & Lifecycle (India + Germany)
        "ci_app_rcl_in_prd_01": {
            "sys_id": "ci_app_rcl_in_prd_01", "name": "rcl-in-app-prd-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "RCL", "u_application": "RCL",
            "u_datacenter": "BKC", "u_region": "India",
        },
        "ci_app_rcl_in_prd_02": {
            "sys_id": "ci_app_rcl_in_prd_02", "name": "rcl-in-app-prd-02",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "RCL", "u_application": "RCL",
            "u_datacenter": "BKC", "u_region": "India",
        },
        "ci_app_rcl_in_dr_01": {
            "sys_id": "ci_app_rcl_in_dr_01", "name": "rcl-in-app-dr-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "DR",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "RCL", "u_application": "RCL",
            "u_datacenter": "Tata", "u_region": "India",
        },
        "ci_app_rcl_de_prd_01": {
            "sys_id": "ci_app_rcl_de_prd_01", "name": "rcl-de-app-prd-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-1",
            "u_business_service": "RCL", "u_application": "RCL",
            "u_datacenter": "DCN", "u_region": "Germany",
        },
        "ci_app_rcl_nonprod_01": {
            "sys_id": "ci_app_rcl_nonprod_01", "name": "rcl-in-app-uat-01",
            "sys_class_name": "cmdb_ci_app_server", "environment": "Non-Production",
            "operational_status": "1", "u_tier": "Tier-2",
            "u_business_service": "RCL", "u_application": "RCL",
            "u_datacenter": "BKC", "u_region": "India",
        },
    }
    APP_CI_RELATIONSHIPS = {
        # RSP depends on UK ExaCC DB
        "ci_app_rsp_uk_prd_01": [
            {"parent": {"value": "ci_app_rsp_uk_prd_01"},
             "child":  {"value": "ci_exacc_uk_cdc_prd_01"},
             "type":   {"display_value": "Depends on::Used by"}},
            {"parent": {"value": "ci_app_rsp_uk_prd_01"},
             "child":  {"value": "ci_app_rsp_uk_prd_02"},
             "type":   {"display_value": "Cluster member::Cluster member"}},
        ],
        "ci_app_rsp_de_prd_01": [
            {"parent": {"value": "ci_app_rsp_de_prd_01"},
             "child":  {"value": "ci_exacc_de_dcn_prd_01"},
             "type":   {"display_value": "Depends on::Used by"}},
        ],
        # UK-Axiom depends on UK ExaCC DB
        "ci_app_ukaxiom_prd_01": [
            {"parent": {"value": "ci_app_ukaxiom_prd_01"},
             "child":  {"value": "ci_exacc_uk_cdc_prd_01"},
             "type":   {"display_value": "Depends on::Used by"}},
            {"parent": {"value": "ci_app_ukaxiom_prd_01"},
             "child":  {"value": "ci_app_ukaxiom_prd_02"},
             "type":   {"display_value": "Cluster member::Cluster member"}},
        ],
        # SRC depends on Singapore ExaCC DB
        "ci_app_src_sg_prd_01": [
            {"parent": {"value": "ci_app_src_sg_prd_01"},
             "child":  {"value": "ci_exacc_sg_9ts_prd_01"},
             "type":   {"display_value": "Depends on::Used by"}},
            {"parent": {"value": "ci_app_src_sg_prd_01"},
             "child":  {"value": "ci_app_src_sg_prd_02"},
             "type":   {"display_value": "Cluster member::Cluster member"}},
        ],
        # CAD JP depends on New York ExaCC DB
        "ci_app_cadjp_ny_prd_01": [
            {"parent": {"value": "ci_app_cadjp_ny_prd_01"},
             "child":  {"value": "ci_exacc_ny_2pk_prd_01"},
             "type":   {"display_value": "Depends on::Used by"}},
            {"parent": {"value": "ci_app_cadjp_sg_prd_01"},
             "child":  {"value": "ci_app_cadjp_ny_prd_01"},
             "type":   {"display_value": "Cross-region peer::Cross-region peer"}},
        ],
        # RCL depends on India ExaCC DB
        "ci_app_rcl_in_prd_01": [
            {"parent": {"value": "ci_app_rcl_in_prd_01"},
             "child":  {"value": "ci_exacc_in_bkc_prd_01"},
             "type":   {"display_value": "Depends on::Used by"}},
            {"parent": {"value": "ci_app_rcl_in_prd_01"},
             "child":  {"value": "ci_app_rcl_in_prd_02"},
             "type":   {"display_value": "Cluster member::Cluster member"}},
        ],
        "ci_app_rcl_de_prd_01": [
            {"parent": {"value": "ci_app_rcl_de_prd_01"},
             "child":  {"value": "ci_exacc_de_dcn_prd_01"},
             "type":   {"display_value": "Depends on::Used by"}},
        ],
    }

    # ── Application-to-CI index (for direct app lookup) ──────
    # Maps application name → list of CI sys_ids across all envs
    APP_INDEX = {
        "RSP":      ["ci_app_rsp_uk_prd_01", "ci_app_rsp_uk_prd_02",
                     "ci_app_rsp_uk_dr_01",  "ci_app_rsp_de_prd_01"],
        "UK-AXIOM": ["ci_app_ukaxiom_prd_01",    "ci_app_ukaxiom_prd_02",
                     "ci_app_ukaxiom_dr_01",      "ci_app_ukaxiom_nonprod_01"],
        "SRC":      ["ci_app_src_sg_prd_01", "ci_app_src_sg_prd_02",
                     "ci_app_src_sg_dr_01",  "ci_app_src_uk_prd_01"],
        "CAD JP":   ["ci_app_cadjp_ny_prd_01", "ci_app_cadjp_ny_prd_02",
                     "ci_app_cadjp_ny_dr_01",  "ci_app_cadjp_sg_prd_01",
                     "ci_app_cadjp_nonprod_01"],
        "RCL":      ["ci_app_rcl_in_prd_01", "ci_app_rcl_in_prd_02",
                     "ci_app_rcl_in_dr_01",  "ci_app_rcl_de_prd_01",
                     "ci_app_rcl_nonprod_01"],
    }

    # ── Lookup methods ─────────────────────────────────────────

    def get_change(self, chg_number: str) -> dict:
        record = self.CHANGES.get(chg_number.upper())
        if not record:
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
        # Check main CIs first, then app CIs
        record = self.CIS.get(sys_id) or self.APP_CIS.get(sys_id)
        if record:
            return record
        return {
            "sys_id": sys_id, "name": f"mock-ci-{sys_id[:8]}",
            "sys_class_name": "cmdb_ci_server", "environment": "Production",
            "operational_status": "1", "u_tier": "Tier-2", "u_business_service": "Unknown",
        }

    def get_ci_relationships(self, ci_sys_id: str) -> list:
        # Check main relationships first, then app relationships
        return (self.RELATIONSHIPS.get(ci_sys_id)
                or self.APP_CI_RELATIONSHIPS.get(ci_sys_id)
                or [])

    def get_maintenance_windows(self, ci_sys_id: str) -> list:
        return self.MAINTENANCE.get(ci_sys_id, [])

    def get_app_cis(self, app_name: str) -> list:
        """
        Return all CIs for a given application name (e.g. 'RSP', 'UK-Axiom').
        Useful for answering 'is PROD impacted for RSP?'
        """
        key      = app_name.upper().replace("-", " ").replace(" ", "-")
        synonyms = {
            "UK-AXIOM": "UK-AXIOM", "UKAXIOM": "UK-AXIOM",
            "CAD-JP": "CAD JP",     "CADJP": "CAD JP",
            "RSP": "RSP", "SRC": "SRC", "RCL": "RCL",
        }
        lookup_key = synonyms.get(key, app_name.upper())
        sys_ids    = self.APP_INDEX.get(lookup_key, [])
        return [self.APP_CIS[sid] for sid in sys_ids if sid in self.APP_CIS]


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
                              "u_environment,cmdb_ci,u_contact_list,u_contact_instructions,"
                              "u_risk_description,u_user_service_impact,change_reason",
            "sysparm_limit":  1,
        })
        return results[0] if results else {}

    def get_ci_by_id(self, sys_id: str) -> dict:
        results = self._get("cmdb_ci", {
            "sysparm_query":  f"sys_id={sys_id}",
            "sysparm_fields": "sys_id,name,sys_class_name,environment,"
                              "operational_status,u_tier,u_business_service,"
                              "u_datacenter,u_region,u_rack",
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
        change = client.get_change("CHG0003774804")
    """
    if USE_MOCK_SERVICENOW:
        print("[ServiceNow] MOCK MODE — using local test data (set USE_MOCK_SERVICENOW=false to use real SNOW)")
        return MockServiceNowData()
    else:
        print("[ServiceNow] LIVE MODE — connecting to", SNOW_INSTANCE)
        return _RealServiceNowClient()
