#!/usr/bin/env bash
# RUN ON: k8s-cp-01. Bounded, read-only Prometheus export for one window
# (operational context for the Week-5 timeline). Fixed queries only.
#
#   bash prom_export.sh <run-id> <label> <start_utc> <end_utc>
#
# Output stays on the control plane under ~/scc26-evidence/<run-id>/<label>/
# (never deleted); the per-query JSON has no addresses (aggregated by namespace).
set -euo pipefail

run_id=${1:?run-id}
label=${2:?label}
start=${3:?start_utc}
end=${4:?end_utc}
[[ "$run_id" =~ ^[0-9]{8}T[0-9]{6}Z-w5-[a-z0-9-]+$ ]] || { echo "bad run-id" >&2; exit 2; }
[[ "$label" =~ ^(baseline|scenario|replay)[a-z0-9-]*$ ]] || { echo "bad label" >&2; exit 2; }
span=$(( $(date -ud "$end" +%s) - $(date -ud "$start" +%s) ))
(( span > 0 && span <= 14400 )) || { echo "window must be 1 s - 4 h" >&2; exit 2; }

out=$HOME/scc26-evidence/$run_id/$label
if [[ -e "$out" ]]; then echo "$out exists: never overwritten; use a new label" >&2; exit 3; fi
mkdir -p "$out"

declare -A Q=(
  [pod_restarts]='sum by (namespace) (increase(kube_pod_container_status_restarts_total[5m]))'
  [pods_not_ready]='sum by (namespace) (kube_pod_status_ready{condition="false"})'
  [cpu_by_namespace]='sum by (namespace) (rate(container_cpu_usage_seconds_total{container!=""}[5m]))'
  [net_rx_by_namespace]='sum by (namespace) (rate(container_network_receive_bytes_total[5m]))'
  [node_load1]='avg(node_load1)'
)
pod=$(kubectl -n monitoring get pods -l app.kubernetes.io/name=prometheus -o jsonpath='{.items[0].metadata.name}')
for name in "${!Q[@]}"; do
  kubectl -n monitoring exec "$pod" -c prometheus -- wget -qO- \
    "http://127.0.0.1:9090/api/v1/query_range?start=$start&end=$end&step=30s&query=$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "${Q[$name]}")" \
    > "$out/prom-$name.json"
  printf '%s %s\n' "$name" "$(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print(d["status"], len(d["data"]["result"]), "series")' "$out/prom-$name.json")"
done
(cd "$out" && sha256sum prom-*.json > SHA256SUMS && chmod 0440 prom-*.json SHA256SUMS)
echo "kept on server: $out"
