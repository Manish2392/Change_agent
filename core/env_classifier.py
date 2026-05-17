# core/env_classifier.py — Step 3: EnvClassifier
# Pure Python rules engine. No API calls needed — fully testable offline.

from config import PROD_ENVS, DR_ENVS, NONPROD_ENVS


def classify_environments(ci_list: list) -> dict:
    """
    Classifies each CI as PROD / DR / NON-PROD / UNKNOWN.
    Returns grouped dict + summary counts.
    """
    classified = {"all_cis": [], "prod": [], "dr": [], "nonprod": [], "unknown": []}

    for ci in ci_list:
        env_raw  = (ci.get("environment") or "").lower().strip()
        name_raw = (ci.get("name")        or "").lower()

        env_class    = _classify(env_raw, name_raw)
        ci["env_class"] = env_class
        classified["all_cis"].append(ci)

        bucket = {"PROD": "prod", "DR": "dr", "NON-PROD": "nonprod"}.get(env_class, "unknown")
        classified[bucket].append(ci)

    classified["summary"] = {
        "PROD":     len(classified["prod"]),
        "DR":       len(classified["dr"]),
        "NON-PROD": len(classified["nonprod"]),
        "UNKNOWN":  len(classified["unknown"]),
    }
    print(f"[EnvClassifier] ✓ {classified['summary']}")
    return classified


def _classify(env_field: str, ci_name: str) -> str:
    """Check env field first, then fall back to CI naming patterns."""
    for p in PROD_ENVS:
        if p in env_field:
            return "PROD"
    for d in DR_ENVS:
        if d in env_field:
            return "DR"
    for n in NONPROD_ENVS:
        if n in env_field:
            return "NON-PROD"

    # Naming convention fallback: e.g. "webserver-prd-01", "db-qa-02"
    for p in PROD_ENVS:
        if f"-{p}-" in ci_name or ci_name.endswith(f"-{p}"):
            return "PROD"
    for d in DR_ENVS:
        if f"-{d}-" in ci_name or ci_name.endswith(f"-{d}"):
            return "DR"
    for n in NONPROD_ENVS:
        if f"-{n}-" in ci_name or ci_name.endswith(f"-{n}"):
            return "NON-PROD"

    return "UNKNOWN"


# ── Quick offline test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample = [
        {"sys_id": "1", "name": "app-server-prd-01", "environment": "Production"},
        {"sys_id": "2", "name": "db-qa-02",           "environment": "QA"},
        {"sys_id": "3", "name": "lb-dr-01",           "environment": "DR"},
        {"sys_id": "4", "name": "mystery-box",        "environment": ""},
    ]
    result = classify_environments(sample)
    for ci in result["all_cis"]:
        print(f"  {ci['name']:35} → {ci['env_class']}")
