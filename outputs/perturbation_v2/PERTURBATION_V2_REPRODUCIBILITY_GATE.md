# Perturbation v2 reproducibility gate

Status: PASS.

Seed 0: two calls in the same process, one fresh Python process, and one reversed node/edge insertion order. All saved hashes and counts are compared exactly, without numerical tolerance. No historical pilot CSV comparisons are used.

```json
{
  "passed": true,
  "same_process_equal": true,
  "fresh_process_equal": true,
  "reversed_insertion_equal": true,
  "config_sha256": "70df833cc1d83ed1b30ca7596ed6fe1f22613be7ddcbf00f9804639de9b8fe6e",
  "packages": {
    "python": "3.13.6 (tags/v3.13.6:4e66535, Aug  6 2025, 14:36:00) [MSC v.1944 64 bit (AMD64)]",
    "executable": "C:\\Python313\\python.exe",
    "numpy": "2.4.4",
    "pandas": "2.3.3",
    "scipy": "1.16.3",
    "scikit-learn": "1.7.2",
    "networkx": "3.6.1",
    "PyYAML": "6.0.3",
    "igraph": "1.0.0",
    "leidenalg": "0.12.0"
  },
  "hashes": {
    "seed": 0,
    "canonical_base_edge_sha256": "132d7a6b7c163ea04d69bc93df184b89b97e9d46495939d582b679cf227e9087",
    "keep_mask_sha256": "8224e97d4ee094542544154fef05f134f23443b61d8e886887536226442af7d8",
    "jitter_array_sha256": "a452718cea693d40cca8e3eb1d29cb7195c4eae392e4c245f5d0da62163447dd",
    "perturbed_intralayer_edge_sha256": "e04e53f8fa3298011b685b24956b4a9dcac421e5fa659921e3b5eb298ee6c815",
    "temporal_edge_sha256": "a4970bcc696bae2fa02cbfbffe182a9908f3d72a974b2a29ab7b8f07bac03de1",
    "final_supra_edge_weight_sha256": "53a39ea0c2cf79ae610e09f3a1bdbb1c31b73d56a05be1f83780003040b5f376",
    "final_supra_graph_sha256": "0f3123225470c4689de1a79828a11f1cdd59eef612e6c99d61c5f6a47709a4b3",
    "node_count": 45696,
    "base_intralayer_count": 283120,
    "retained_intralayer_count": 268717,
    "temporal_edge_count": 43792,
    "edge_count": 312509
  }
}
```

The gate verifies perturbation graph determinism; Louvain uses the run seed separately.
