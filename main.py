# main.py — FlowMaster CLI Entry Point
# Run: python main.py CHG0012345
# Or : python main.py --load reports/report_CHG0012345.json

import sys
import argparse
from pipeline import run_pipeline, save_report, load_report
from ops_copilot import OpsCopilot


def main():
    parser = argparse.ArgumentParser(description="FlowMaster – Change Impact Analysis Agent")
    parser.add_argument("chg_number", nargs="?", help="ServiceNow CHG number (e.g. CHG0012345)")
    parser.add_argument("--load",  metavar="FILE",   help="Load existing JSON report for Q&A")
    parser.add_argument("--no-qa", action="store_true", help="Run pipeline only, skip Q&A")
    args = parser.parse_args()

    # ── Load existing report OR run full pipeline ──────────────────────────
    if args.load:
        print(f"[Main] Loading report: {args.load}")
        report = load_report(args.load)
    else:
        chg = args.chg_number or input("Enter CHG number (e.g. CHG0012345): ").strip()
        if not chg:
            print("Error: CHG number is required.")
            sys.exit(1)
        report = run_pipeline(chg)
        if "error" in report:
            print(f"\n✗ Error: {report['error']}")
            sys.exit(1)
        save_report(report)

    _print_summary(report)

    # ── Interactive Q&A ────────────────────────────────────────────────────
    if not args.no_qa:
        copilot = OpsCopilot(report)
        copilot.interactive_session()


def _print_summary(report: dict):
    change  = report.get("change",     {})
    summary = report.get("ci_summary", {})
    impact  = report.get("impact",     {})
    print(f"""
╔══════════════════════════════════════════════════════╗
║      FlowMaster — Impact Report Summary              ║
╠══════════════════════════════════════════════════════╣
║ Change  : {change.get('chg_number', 'N/A'):<43}║
║ Desc    : {change.get('description', '')[:43]:<43}║
║ Window  : {str(change.get('start_date',''))[:20]} → {str(change.get('end_date',''))[:18]:<18}║
╠══════════════════════════════════════════════════════╣
║ SEVERITY: {impact.get('severity', 'N/A'):<43}║
║ Downtime: {str(impact.get('estimated_downtime_minutes','?')) + ' minutes':<43}║
║ Rollback: {impact.get('rollback_complexity', 'N/A'):<43}║
╠══════════════════════════════════════════════════════╣
║ PROD CIs    : {str(summary.get('PROD',     0)):<39}║
║ DR CIs      : {str(summary.get('DR',       0)):<39}║
║ NON-PROD CIs: {str(summary.get('NON-PROD', 0)):<39}║
╠══════════════════════════════════════════════════════╣
║ Risk: {impact.get('risk_summary','')[:47]:<47}║
╚══════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
