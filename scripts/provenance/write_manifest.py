#!/usr/bin/env python3
"""Write one run manifest (docs/EXPERIMENT-PROVENANCE.md, schema 1.0).

Allowlist only: every field comes from an explicit argument or from git. The
process environment is never read, so tokens, keys, kubeconfigs and passwords
cannot leak into a manifest. Values that look like secrets are refused.

Example:
  scripts/provenance/write_manifest.py \
    --experiment "week2-part-g-reconciliation" --status completed \
    --started 2026-10-16T23:20:50Z --finished 2026-10-16T23:25:31Z \
    --location sebowa-kubernetes --namespace ingress-test \
    --image whoami=docker.io/traefik/whoami@sha256:80f8... \
    --param replicas_before=1 --param replicas_after=2 \
    --metric reconcile_seconds=281 --notes "PR #61"
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import uuid

PROJECT = "purple-team1-scc26"
REPO_URL = "https://github.com/chpc-tech-eval/purple-team1-scc26"
LOCATIONS = {"sebowa-kubernetes", "a100", "h200", "other-approved-target"}
STATUSES = {"running", "completed", "failed"}
# Refuse anything that looks like a credential or a private address.
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key)\s*[=:]"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(10|172\.(1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}(/\d+)?\b"),
]


def rfc3339(value: str) -> str:
    try:
        t = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not RFC3339: {value}") from exc
    if t.tzinfo is None:
        raise argparse.ArgumentTypeError(f"timestamp needs a timezone (use Z for UTC): {value}")
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def kv(value: str) -> tuple:
    if "=" not in value:
        raise argparse.ArgumentTypeError(f"expected key=value, got {value}")
    k, v = value.split("=", 1)
    if not re.fullmatch(r"[a-z][a-z0-9_]*", k):
        raise argparse.ArgumentTypeError(f"key must be snake_case: {k}")
    return k, v


def git(*args: str, cwd: pathlib.Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def number(v: str):
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def check_clean(obj, path="manifest"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            check_clean(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check_clean(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        for pat in SECRET_PATTERNS:
            if pat.search(obj):
                sys.exit(f"refused: {path} looks like a secret or a private address; keep it out of provenance")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--status", required=True, choices=sorted(STATUSES))
    ap.add_argument("--started", required=True, type=rfc3339)
    ap.add_argument("--finished", type=rfc3339)
    ap.add_argument("--location", required=True, choices=sorted(LOCATIONS))
    ap.add_argument("--host-class", default="")
    ap.add_argument("--namespace", default="")
    ap.add_argument("--commit", help="record this commit instead of the working tree HEAD (for a run on a merged commit)")
    ap.add_argument("--image", action="append", default=[], type=kv, help="name=immutable-ref (digest or sha- tag)")
    ap.add_argument("--resource", action="append", default=[], type=kv, help="requested resource, key=value")
    ap.add_argument("--param", action="append", default=[], type=kv)
    ap.add_argument("--metric", action="append", default=[], type=kv)
    ap.add_argument("--artifact", action="append", default=[], help="file to hash (sha256) and reference")
    ap.add_argument("--failure-type", default="")
    ap.add_argument("--notes", default="")
    ap.add_argument("--out-dir", default="evidence/runs")
    a = ap.parse_args()

    repo = pathlib.Path(git("rev-parse", "--show-toplevel", cwd=pathlib.Path.cwd()))
    if a.commit:
        commit = git("rev-parse", "--verify", f"{a.commit}^{{commit}}", cwd=repo)
        dirty = False  # a recorded commit is immutable
    else:
        commit = git("rev-parse", "HEAD", cwd=repo)
        dirty = bool(git("status", "--porcelain", "--untracked-files=no", cwd=repo))
    if a.status != "running" and not a.finished:
        sys.exit("--finished is required unless --status running")
    if a.status == "failed" and not a.failure_type:
        sys.exit("--failure-type is required for a failed run (failure is a valid result: record why)")
    for name, ref in a.image:
        if "@sha256:" not in ref and not re.search(r":sha-[0-9a-f]{7,40}$", ref):
            sys.exit(f"image {name}: use an immutable digest or sha-<commit> tag, not {ref}")

    artifacts = []
    for f in a.artifact:
        p = (pathlib.Path.cwd() / f).resolve()
        artifacts.append({"path": str(p.relative_to(repo)).replace("\\", "/"),
                          "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})

    manifest = {
        "schema_version": "1.0",
        "run_id": str(uuid.uuid4()),
        "project": PROJECT,
        "experiment": a.experiment,
        "status": a.status,
        "started_at": a.started,
        "finished_at": a.finished,
        "source": {"repository": REPO_URL, "commit": commit, "dirty": dirty},
        "software": {"images": [{"name": n, "ref": r} for n, r in a.image]},
        "execution": {"location": a.location, "host_class": a.host_class, "namespace": a.namespace,
                      "requested_resources": {k: number(v) for k, v in a.resource}},
        "parameters": {k: number(v) for k, v in a.param},
        "metrics": {k: number(v) for k, v in a.metric},
        "artifacts": artifacts,
        "notes": a.notes,
    }
    if a.status == "failed":
        manifest["failure"] = {"type": a.failure_type}
    check_clean(manifest)

    out = repo / a.out_dir
    out.mkdir(parents=True, exist_ok=True)
    stamp = a.started.replace(":", "").replace("-", "")
    path = out / f"{stamp}-{re.sub(r'[^a-z0-9]+', '-', a.experiment.lower()).strip('-')}.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(path.relative_to(repo))


if __name__ == "__main__":
    main()
