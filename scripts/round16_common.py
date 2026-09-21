"""Shared Round 16 integrity and resumable, non-destructive output handling."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

import numpy as np

from sbernet.robustness.experiment_common import make_manifest, save_json
from sbernet.robustness.reproduction_gate import sha256


def array_hash(x):
    return hashlib.sha256(np.asarray(x, dtype='<f8', order='C').tobytes()).hexdigest()


def start_run(config_path, cfg, force=False):
    out = Path(cfg['paths']['output_dir'])
    manifest = make_manifest(config_path, cfg)
    manifest['round16_scripts_sha256'] = {
        str(p): sha256(p) for p in Path('scripts').glob('*round16*.py')}
    gate = Path(cfg['experiment']['baseline_gate_dir'])
    manifest['gate_sha256'] = {str(p): sha256(p) for p in [
        gate / 'baseline_gate.json', gate / 'graph_checksums.json', gate / 'baseline_graphs.pkl']}
    if out.exists():
        oldpath = out / 'run_manifest.json'
        if force:
            archive = out.with_name(out.name + '_archived_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
            shutil.move(str(out), str(archive))
        elif not oldpath.exists():
            raise FileExistsError(f'Existing output has no resume manifest: {out}; use --force or a new directory')
        else:
            old = json.loads(oldpath.read_text(encoding='utf-8'))
            for key in ['config_sha256', 'source_sha256', 'packages', 'round16_scripts_sha256', 'gate_sha256']:
                if old[key] != manifest[key]:
                    raise ValueError(f'Resume mismatch: {key}; use a new run directory')
            return out
    out.mkdir(parents=True, exist_ok=False)
    save_json(out / 'run_manifest.json', manifest)
    return out


def completed(directory):
    directory = Path(directory)
    p = directory / 'COMPLETED.json'
    if not p.exists():
        if directory.exists():
            raise ValueError(f'Incomplete checkpoint: {directory}; inspect it and use --force/new directory')
        return False
    expected = json.loads(p.read_text(encoding='utf-8'))
    for name, checksum in expected['files_sha256'].items():
        if sha256(directory / name) != checksum:
            raise ValueError(f'Corrupt checkpoint: {directory / name}')
    return True


def seal(directory):
    directory = Path(directory)
    save_json(directory / 'COMPLETED.json', {'files_sha256': {
        p.name: sha256(p) for p in directory.iterdir() if p.is_file() and p.name != 'COMPLETED.json'}})


def require_fresh(directory, force=False):
    p = Path(directory)
    if p.exists():
        if not force:
            raise FileExistsError(f'{p} exists; use --force or a new directory')
        shutil.move(str(p), str(p.with_name(p.name + '_archived_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))))
    p.mkdir(parents=True, exist_ok=False)
    return p
