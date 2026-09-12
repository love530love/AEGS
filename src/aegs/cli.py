from __future__ import annotations

import argparse
import json
import sys

from .console import serve
from .core import AEGSError, create_handoff, create_proposal, decide, initialise, verify
from .discovery import discover


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
    proposal = commands.add_parser("proposal", help="manage evolution proposals")
    proposal_commands = proposal.add_subparsers(dest="proposal_command", required=True)
    create = proposal_commands.add_parser("create")
    create.add_argument("path", nargs="?", default=".")
    create.add_argument("--title", required=True)
    create.add_argument("--risk", required=True, choices=["GREEN", "YELLOW", "RED"])
    create.add_argument("--proposer", required=True)
    decision = commands.add_parser("decide", help="record an owner decision")
    decision.add_argument("path", nargs="?", default=".")
    decision.add_argument("--proposal", required=True)
    decision.add_argument("--action", required=True, choices=["APPROVE", "REJECT", "DEFER", "HOLD"])
    decision.add_argument("--approver", required=True)
    decision.add_argument("--evidence")
    decision.add_argument("--rollback")
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
        elif args.command == "proposal" and args.proposal_command == "create":
            result = create_proposal(args.path, args.title, args.risk, args.proposer)
        else:
            result = decide(args.path, args.proposal, args.action, args.approver, args.evidence, args.rollback)
    except AEGSError as error:
        print(f"AEGS error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
