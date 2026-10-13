from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.core.config import get_settings

from .eligibility import select_eligible_cases
from .runner import Step74Runner


async def _run(args) -> int:
    if args.command == "offline-preflight":
        _, cases = select_eligible_cases()
        print(json.dumps({"mode": "OFFLINE_IMPLEMENTATION", "paid_api_calls": 0,
                          "eligible_case_count": len(cases),
                          "development_count": sum(row["split"] == "DEVELOPMENT" for row in cases),
                          "holdout_count": sum(row["split"] == "HOLDOUT" for row in cases)}, indent=2))
        return 0
    runner = Step74Runner(settings=get_settings())
    if args.command == "execute-live-stage-a":
        result = await runner.run_stage_a()
    elif args.command == "resume-stage-b":
        result = await runner.resume_stage_b_from_run(
            args.run_id,
            annotation_file=args.annotation_file,
        )
    else:
        raise RuntimeError("Unknown Step 7.4 command")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Step 7.4 generation-isolated evaluation")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("offline-preflight", help="Validate pinned offline dataset eligibility only")
    commands.add_parser("execute-live-stage-a", help="Run mandatory real smokes, then official Stage A")
    resume = commands.add_parser("resume-stage-b", help="Resume the same frozen Stage-A run after human approval")
    resume.add_argument("run_id")
    resume.add_argument("--annotation-file", type=Path)
    args = parser.parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
