# Run manifests (provenance)

One JSON file per significant experiment, demo or security drill, following [`docs/EXPERIMENT-PROVENANCE.md`](../../docs/EXPERIMENT-PROVENANCE.md) (schema 1.0). Files are named `<started_at>-<experiment>.json`.

Write them with [`scripts/provenance/write_manifest.py`](../../scripts/provenance/write_manifest.py), never by dumping the environment. The writer:

- takes every field from an explicit argument or from git (an **allowlist**); it never reads the process environment;
- refuses values that look like keys, tokens, passwords or private addresses;
- accepts only immutable image references (`@sha256:` digest or `sha-<commit>` tag);
- records the Git commit and whether the working tree was dirty (or a given merged commit);
- hashes artifacts with SHA-256;
- requires a `--failure-type` for failed runs, because a failed run is a valid result and is kept.

Manifests are never deleted (team rule: everything stays).

| Run | Manifest |
| --- | --- |
| Week-2 Part G: Git change reconciled by Argo CD (#61) | [`20261016T232050Z-week2-part-g-gitops-reconciliation.json`](20261016T232050Z-week2-part-g-gitops-reconciliation.json) |
