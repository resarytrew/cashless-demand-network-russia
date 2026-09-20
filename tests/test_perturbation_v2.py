import json

import networkx as nx
import numpy as np
import pytest

from sbernet.config import load_config
from sbernet.robustness.perturbation_v2 import perturb, canonical_edges, EDGE_DTYPE, checkpoint_valid
from sbernet.robustness.experiment_common import profile_diagnostics, distribution
from sbernet.robustness.reproduction_gate import sha256, versions


def graph_fixture():
    graph = nx.Graph()
    graph.add_nodes_from(range(50))
    for i in range(20):
        for j in range(i + 1, 20):
            graph.add_edge(i, j, weight=(i + j + 1) / 100, kind='intralayer')
    for i in range(20):
        graph.add_edge(i, i + 20, weight=1.031, kind='temporal')
    return graph


def test_sorted_protocol_matches_explicit_rng_and_keeps_temporal_edges():
    settings = load_config('configs/perturbation_v2.yaml')['robustness']['perturbation']
    original = graph_fixture()
    result, hashes = perturb(original, 0, settings)
    base = canonical_edges(original, 'intralayer')
    assert EDGE_DTYPE.itemsize == 24
    rng = np.random.default_rng(20260918)
    mask = rng.random(len(base)) >= 0.05
    multiplier = np.exp(rng.normal(0, 0.02, mask.sum()))
    expected = base[mask].copy(); expected['weight'] *= multiplier
    assert np.array_equal(canonical_edges(result, 'intralayer'), expected)
    assert np.array_equal(canonical_edges(result, 'temporal'), canonical_edges(original, 'temporal'))
    assert set(result.nodes) == set(original.nodes)
    assert hashes['retained_intralayer_count'] == int(mask.sum())
    assert perturb(original, 0, settings)[1] == hashes
    assert perturb(original, 1, settings)[1]['final_supra_graph_sha256'] != hashes['final_supra_graph_sha256']


def test_reversed_node_and_edge_insertion_is_bitwise_identical():
    settings = load_config('configs/perturbation_v2.yaml')['robustness']['perturbation']
    original = graph_fixture()
    reverse = nx.Graph()
    reverse.add_nodes_from(reversed(list(original.nodes)))
    reverse.add_edges_from((v, u, dict(d)) for u, v, d in reversed(list(original.edges(data=True))))
    assert perturb(original, 0, settings)[1] == perturb(reverse, 0, settings)[1]


def test_unknown_edge_kind_rejected():
    original = graph_fixture()
    original.add_edge(40, 41, weight=1)
    with pytest.raises(ValueError, match='explicit kind'):
        perturb(original, 0, {})


def test_profile_diagnostics_distinguish_retention_from_merged_boundary():
    profiles, pairs = profile_diagnostics(np.array([0, 0, 1, 1]), np.array([9, 9, 9, 9]), {'A': 0, 'B': 1})
    assert all(r['retention'] == 1 and r['precision'] == 0.5 and r['Jaccard'] == 0.5 for r in profiles)
    assert all(r['within_pair_coassignment'] == 1 for r in profiles)
    assert pairs == [{'pair': 'A/B', 'cross_coassignment': 1.0}]


def test_distribution_schema_and_sample_sd():
    result = distribution([0, 1, 2], [0.05, 0.1, 0.25, 0.75, 0.9, 0.95])
    assert set(result) == {'n', 'mean', 'median', 'SD', 'min', 'max', 'q05', 'q10', 'q25', 'q75', 'q90', 'q95'}
    assert result['SD'] == 1.0
    assert result['q10'] == 0.2


def test_checkpoint_does_not_accept_partial_or_different_config(tmp_path):
    assert not checkpoint_valid(tmp_path, 'expected')
    (tmp_path / 'COMPLETED.json').write_text(json.dumps({'config_sha256': 'wrong'}))
    with pytest.raises(ValueError, match='mismatch'):
        checkpoint_valid(tmp_path, 'expected')


def test_checkpoint_detects_corrupt_raw_result(tmp_path):
    result = tmp_path / 'raw_results.json'
    result.write_text('{"seed": 0}')
    checkpoint = {'config_sha256': 'expected', 'packages': versions(),
                  'files_sha256': {'raw_results.json': sha256(result)}}
    (tmp_path / 'COMPLETED.json').write_text(json.dumps(checkpoint))
    assert checkpoint_valid(tmp_path, 'expected')
    result.write_text('{"seed": 1}')
    with pytest.raises(ValueError, match='integrity mismatch'):
        checkpoint_valid(tmp_path, 'expected')
