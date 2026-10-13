from __future__ import annotations

import argparse
import json
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the frozen Step 7.3 retrieval evaluation")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--ensure", action="store_true", help="reuse a matching fixture bootstrap or create it")
    action.add_argument("--reset", action="store_true", help="reset fixture-owned evaluation state, then run")
    args = parser.parse_args(argv)
    os.environ.setdefault("APP_ENV", "test")
    os.environ["RAG_EVIDENCE_CALIBRATION_MODE"] = "true"
    # Consume only the exact locally staged revisions; no floating or remote fallback.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    from app.evaluation.step73.runner import run_step73
    import asyncio
    try:
        result = asyncio.run(run_step73(reset=args.reset))
    except Exception as exc:
        # Application/provider exceptions can contain DSNs or model download URLs.
        # Keep CLI errors bounded to type and sanitized message.
        message = str(exc)
        if "@" in message or "password" in message.lower() or "postgresql+" in message:
            message = "sensitive connection detail redacted"
        print(json.dumps({"status": "FAILED", "error_type": type(exc).__name__, "error": message}, ensure_ascii=False))
        return 1
    print(json.dumps({
        "status": result["calibration"]["recommendation_status"],
        "run_id": result["run_id"], "artifact_path": result["run_dir"],
        "dataset_version": result["manifest"]["dataset_version"],
        "development_attempts": result["summary"]["metrics_by_split"]["DEVELOPMENT"]["attempt_count"],
        "holdout_attempts": result["summary"]["metrics_by_split"]["HOLDOUT"]["attempt_count"],
        "recommended_threshold": result["calibration"]["recommended_threshold"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
