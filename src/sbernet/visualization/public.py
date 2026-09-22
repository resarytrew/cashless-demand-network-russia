"""Build standalone public visuals from saved evidence; only new output roots are writable."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import html
import json
import shutil
import subprocess

import numpy as np
import pandas as pd
import yaml

from .stability_landscape import FIELDS, PROFILES, field_grid, project


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def landscape_svg(data, cfg, cells, standalone=False):
    def txt(x, y, text, size=14, **attrs):
        extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
        return f'<text x="{x}" y="{y}" font-size="{size}" {extra}>{html.escape(text)}</text>'
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 820 700" role="img" aria-label="Ландшафт близости 1904 муниципалитетов" id="landscape">',
             '<title>Стабильное окружение и смешанная близость</title>',
             '<desc>Фиксированные полюса A–G, не география. Точки взвешены по исходным долям близости. Цвет — сводный профиль; обводка — категория устойчивости.</desc>',
             f'<rect width="820" height="700" fill="{cfg["background"]}"/>',
             '<defs><filter id="field-soften"><feGaussianBlur stdDeviation="11"/></filter></defs><g id="field" aria-hidden="true" filter="url(#field-soften)">']
    for x, y, u in cells:
        shade = round(205 + 42 * u)
        parts.append(f'<circle cx="{x}" cy="{y}" r="23" fill="rgb({shade},{shade+2},{shade})" opacity="0.35"/>')
    parts += ['</g><g id="corridors" fill="none" stroke-linecap="round" aria-hidden="true">']
    for family, width, opacity in [("DFG", 30, .08), ("BE", 18, .06)]:
        coords = " ".join(",".join(map(str, cfg["anchors"][p])) for p in family)
        parts.append(f'<polyline points="{coords}" stroke="#617c74" stroke-width="{width}" opacity="{opacity}"/>')
        parts.append(f'<polyline points="{coords}" stroke="#a8b3ac" stroke-width="1" stroke-dasharray="4 6"/>')
    parts += ['</g><g id="points">']
    for r in data.to_dict("records"):
        color = cfg["profiles"].get(r["consensus_class"], "#777777")
        radius = cfg["radius"]["floor"] + cfg["radius"]["range"] * r["top_affinity_share"] ** cfg["radius"]["exponent"]
        opacity = cfg["opacity"]["floor"] + cfg["opacity"]["range"] * r["affinity_margin"]
        dashed = ' stroke-dasharray="2 2"' if r["stability_class"] in ("transition", "unresolved") else ""
        ring = "#929a96" if r["stability_class"] == "unresolved" else "#3c4b47"
        parts.append(f'<g class="point" data-id="{r["panel_index"]}" transform="translate({r["x"]:.8f} {r["y"]:.8f})" role="button" tabindex="-1" aria-label="{html.escape(r["municipality"], quote=True)}">')
        parts.append(f'<title>{html.escape(r["municipality"])} · {r["consensus_class"]}</title><circle class="dot" r="{radius:.3f}" fill="{color}" fill-opacity="{opacity:.4f}"/>')
        parts.append(f'<circle class="ring" r="{radius+1:.3f}" fill="none" stroke="{ring}" stroke-width="0.7"{dashed} opacity="0.65"/>')
        if r["stability_class"] == "expansive_core":
            parts.append(f'<circle r="{radius+2.4:.3f}" fill="none" stroke="{ring}" stroke-width="0.5" opacity="0.45"/>')
        parts.append('</g>')
    parts += ['</g><g id="anchors" font-family="Arial,sans-serif" fill="#263331">']
    for p, (x, y) in cfg["anchors"].items():
        parts += [f'<circle cx="{x}" cy="{y}" r="14" fill="{cfg["background"]}" stroke="{cfg["profiles"][p]}" stroke-width="2"/>', txt(x, y+5, p, 16, text_anchor="middle", font_weight="bold")]
    parts += [txt(500, 582, 'D · F · G: смешанная близость', 14, text_anchor="middle"),
              txt(90, 292, 'B · E', 14), txt(535, 611, 'F — базовый ориентир, не равноправное устойчивое ядро', 12, text_anchor="middle"), '</g>']
    if standalone:
        parts += ['<g font-family="Arial,sans-serif" fill="#364640">', txt(30, 30, 'Ландшафт устойчивости муниципального спроса', 22),
                  txt(30, 650, '1 904 точки · цвет: сводный профиль · ярче: больше разрыв близости', 15),
                  txt(30, 676, 'Полюса — схема, не география. Положение не заменяет проверку границы.', 14), '</g>']
    parts.append('</svg>')
    return ''.join(parts)


def figures(repo, destination, cfg, atlas):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    plt.rcParams.update({"svg.fonttype": "none", "svg.hashsalt": "public-visual-v1", "font.family": "DejaVu Sans", "font.size": 12,
                         "axes.spines.top": False, "axes.spines.right": False, "axes.facecolor": cfg["background"],
                         "figure.facecolor": cfg["background"], "text.color": cfg["ink"], "axes.labelcolor": cfg["ink"]})
    colors = cfg["profiles"]
    def save(fig, name):
        fig.savefig(destination / (name + '.svg'), bbox_inches="tight", metadata={"Date": None})
        svg_path = destination / (name + '.svg')
        svg_path.write_text(svg_path.read_text(encoding='utf-8').replace("'DejaVu Sans'", "'DejaVu Sans', Arial, sans-serif"), encoding='utf-8', newline='\n')
        plt.close(fig)
    matrix = pd.read_csv(repo / cfg["matrix"]).set_index("archetype")
    retention = float(matrix.loc["D", "perturbation_v2_mean_retention"])
    precision = float(matrix.loc["D", "perturbation_v2_mean_precision"])
    fig, ax = plt.subplots(figsize=(10, 5.3)); ax.set(xlim=(0, 10), ylim=(0, 5)); ax.set_aspect('equal'); ax.axis('off')
    ax.add_patch(Circle((3.0, 2.4), 1.65, fc=colors['D'], alpha=.12, ec=colors['D']))
    ax.add_patch(Circle((2.8, 2.4), 1.15, fc=colors['D'], alpha=.35, ec=colors['D']))
    ax.text(.25, 4.6, 'Сохранить ядро ≠ сохранить границу', fontsize=21, weight='bold')
    ax.text(5, 3.4, f'{retention:.1%} сохранения', fontsize=23, color=colors['D'])
    ax.text(5, 2.9, 'Сколько исходных участников осталось вместе?')
    ax.text(5, 2.0, f'{precision:.1%} точности', fontsize=23, color=colors['D'])
    ax.text(5, 1.5, 'Какая доля новой группы приходится на них?')
    ax.text(.25, .55, 'Профиль D · средние по 50 проверкам; схема окружностей не задаёт площади множеств.', fontsize=11)
    ax.text(.25, .15, 'Почти всё ядро может сохраниться внутри значительно более широкой группы.', fontsize=11)
    save(fig, 'core_vs_boundary')
    gradient = pd.read_csv(repo / cfg['gradient']).set_index('reference_profile')
    with np.load(repo / cfg['family_matrices']) as families:
        consensus = sum(families[name] for name in families.files) / len(families.files)
    pairs = {}
    for a, b in [('D', 'F'), ('F', 'G')]:
        pairs[a+b] = float(consensus[np.ix_(atlas.reference_profile.eq(a), atlas.reference_profile.eq(b))].mean())
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(10, 6), gridspec_kw={'height_ratios': [1, 2]})
    top.set(xlim=(-.5, 2.5), ylim=(-.5, .7)); top.axis('off')
    top.set_title('D–F–G: внутреннее окружение и внешнее наблюдение', loc='left', fontsize=19, pad=20)
    for i, pair in enumerate(['DF', 'FG']):
        top.plot([i, i+1], [0, 0], lw=3+25*pairs[pair], alpha=.22, color=colors['F'], solid_capstyle='round')
        top.text(i+.5, .25, f'совместное попадание {pairs[pair]:.1%}', ha='center', fontsize=10)
    for i, p in enumerate('DFG'):
        top.scatter(i, 0, s=700, c=colors[p]); top.text(i, 0, p, color='white', ha='center', va='center', weight='bold')
    wages = [float(gradient.loc[p, 'median']) / 1000 for p in 'DFG']
    bottom.plot(range(3), wages, color='#b4b9b3', lw=1)
    for i, p in enumerate('DFG'):
        bottom.scatter(i, wages[i], s=95, color=colors[p]); bottom.text(i+.05, wages[i]+1, f'{wages[i]:.1f} тыс. ₽', fontsize=13)
    bottom.set(xticks=[0, 1, 2], xticklabels=['D · n=2', 'F · n=1', 'G · n=3'], ylabel='Медианная зарплата, тыс. ₽', ylim=(50, 81), xlim=(-.4, 2.5))
    bottom.set_title('Республика Алтай, 2024 · ρ=0,926 · n=6', loc='left', fontsize=13)
    fig.text(.06, -.01, 'Маленькая региональная выборка, не универсальный закон. p=0,008; регрессия с ковариатами p=0,089.', fontsize=10)
    fig.text(.06, -.055, 'Линии не показывают историческое или причинное движение. Толщина сверху: средняя частота пары.', fontsize=10)
    fig.tight_layout(); save(fig, 'dfg_evidence_bridge')
    external = pd.read_csv(repo / cfg['external'])
    yak = external[(external.region == 'Республика Саха (Якутия)') & (external.reference_profile == 'A')]
    fig, ax = plt.subplots(figsize=(10, 6))
    area = 25 + 180 * np.sqrt(yak.population_2024 / yak.population_2024.max())
    ax.scatter(yak.investment_per_capita_2024, yak.salary_2024/1000, s=area, c=colors['A'], alpha=.65, edgecolors=colors['A'])
    ax.set_xscale('log'); ax.set_xlabel('Инвестиции на жителя, ₽ · логарифмическая шкала')
    ax.set_ylabel('Зарплата 2024, тыс. ₽ в месяц')
    ax.set_title('A в Якутии: зарплата и инвестиционная интенсивность', loc='left', fontsize=18, pad=20)
    extremes = sorted(set([yak.salary_2024.idxmin(), yak.salary_2024.idxmax(), yak.investment_per_capita_2024.idxmax()]))
    for j, idx in enumerate(extremes):
        r = yak.loc[idx]
        ax.annotate(r.municipality, (r.investment_per_capita_2024, r.salary_2024/1000), xytext=(-8, 12+j*5), textcoords='offset points', fontsize=9, ha='right')
    ax.margins(.25, .18); ax.grid(alpha=.15)
    fig.text(.06, .01, 'ρ=0,790598 · n=27. Размер точки растёт с √населения; это не доказательство независимости от размера.', fontsize=10)
    fig.text(.06, -.03, 'Номинальная зарплата работников, не доход всех жителей. Причинный и добывающий механизм не установлен.', fontsize=10)
    fig.tight_layout(rect=(0, .07, 1, 1)); save(fig, 'yakutia_A_external_validation')
    return {'D_retention': retention, 'D_precision': precision, 'internal_pairs': pairs, 'yakutia_n': len(yak)}


def build(repo=Path('.'), output=None, images=None):
    repo = Path(repo).resolve()
    config_path = repo / 'configs/public_visual_style.yaml'
    cfg = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    output = Path(output) if output else repo / cfg['output']
    images = Path(images) if images else repo / cfg['images']
    # Explicitly limited to visual destinations or caller-provided empty temp roots.
    protected = [(repo / p).resolve() for p in ['data', 'reference', 'outputs/baseline', 'outputs/stability_atlas_v2_2_1', 'outputs/round17_external_validation']]
    for destination in [output, images]:
        resolved = destination.resolve()
        allowed = [(repo / cfg['output']).resolve(), (repo / cfg['images']).resolve()]
        if resolved.is_relative_to(repo) and resolved not in allowed:
            raise ValueError('Only configured visual destinations are writable inside repository')
        if any(destination.resolve() == p or destination.resolve().is_relative_to(p) for p in protected):
            raise ValueError('Scientific paths are read-only')
        destination.mkdir(parents=True, exist_ok=True)
    paths = [cfg[k] for k in ['atlas', 'external', 'statistics', 'gradient', 'matrix', 'family_matrices']]
    inputs = {p: digest(repo / p) for p in paths}
    atlas = pd.read_csv(repo / cfg['atlas'])
    data = project(atlas, cfg)
    cells = field_grid(data, cfg)
    records = json.loads(data.to_json(orient='records', force_ascii=False, double_precision=15))
    payload = {'config': cfg, 'rows': records, 'fields': FIELDS, 'input_sha256': inputs,
               'f_counts': data[data.reference_profile.eq('F')].consensus_class.value_counts().to_dict()}
    svg = landscape_svg(data, cfg, cells)
    (images / 'stability_landscape_overview.svg').write_text(landscape_svg(data, cfg, cells, True), encoding='utf-8', newline='\n')
    stats = figures(repo, images, cfg, atlas)
    payload['summary'] = stats
    template = (repo / 'src/sbernet/visualization/landscape.html').read_text(encoding='utf-8')
    serialized = json.dumps(payload, ensure_ascii=False, allow_nan=False).replace('</', r'<\/')
    page = template.replace('__LANDSCAPE__', svg).replace('__DATA__', serialized)
    (output / 'index.html').write_text(page, encoding='utf-8', newline='\n')
    (output / 'data').mkdir(exist_ok=True)
    (output / 'assets').mkdir(exist_ok=True)
    (output / 'data/municipalities.json').write_text(serialized, encoding='utf-8', newline='\n')
    for p in images.glob('*.svg'):
        if p.stem in ['stability_landscape_overview', 'core_vs_boundary', 'dfg_evidence_bridge', 'yakutia_A_external_validation']:
            shutil.copyfile(p, output / 'assets' / p.name)
    meta = {'inputs_sha256': inputs, 'fields_used': FIELDS, 'external_fields': ['region', 'reference_profile', 'salary_2024', 'investment_per_capita_2024', 'population_2024'],
            'generation_script': 'scripts/build_public_visuals.py', 'config_sha256': digest(config_path),
            'source_sha256': {p.relative_to(repo).as_posix(): digest(p) for p in (repo/'src/sbernet/visualization').glob('*') if p.is_file()},
            'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
            'git_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo)),
            'coordinate_rule': 'sum original affinity_share * fixed anchor; no renormalization/jitter',
            'field_rule': 'local display-weighted mean of (entropy+1-margin)/2; masked below support; config fixed',
            'limitations': 'Projection is many-to-one; pole distances are not economic distances. No new clustering.', 'summary': stats}
    for name in ['stability_landscape', 'core_vs_boundary', 'dfg_evidence_bridge', 'yakutia_A_external_validation']:
        m = {**meta, 'visualization': name}
        (images / (name+'.meta.json')).write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
        (output / 'assets' / (name+'.meta.json')).write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    if inputs != {p: digest(repo / p) for p in paths}:
        raise ValueError('Scientific input changed during rendering')
    return {'municipalities': len(data), 'output': str(output), 'inputs_sha256': inputs}
