from __future__ import annotations

import argparse
import json

from .pipeline import inspect_panel, run
from .config import load_config
from .robustness.region_null import run_region_admin_null


def main() -> None:
    parser = argparse.ArgumentParser(prog="sbernet")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_cmd = sub.add_parser("inspect-panel")
    inspect_cmd.add_argument("--config", required=True)

    run_cmd = sub.add_parser("run")
    run_cmd.add_argument("--config", required=True)
    run_cmd.add_argument("--mode", choices=["static", "temporal", "both"], default="both")

    args = parser.parse_args()

    if args.command == "inspect-panel":
        print(json.dumps(inspect_panel(args.config), ensure_ascii=False, indent=2))
    elif args.command == "run":
        run(args.config, mode=args.mode)
