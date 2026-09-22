"""Generate public presentation assets without running any research experiment."""
import argparse
import json
from pathlib import Path
from sbernet.visualization.public import build

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--images-dir', type=Path)
    args = parser.parse_args()
    print(json.dumps(build(Path(__file__).resolve().parents[1], args.output_dir, args.images_dir), indent=2))
