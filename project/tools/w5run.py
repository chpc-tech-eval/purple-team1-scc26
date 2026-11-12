#!/usr/bin/env python3
"""Week-5 exercise run tool: validate a run manifest, compute detection
metrics and merge evidence into one incident timeline (week5/README.md).

  w5run.py validate project/runs/<run-id>/manifest.yaml --stage plan|final
  w5run.py metrics  project/runs/<run-id>/manifest.yaml [-o metrics.json]
  w5run.py timeline evidence-a.csv evidence-b.csv -o timeline.csv [--md timeline.md]

Rules enforced (public repository):
- every timestamp is RFC3339 UTC ("...Z");
- only logical host names, never addresses: IPv4 outside the RFC 5737
  documentation ranges is refused, as is anything that looks like a secret;
- images are pinned by digest; the Git SHA is a full 40-hex commit;
- a run that never detected anything is still a valid result: metrics are
  then null and the false negative is recorded, not hidden.
"""
import argparse
import csv
import datetime as dt
import ipaddress
import json
import pathlib
import re
import sys

import yaml

SCHEMA = "scc26-week5-run/1"
ROLES = {"attacker", "defender"}
LAYERS = {"host", "network", "application", "platform"}
DOC_NETS = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]
IPV4 = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d{1,3}){3})(?:/\d{1,2})?(?!\w|\.\d)")
SECRET = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)\s*[=:]\s*\S"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\."),  # JWT
]
DIGEST = re.compile(r"^[a-z0-9.\-/:_]+@sha256:[0-9a-f]{64}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
LOGICAL = re.compile(r"^[a-z][a-z0-9-]{1,62}$")
TIMELINE_FIELDS = ["utc", "source", "layer", "evidence_id", "summary"]


class Invalid(Exception):
    pass


def parse_utc(value, field):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise Invalid(f"{field}: must be an RFC3339 UTC string ending in Z, got {value!r}")
    try:
        t = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Invalid(f"{field}: not RFC3339: {value!r}") from exc
    return t


def scan_public_safe(text, where):
    """Refuse real addresses and secret-looking strings anywhere in the text."""
    problems = []
    for m in IPV4.finditer(text):
        try:
            ip = ipaddress.ip_address(m.group(1))
        except ValueError:
            continue
        if not any(ip in n for n in DOC_NETS):
            problems.append(f"{where}: real IPv4 address found (use a logical name or RFC 5737 range)")
            break
    for p in SECRET:
        if p.search(text):
            problems.append(f"{where}: secret-looking value found")
            break
    return problems


def _blank(v):
    return v is None or v == "" or v == [] or v == {}


def validate(manifest, stage, raw_text=""):
    """Return a list of problems (empty = valid)."""
    errs = scan_public_safe(raw_text, "manifest") if raw_text else []
    m = manifest or {}
    if m.get("schema") != SCHEMA:
        errs.append(f"schema must be {SCHEMA}")
    if not re.fullmatch(r"\d{8}T\d{6}Z-w5-[a-z0-9-]+", str(m.get("run_id", ""))):
        errs.append("run_id must look like 20261107T090000Z-w5-<phase-name>")
    if m.get("team_role") not in ROLES:
        errs.append(f"team_role must be one of {sorted(ROLES)}")
    if _blank(m.get("scenario_id")):
        errs.append("scenario_id: the instructor-supplied ID is required (the ID only, never the secret text)")
    auth = m.get("authorisation") or {}
    if _blank(auth.get("roe_reference")):
        errs.append("authorisation.roe_reference is required: no exercise without acknowledged Rules of Engagement")
    frozen = m.get("frozen") or {}
    if not SHA.fullmatch(str(frozen.get("git_sha", ""))):
        errs.append("frozen.git_sha must be the full 40-hex accepted Week-4 commit")
    images = frozen.get("images") or {}
    if not images:
        errs.append("frozen.images: list the relevant image digests")
    for name, ref in images.items():
        if not DIGEST.fullmatch(str(ref)):
            errs.append(f"frozen.images.{name}: must be pinned as repo@sha256:<64 hex>")
    for side in ("sources", "targets"):
        names = (m.get("scope") or {}).get(side) or []
        if not names:
            errs.append(f"scope.{side}: at least one authorised logical name is required")
        for n in names:
            if not LOGICAL.fullmatch(str(n)):
                errs.append(f"scope.{side}: {n!r} is not a logical name (lowercase-dashed, no addresses)")
    ts = m.get("time_sync") or {}
    times = {}
    for key, value in (
        ("authorisation.acknowledged_utc", auth.get("acknowledged_utc")),
        ("time_sync.checked_utc", ts.get("checked_utc")),
        ("baseline.start_utc", (m.get("baseline") or {}).get("start_utc")),
        ("baseline.end_utc", (m.get("baseline") or {}).get("end_utc")),
        ("window.start_utc", (m.get("window") or {}).get("start_utc")),
    ):
        try:
            times[key] = parse_utc(value, key)
        except Invalid as exc:
            errs.append(str(exc))
    skew = ts.get("max_skew_seconds")
    if not isinstance(skew, (int, float)) or skew < 0:
        errs.append("time_sync.max_skew_seconds must be a non-negative number")
    elif skew > 1:
        errs.append(f"time_sync.max_skew_seconds={skew}: above 1 s the timeline is not defensible; fix NTP first")
    if "baseline.start_utc" in times and "baseline.end_utc" in times:
        minutes = (times["baseline.end_utc"] - times["baseline.start_utc"]).total_seconds() / 60
        if not 10 <= minutes <= 15:
            errs.append(f"baseline must cover 10-15 minutes of normal telemetry, got {minutes:.1f}")
        if "window.start_utc" in times and times["baseline.end_utc"] > times["window.start_utc"]:
            errs.append("baseline must end before the scenario window starts")
    if "authorisation.acknowledged_utc" in times and "window.start_utc" in times:
        if times["authorisation.acknowledged_utc"] > times["window.start_utc"]:
            errs.append("RoE acknowledgement must come before the scenario starts")
    layers = m.get("expected_layers") or []
    if not layers or not set(layers) <= LAYERS:
        errs.append(f"expected_layers must be a non-empty subset of {sorted(LAYERS)}")

    if stage == "final":
        try:
            end = parse_utc((m.get("window") or {}).get("end_utc"), "window.end_utc")
            if "window.start_utc" in times and end <= times["window.start_utc"]:
                errs.append("window.end_utc must be after window.start_utc")
        except Invalid as exc:
            errs.append(str(exc))
        evidence = m.get("evidence") or []
        if not evidence:
            errs.append("evidence: at least one retained evidence reference is required")
        ids = set()
        for i, e in enumerate(evidence):
            if _blank(e.get("id")) or e.get("id") in ids:
                errs.append(f"evidence[{i}].id missing or duplicated")
            ids.add(e.get("id"))
            if e.get("layer") not in LAYERS:
                errs.append(f"evidence[{i}].layer must be one of {sorted(LAYERS)}")
            if not re.fullmatch(r"[0-9a-f]{64}", str(e.get("sha256", ""))):
                errs.append(f"evidence[{i}].sha256 must be the SHA-256 of the retained file")
        for i, d in enumerate(m.get("detections") or []):
            try:
                parse_utc(d.get("utc"), f"detections[{i}].utc")
            except Invalid as exc:
                errs.append(str(exc))
            if d.get("evidence_id") not in ids:
                errs.append(f"detections[{i}].evidence_id must reference an evidence id")
        if not m.get("detections") and not (m.get("findings") or {}).get("false_negatives"):
            errs.append("no detections: record the miss under findings.false_negatives (a miss is a result, not a gap to hide)")
        for i, a in enumerate(m.get("acp") or []):
            if _blank(a.get("task_id")):
                errs.append(f"acp[{i}].task_id is required")
            if _blank(a.get("human_review")):
                errs.append(f"acp[{i}].human_review: a human must review and correct the explanation")
        if _blank(m.get("reset_replay")):
            errs.append("reset_replay: reference the reset/replay procedure used")
    return errs


def _delta(later, earlier, name):
    if _blank(later) or _blank(earlier):
        return None
    seconds = (parse_utc(later, name) - parse_utc(earlier, name)).total_seconds()
    if seconds < 0:
        raise Invalid(f"{name} is negative: milestones are out of order")
    return seconds


def metrics(manifest):
    w = manifest.get("window") or {}
    ms = manifest.get("milestones") or {}
    findings = manifest.get("findings") or {}
    return {
        "run_id": manifest.get("run_id"),
        "team_role": manifest.get("team_role"),
        "T_detect_s": _delta(ms.get("first_detection_utc"), w.get("start_utc"), "T_detect"),
        "T_identify_s": _delta(ms.get("identified_utc"), ms.get("first_detection_utc"), "T_identify"),
        "T_contain_s": _delta(ms.get("contained_utc"), ms.get("identified_utc"), "T_contain"),
        "T_recover_s": _delta(ms.get("recovered_utc"), ms.get("contained_utc") or ms.get("recovery_started_utc"), "T_recover"),
        "detections": len(manifest.get("detections") or []),
        "false_positives": len(findings.get("false_positives") or []),
        "false_negatives": len(findings.get("false_negatives") or []),
        "evidence_gaps": len(findings.get("gaps") or []),
        "note": "null = milestone not reached or not exercised; never imputed",
    }


def merge_timeline(paths):
    rows, seen = [], set()
    for path in paths:
        text = pathlib.Path(path).read_text(encoding="utf-8")
        problems = scan_public_safe(text, str(path))
        if problems:
            raise Invalid("; ".join(problems))
        reader = csv.DictReader(text.splitlines())
        if reader.fieldnames != TIMELINE_FIELDS:
            raise Invalid(f"{path}: header must be {','.join(TIMELINE_FIELDS)}")
        for n, row in enumerate(reader, start=2):
            parse_utc(row["utc"], f"{path}:{n}")
            if row["layer"] not in LAYERS:
                raise Invalid(f"{path}:{n}: layer must be one of {sorted(LAYERS)}")
            if not row["evidence_id"]:
                raise Invalid(f"{path}:{n}: every timeline row cites an evidence_id")
            key = tuple(row[f] for f in TIMELINE_FIELDS)
            if key not in seen:
                seen.add(key)
                rows.append(row)
    rows.sort(key=lambda r: (parse_utc(r["utc"], "utc"), r["source"], r["evidence_id"]))
    return rows


def _load(path):
    raw = pathlib.Path(path).read_text(encoding="utf-8")
    return yaml.safe_load(raw), raw


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("manifest")
    v.add_argument("--stage", choices=["plan", "final"], required=True)
    mt = sub.add_parser("metrics")
    mt.add_argument("manifest")
    mt.add_argument("-o", "--output")
    tl = sub.add_parser("timeline")
    tl.add_argument("inputs", nargs="+")
    tl.add_argument("-o", "--output", required=True)
    tl.add_argument("--md")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "validate":
            data, raw = _load(a.manifest)
            errs = validate(data, a.stage, raw)
            for e in errs:
                print(f"INVALID: {e}", file=sys.stderr)
            print(f"{a.manifest}: {'OK' if not errs else f'{len(errs)} problem(s)'} ({a.stage})")
            return 1 if errs else 0
        if a.cmd == "metrics":
            data, _ = _load(a.manifest)
            out = json.dumps(metrics(data), indent=2) + "\n"
            if a.output:
                pathlib.Path(a.output).write_text(out, encoding="utf-8")
            print(out, end="")
            return 0
        rows = merge_timeline(a.inputs)
        with open(a.output, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=TIMELINE_FIELDS, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        if a.md:
            lines = ["| UTC | Source | Layer | Evidence | Summary |", "| --- | --- | --- | --- | --- |"]
            lines += [
                f"| {r['utc']} | {r['source']} | {r['layer']} | `{r['evidence_id']}` | {r['summary'].replace('|', '/')} |"
                for r in rows
            ]
            pathlib.Path(a.md).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"{len(rows)} timeline rows -> {a.output}")
        return 0
    except Invalid as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
