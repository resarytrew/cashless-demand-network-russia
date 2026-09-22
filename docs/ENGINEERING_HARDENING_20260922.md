# Engineering provenance and Atlas hardening — 2026-09-22

Scope: engineering and presentation, no new scientific evidence round, no change
to reference parameters or A–G statuses. Base: b5c365057e991580893da72420fe854a5dd060aa.

## Freeze mismatch diagnosis

Commit 48299d106f2dfe4e0cad57fb0e07fefbfe4b9070 changed only one import in
`scripts/build_competition_artifacts.py`, from `round16_common` to
`scripts.round16_common`. The imported helper implementations and calculations
are unchanged. An exact text-difference test and helper identity assertions check
this limited claim. The original bytes were recovered from 5c461cc and matched
the existing Round16 SHA256 inventory before preservation.

Original evidence outputs, inventory, manifest and checksums remain unchanged.
`reference/engineering_20260922/source_transitions.json` explicitly records the
historical/current hashes, snapshots and reasons for this import correction and
current-state documentation edits. Historical source bytes are checked against
the original inventory; current bytes against a separate engineering manifest.
No arbitrary mismatch fallback is permitted, and outputs/data cannot be redirected.

The existing Round16 verifier is retained unchanged for its historical checkout.
The current entrypoint, `scripts/verify_current_artifacts.py`, first authenticates
the original/current provenance chain and then executes the same numerical
replay with historical integrity handled by the explicit snapshot registry. Main CI uses this entrypoint and builds/checks the current Atlas as well.

## Atlas contract

An explicit YAML specifies inputs, reference month, equal family weights, anchors,
voting and threshold rules. Registered input bytes inherit the gated municipality
order/calendar; CSV alignment is by unique key and named month. Saved inputs are
checked before output creation and again before completion. A manifest records
code, config, runtime, Git state and input axes. Atomic completion and exact file
hash checks protect resume. Force archives only managed output directories.

For the registered 1904 cases, no zero-affinity rows were present in the review.
The corrected zero-affinity behavior therefore fixes a latent edge case without
changing the recorded numerical conclusions. Tests cover missing/reordered input,
calendar/registry mismatch, corrupt output, resume without mutation, protected
directories, explicit archival and zero/invalid affinities.

An offline HTML viewer, CSV dictionary and persisted Atlas artifact provide a
publicly inspectable derivative. They keep contextual limitations visible and
separate family-vote direction from LOFO balance sign. Positive ties remain
deterministic and have zero margin; micro-community affinities are descriptive.

## Scientific scope and remaining work

`docs/CURRENT_STATE.json` distinguishes evidence v2.3.0 from Atlas v2.2.1. Historical
context is preserved with an explicit current override and immutable snapshots.
Geographic/metropolitan language unsupported by available joins has been qualified.
No C status promotion or seven-equally-robust-profile interpretation is introduced.

Metadata and historical contextual inputs remain unavailable. See
`DATA_METADATA_REQUEST.md`. New weight sensitivity, added algorithm seeds or
prospective utility experiments remain separate research tasks requiring explicit
protocols, baseline gates, raw results and a new evidence round. They are not
implicitly claimed by the engineering verification. No remote publication or
license decision is part of this local implementation.

Verification results are recorded in `outputs/engineering_20260922/verification.json`.
