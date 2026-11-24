import argparse
import json
import sys
from pathlib import Path
from typing import List
from .schema import save_contract
from .differ import diff_payload_against_contract, DriftIssue
from .redact import redact_payload
from .license import verify_pro_license


def _load_json(filepath: str):
    path = Path(filepath)
    if not path.exists():
        print(f"Error: File not found -> {filepath}", file=sys.stderr)
        sys.exit(2)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _format_markdown(issues: List[DriftIssue]) -> str:
    if not issues:
        return "### DriftLock Report: Passed\nNo schema or type drift detected."
    lines = [
        "### DriftLock Schema Report",
        "",
        "| Severity | Path | Details |",
        "| :--- | :--- | :--- |",
    ]
    for issue in issues:
        badge = "BREAKING" if issue.severity == "BREAKING" else "NON-BREAKING"
        lines.append(f"| **{badge}** | `{issue.path}` | {issue.message} |")
    return "\n".join(lines)


def _require_pro(license_key: str | None) -> None:
    ok, reason = verify_pro_license(license_key)
    if not ok:
        print(f"[DriftLock Pro Required] {reason}", file=sys.stderr)
        print("Upgrade for Pro license key (redact + strict CI gating).", file=sys.stderr)
        sys.exit(3)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="driftlock",
        description="Lock webhook & API JSON contracts and catch breaking schema drift.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # snapshot (Free)
    snap_p = subparsers.add_parser("snapshot", help="Generate a baseline contract from a JSON payload")
    snap_p.add_argument("payload", help="Path to sample JSON payload")
    snap_p.add_argument("-o", "--output", default="driftlock.contract.json", help="Output contract path")

    # diff (Free core; --strict is Pro)
    diff_p = subparsers.add_parser("diff", help="Check a payload against a locked contract")
    diff_p.add_argument("contract", help="Path to locked contract JSON")
    diff_p.add_argument("payload", help="Path to incoming JSON payload")
    diff_p.add_argument("--markdown", action="store_true", help="Output GitHub PR Markdown table")
    diff_p.add_argument("--strict", action="store_true", help="[Pro] Fail on non-breaking field additions too")
    diff_p.add_argument("--license-key", default=None, help="DriftLock Pro license key")

    # redact (Pro)
    red_p = subparsers.add_parser("redact", help="[Pro] Mask secrets and PII in a JSON payload for safe Git commits")
    red_p.add_argument("payload", help="Path to raw JSON payload")
    red_p.add_argument("-o", "--output", required=True, help="Output sanitized JSON path")
    red_p.add_argument("--license-key", default=None, help="DriftLock Pro license key")

    args = parser.parse_args()

    if args.command == "snapshot":
        payload = _load_json(args.payload)
        save_contract(payload, args.output)
        print(f"[DriftLock] Contract locked -> {args.output}")

    elif args.command == "diff":
        if args.strict:
            _require_pro(args.license_key)

        contract = _load_json(args.contract)
        payload = _load_json(args.payload)
        issues = diff_payload_against_contract(contract, payload)

        if args.markdown:
            print(_format_markdown(issues))
        else:
            if not issues:
                print("[DriftLock] OK - Payload matches locked contract.")
            for issue in issues:
                tag = "[BREAKING]" if issue.severity == "BREAKING" else "[INFO]"
                print(f"{tag} {issue.path}: {issue.message}")

        breaking_count = sum(1 for i in issues if i.severity == "BREAKING")
        if breaking_count > 0 or (args.strict and len(issues) > 0):
            sys.exit(1)
        sys.exit(0)

    elif args.command == "redact":
        _require_pro(args.license_key)
        payload = _load_json(args.payload)
        clean = redact_payload(payload)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(clean, f, indent=2)
        print(f"[DriftLock] Sanitized fixture written -> {args.output}")


if __name__ == "__main__":
    main()