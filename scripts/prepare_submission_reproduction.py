"""Create isolated reproduction configs; never overwrite evidence or existing configs."""
import argparse
from pathlib import Path
import re
import yaml
from sbernet.config import load_config


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--tag',required=True); args=parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',args.tag):
        raise ValueError('Tag must contain only letters, digits, underscores or hyphens')
    configs=Path('configs')/f'round16_reproduction_{args.tag}'
    output=Path('outputs')/f'round16_reproduction_{args.tag}'
    if output.exists() or configs.exists():
        raise FileExistsError('Choose a new tag; reproduction directories already exist')
    configs.mkdir()
    gate=str(output/'baseline')
    sources={'benchmark':'benchmark_canonical.yaml','leiden':'leiden.yaml',
             'perturbation_v2':'perturbation_v2.yaml','decomposition':'round16_decomposition.yaml',
             'protocol_gate':'round16_protocol_gate.yaml','resolution':'resolution_sensitivity.yaml',
             'competition':'competition_artifacts.yaml'}
    for name,source in sources.items():
        cfg=load_config(Path('configs')/source)
        cfg['paths']['output_dir']=str(output/name)
        cfg['experiment']['baseline_gate_dir']=gate
        if name in ['perturbation_v2','protocol_gate']:
            cfg['experiment']['leiden_output_dir']=str(output/'leiden')
        if name=='decomposition':
            cfg['experiment']['protocol_gate_dir']=str(output/'protocol_gate')
            cfg['experiment']['protocol_gate_config']=str(configs/'protocol_gate.yaml')
        (configs/f'{name}.yaml').write_text(yaml.safe_dump(cfg,allow_unicode=True,sort_keys=False),encoding='utf-8')
    print(f'Configs: {configs}; fresh baseline output: {gate}')


if __name__=='__main__':
    main()
