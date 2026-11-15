from __future__ import annotations

import argparse
import json
import sys

from .console import serve
from .core import AEGSError, create_handoff, create_proposal, decide, doctor, initialise, takeover, verify
from .discovery import diff_snapshots, discover, list_snapshots


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="aegs", description="AEGS governance control-plane prototype")
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a .aegs governance package")
    init.add_argument("path")
    init.add_argument("--owner", required=True)
    check = commands.add_parser("verify", help="verify charter, state, and event ledger")
    check.add_argument("path", nargs="?", default=".")
    handoff = commands.add_parser("handoff", help="create a verified Agent handoff package")
    handoff.add_argument("path", nargs="?", default=".")
    discovery = commands.add_parser("discover", help="create a read-only architecture snapshot")
    discovery.add_argument("path", nargs="?", default=".")
    discovery.add_argument("--max-files", type=int, default=5000)
    takeover_command = commands.add_parser("takeover", help="gate Agent work on fresh verified project context")
    takeover_command.add_argument("path", nargs="?", default=".")
    doctor_command = commands.add_parser("doctor", help="run non-mutating project readiness diagnostics")
    doctor_command.add_argument("path", nargs="?", default=".")
    architecture = commands.add_parser("architecture", help="inspect stored architecture snapshots")
    architecture_commands = architecture.add_subparsers(dest="architecture_command", required=True)
    snapshots = architecture_commands.add_parser("list")
    snapshots.add_argument("path", nargs="?", default=".")
    diff = architecture_commands.add_parser("diff")
    diff.add_argument("path", nargs="?", default=".")
    diff.add_argument("--from", dest="older_id", required=True)
    diff.add_argument("--to", dest="newer_id", required=True)
    proposal = commands.add_parser("proposal", help="manage evolution proposals")
    proposal_commands = proposal.add_subparsers(dest="proposal_command", required=True)
    create = proposal_commands.add_parser("create")
    create.add_argument("path", nargs="?", default=".")
    create.add_argument("--title", required=True)
    create.add_argument("--risk", required=True, choices=["GREEN", "YELLOW", "RED"])
    create.add_argument("--proposer", required=True)
    create.add_argument("--scope", default="")
    create.add_argument("--alternatives", default="")
    create.add_argument("--impact", default="")
    create.add_argument("--counter-evidence", default="")
    create.add_argument("--acceptance-criteria", default="")
    create.add_argument("--expires-at")
    decision = commands.add_parser("decide", help="record an owner decision")
    decision.add_argument("path", nargs="?", default=".")
    decision.add_argument("--proposal", required=True)
    decision.add_argument("--action", required=True, choices=["APPROVE", "REJECT", "DEFER", "HOLD"])
    decision.add_argument("--approver", required=True)
    decision.add_argument("--evidence")
    decision.add_argument("--rollback")
    decision.add_argument("--reason")
    server = commands.add_parser("serve", help="run the local Human Governance Console")
    server.add_argument("path", nargs="?", default=".")
    server.add_argument("--port", type=int, default=8080)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "serve":
        if not 1 <= args.port <= 65535:
            parser().error("--port must be between 1 and 65535")
        try:
            serve(args.path, args.port)
        except AEGSError as error:
            print(f"AEGS error: {error}", file=sys.stderr)
            return 2
        return 0
    try:
        if args.command == "init":
            result = initialise(args.path, args.owner)
        elif args.command == "verify":
            result = verify(args.path)
        elif args.command == "handoff":
            result = create_handoff(args.path)
        elif args.command == "discover":
            result = discover(args.path, args.max_files)
        elif args.command == "takeover":
            result = takeover(args.path)
        elif args.command == "doctor":
            result = doctor(args.path)
        elif args.command == "architecture" and args.architecture_command == "list":
            result = {"snapshots": list_snapshots(args.path)}
        elif args.command == "architecture" and args.architecture_command == "diff":
            result = diff_snapshots(args.path, args.older_id, args.newer_id)
        elif args.command == "proposal" and args.proposal_command == "create":
            result = create_proposal(args.path, args.title, args.risk, args.proposer, args.scope, args.alternatives, args.impact, args.counter_evidence, args.acceptance_criteria, args.expires_at)
        else:
            result = decide(args.path, args.proposal, args.action, args.approver, args.evidence, args.rollback, args.reason)
    except AEGSError as error:
        print(f"AEGS error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
