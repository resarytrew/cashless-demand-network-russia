"""Offline Round17 replay. Existing completed outputs are verified, never overwritten."""
import argparse
import json
from pathlib import Path

from sbernet.validation.external_economic import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/round17_external_validation.yaml")
    parser.add_argument("--output-dir", help="Empty directory for independent replay")
    args = parser.parse_args()
    print(json.dumps(run(args.config, Path(__file__).resolve().parents[1], args.output_dir), indent=2))


if __name__ == "__main__":
    main()
