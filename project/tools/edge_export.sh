#!/usr/bin/env bash
# RUN ON: edge-01 (sudo). Bounded, read-only export of Suricata + Wazuh evidence
# for one time window (baseline or scenario). Week 5, steps 4 and 8.
#
#   sudo bash edge_export.sh <run-id> <label> <start_utc> <end_utc> [hostmap.csv]
#   e.g. sudo bash edge_export.sh 20261110T090000Z-w5-phase1-defend scenario \
#          2026-11-10T09:00:00Z 2026-11-10T09:40:00Z /root/hostmap.csv
#
# Raw copies stay on the server (/var/lib/scc26-evidence/<run-id>/<label>/, never
# deleted, never committed: they contain addresses). Git gets only the sanitised
# outputs: summary.json, timeline.csv (addresses replaced via hostmap.csv
# "address,logical-name", else "<addr>") and SHA256SUMS of the raw files.
set -euo pipefail

run_id=${1:?run-id}
label=${2:?label (baseline|scenario|replay)}
start=${3:?start_utc}
end=${4:?end_utc}
hostmap=${5:-}

[[ "$run_id" =~ ^[0-9]{8}T[0-9]{6}Z-w5-[a-z0-9-]+$ ]] || { echo "bad run-id" >&2; exit 2; }
[[ "$label" =~ ^(baseline|scenario|replay)[a-z0-9-]*$ ]] || { echo "bad label" >&2; exit 2; }
for t in "$start" "$end"; do
  [[ "$t" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] || { echo "timestamps must be UTC ...Z" >&2; exit 2; }
done
span=$(( $(date -ud "$end" +%s) - $(date -ud "$start" +%s) ))
(( span > 0 && span <= 14400 )) || { echo "window must be 1 s - 4 h (bounded export)" >&2; exit 2; }

out=/var/lib/scc26-evidence/$run_id/$label
if [[ -e "$out" ]]; then echo "$out exists: evidence is never overwritten; use a new label" >&2; exit 3; fi
install -d -m 0750 "$out"

# Include rotated files that can overlap the window.
eve_files=$(find /var/log/suricata -maxdepth 1 -name 'eve.json*' -newermt "$start" 2>/dev/null | sort || true)
waz_files=$(find /var/ossec/logs/alerts -maxdepth 4 -name 'alerts.json*' -newermt "$start" 2>/dev/null | sort || true)

python3 - "$start" "$end" "$out" "$hostmap" "$run_id" "$label" "$eve_files" "$waz_files" <<'PY'
import collections, csv, datetime as dt, gzip, hashlib, ipaddress, json, os, re, sys

start, end, out, hostmap, run_id, label, eve_files, waz_files = sys.argv[1:9]
utc = lambda s: dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
lo, hi = utc(start), utc(end)
names = {}
if hostmap:
    with open(hostmap, encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if len(row) == 2 and not row[0].startswith("#"):
                names[row[0].strip()] = row[1].strip()
ip_re = re.compile(r"(?<![\w.])\d{1,3}(?:\.\d{1,3}){3}(?!\w|\.\d)")
def clean(text):
    def sub(m):
        try:
            ipaddress.ip_address(m.group(0))
        except ValueError:
            return m.group(0)
        return names.get(m.group(0), "<addr>")
    return ip_re.sub(sub, str(text)).replace(",", ";")

def ts(rec):
    t = rec.get("timestamp", "")
    t = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", t)
    try:
        return dt.datetime.fromisoformat(t).astimezone(dt.timezone.utc)
    except ValueError:
        return None

def records(paths):
    for p in [x for x in paths.split("\n") if x]:
        opener = gzip.open if p.endswith(".gz") else open
        with opener(p, "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                t = ts(r)
                if t and lo <= t < hi:
                    yield t, line, r

timeline, summary = [], {"run_id": run_id, "label": label, "start_utc": start, "end_utc": end}
eve_types, sigs = collections.Counter(), collections.Counter()
with open(os.path.join(out, "suricata-eve.json"), "w", encoding="utf-8") as raw:
    for t, line, r in records(eve_files):
        raw.write(line)
        eve_types[r.get("event_type")] += 1
        if r.get("event_type") == "alert":
            a = r.get("alert", {})
            sigs[f'{a.get("signature_id")} {a.get("signature")}'] += 1
            timeline.append([t.strftime("%Y-%m-%dT%H:%M:%SZ"), "suricata", "network",
                             f"{run_id}/{label}/suricata-eve.json#flow_id={r.get('flow_id')}",
                             clean(f'sid {a.get("signature_id")} {a.get("signature")} {r.get("src_ip")}->{r.get("dest_ip")}:{r.get("dest_port")}')])
rules, agents = collections.Counter(), collections.Counter()
with open(os.path.join(out, "wazuh-alerts.json"), "w", encoding="utf-8") as raw:
    for t, line, r in records(waz_files):
        raw.write(line)
        rule = r.get("rule", {})
        rules[f'{rule.get("id")} L{rule.get("level")} {rule.get("description")}'] += 1
        agents[r.get("agent", {}).get("name")] += 1
        if int(rule.get("level", 0)) >= 5:
            timeline.append([t.strftime("%Y-%m-%dT%H:%M:%SZ"), "wazuh", "host",
                             f"{run_id}/{label}/wazuh-alerts.json#id={r.get('id')}",
                             clean(f'rule {rule.get("id")} L{rule.get("level")} {rule.get("description")} on {r.get("agent", {}).get("name")}')])
summary.update({
    "suricata_event_types": dict(eve_types),
    "suricata_alert_signatures": {clean(k): v for k, v in sigs.most_common(25)},
    "wazuh_rules": {clean(k): v for k, v in rules.most_common(25)},
    "wazuh_alerts_by_agent": dict(agents),
    "timeline_rows": len(timeline),
    "note": "raw files stay on edge-01; addresses replaced in this summary and the timeline",
})
timeline.sort()
with open(os.path.join(out, "timeline.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["utc", "source", "layer", "evidence_id", "summary"])
    w.writerows(timeline)
with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)
    fh.write("\n")
with open(os.path.join(out, "SHA256SUMS"), "w", encoding="utf-8") as fh:
    for name in ("suricata-eve.json", "wazuh-alerts.json"):
        with open(os.path.join(out, name), "rb") as f:
            fh.write(f"{hashlib.sha256(f.read()).hexdigest()}  {name}\n")
print(json.dumps({k: summary[k] for k in ("label", "start_utc", "end_utc", "suricata_event_types", "timeline_rows")}))
PY
chmod 0440 "$out"/*.json "$out"/SHA256SUMS "$out"/timeline.csv
echo "kept on server: $out"
cat "$out/SHA256SUMS"
