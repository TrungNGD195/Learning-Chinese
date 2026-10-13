from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from app.core.config import get_settings

from .runner import offline_settings, run_generation_offline, run_grading_offline


async def _run(track: str, run_id: str | None, output_root):
    if track == "all" and run_id is None:
        run_id = f"step77-{uuid.uuid4()}"
    result = {}
    if track in {"grading", "all"}:
        result["grading"] = await run_grading_offline(offline_settings(), run_id=run_id, output_root=output_root)
    if track in {"assessment_generation", "all"}:
        try:
            settings = get_settings()
        except Exception:
            raise RuntimeError("dedicated test database configuration is unavailable") from None
        result["assessment_generation"] = await run_generation_offline(settings, run_id=run_id, output_root=output_root)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 7.7 offline deterministic evaluator")
    parser.add_argument("--track", choices=("grading", "assessment_generation", "all"), required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--output-root", default=str(Path(__file__).resolve().parents[4] / "evaluation/runs"))
    args = parser.parse_args()
    try:
        result = asyncio.run(_run(args.track, args.run_id, args.output_root))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    except Exception as exc:
        print(json.dumps({"status": "BLOCKED_OFFLINE_PREREQUISITE", "error_type": type(exc).__name__,
                          "reason": "dedicated test DB prerequisite unavailable or offline evaluator failed"},
                         sort_keys=True))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
