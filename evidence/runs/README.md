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
| Week-2 Part E: persistence re-test on the restored storage-test app (#70) | [`20261018T183913Z-week2-part-e-persistence-retest.json`](20261018T183913Z-week2-part-e-persistence-retest.json) |
| Week-3 Part C: PostgreSQL row survives DB pod replacement (#66) | [`20261018T190314Z-week3-part-c-postgres-persistence.json`](20261018T190314Z-week3-part-c-postgres-persistence.json) |
| Week-3 Part B: security drill, SSH → Wazuh 5710, Suricata → Wazuh 86601 (#75, #76) | [`20261025T174432Z-week3-part-b-security-drill.json`](20261025T174432Z-week3-part-b-security-drill.json) |
| Week-3 Part C: platform browser path, auth and data persistence (#66) | [`20261101T112300Z-week3-part-c-platform-e2e.json`](20261101T112300Z-week3-part-c-platform-e2e.json) |
| Week-3 Part C: platform v2 (forced password change, throttling, 0 restarts on DB replacement) (#84, #85) | [`20261101T123000Z-week3-part-c-platform-v2-verify.json`](20261101T123000Z-week3-part-c-platform-v2-verify.json) |
| Week-3 close-out: fresh drill through the whole chain (Suricata → Wazuh → Filebeat → indexer/dashboard) with platform health, after #87–#91 | [`20261101T193548Z-week3-closeout-full-chain-drill.json`](20261101T193548Z-week3-closeout-full-chain-drill.json) |
