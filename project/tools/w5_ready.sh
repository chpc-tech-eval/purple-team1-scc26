#!/usr/bin/env bash
# RUN ON: laptop (VPN up, SSH aliases for the hosts). Read-only Week-5 readiness
# check (docs/week5-runbook.md, steps 2-4): time sync on every evidence host,
# the edge sensors, and Argo CD. Changes nothing on any host.
#
#   bash project/tools/w5_ready.sh            # all evidence hosts
#   W5_HOSTS="edge-01 k8s-cp-01" bash project/tools/w5_ready.sh
#
# Prints one line per check (ok / WARN / FAIL), then the value for
# time_sync.max_skew_seconds in the run manifest. Exit 0 = ready, 1 = a FAIL.
# Output has host names and counts only (no addresses), so it is safe to paste.
set -uo pipefail

hosts=${W5_HOSTS:-"edge-01 k8s-cp-01 k8s-worker-01 k8s-worker-02 api-lb-01"}
edge=${W5_EDGE:-edge-01}
cp=${W5_CP:-k8s-cp-01}
max_skew=${W5_MAX_SKEW:-1}
ssh_opts=(-o BatchMode=yes -o ConnectTimeout=10)

fails=0
worst=0
say() {  # status host check detail
  printf '%-5s %-14s %-22s %s\n' "$1" "$2" "$3" "$4"
  [[ "$1" == FAIL ]] && fails=$((fails + 1))
  return 0
}

echo "Week-5 readiness  $(date -u +%Y-%m-%dT%H:%M:%SZ)  (max skew ${max_skew}s)"

# --- 1. time sync on every evidence host (runbook step 3) -------------------
for h in $hosts; do
  out=$(ssh "${ssh_opts[@]}" "$h" bash -s 2>/dev/null <<'EOF'
echo "ntp=$(timedatectl show -p NTPSynchronized --value 2>/dev/null)"
chronyc -n tracking 2>/dev/null | awk -F': *' '
  /^System time/ {split($2, a, " "); print "offset=" a[1]}
  /^Leap status/ {print "leap=" $2}'
for s in wazuh-agent wazuh-manager; do
  [ "$(systemctl is-active "$s" 2>/dev/null)" = active ] && echo "wazuh=$s"
done
exit 0
EOF
  ) || { say FAIL "$h" ssh "unreachable (VPN up? key loaded?)"; continue; }
  ntp=$(sed -n 's/^ntp=//p' <<<"$out")
  offset=$(sed -n 's/^offset=//p' <<<"$out")
  leap=$(sed -n 's/^leap=//p' <<<"$out")
  wz=$(sed -n 's/^wazuh=//p' <<<"$out" | head -1)

  [[ "$ntp" == yes ]] && say ok "$h" ntp-synchronised yes || say FAIL "$h" ntp-synchronised "${ntp:-unknown} (timedatectl)"
  if [[ -n "$offset" ]]; then
    worst=$(awk -v a="$worst" -v b="$offset" 'BEGIN {print (b > a) ? b : a}')
    if awk -v o="$offset" -v m="$max_skew" 'BEGIN {exit !(o <= m)}'; then
      say ok "$h" clock-offset "${offset}s (leap: ${leap:-?})"
    else
      say FAIL "$h" clock-offset "${offset}s > ${max_skew}s: fix NTP before the run"
    fi
  else
    say FAIL "$h" clock-offset "chronyc tracking gave no offset"
  fi
  [[ -n "$wz" ]] && say ok "$h" wazuh "$wz active" || say FAIL "$h" wazuh "no wazuh agent/manager running"
done

# --- 2. edge sensors (Suricata, Wazuh manager, evidence prerequisites) -------
out=$(ssh "${ssh_opts[@]}" "$edge" bash -s 2>/dev/null <<'EOF'
echo "suricata=$(systemctl is-active suricata 2>/dev/null)"
age=$(sudo -n stat -c %Y /var/log/suricata/eve.json 2>/dev/null) && echo "eve_age=$(( $(date +%s) - age ))"
echo "sids=$(sudo -n grep -ohE 'sid:90000(0[1-9]|1[0-9]);' /var/lib/suricata/rules/suricata.rules 2>/dev/null | sort -u | wc -l)"
echo "bg_rule=$(sudo -n grep -c 'rule id="100110"' /var/ossec/etc/rules/scc26_rules.xml 2>/dev/null)"
echo "agents=$(sudo -n /var/ossec/bin/agent_control -l 2>/dev/null | grep -c ', Active')"
sudo -n test -s /root/hostmap.csv && echo "hostmap=yes" || echo "hostmap=no"
sudo -n true 2>/dev/null && echo "sudo=yes" || echo "sudo=no"
EOF
) || { say FAIL "$edge" ssh unreachable; out=""; }
if [[ -n "$out" ]]; then
  v() { sed -n "s/^$1=//p" <<<"$out"; }
  [[ "$(v sudo)" == yes ]] || say WARN "$edge" sudo "no passwordless sudo: root-only checks skipped"
  [[ "$(v suricata)" == active ]] && say ok "$edge" suricata active || say FAIL "$edge" suricata "$(v suricata)"
  age=$(v eve_age)
  if [[ -z "$age" ]]; then say WARN "$edge" eve.json "age unknown"
  elif (( age <= 120 )); then say ok "$edge" eve.json "written ${age}s ago"
  else say FAIL "$edge" eve.json "last write ${age}s ago: Suricata is not logging"; fi
  [[ "$(v sids)" == 7 ]] && say ok "$edge" team-sids "7/7 in the loaded ruleset" || say FAIL "$edge" team-sids "$(v sids)/7 in the loaded ruleset"
  [[ "$(v bg_rule)" -ge 1 ]] 2>/dev/null && say ok "$edge" break-glass-rule "100110 deployed" || say WARN "$edge" break-glass-rule "100110 not deployed yet"
  # agent_control lists the manager itself as 000 (Active/Local), so every host counts.
  n=$(v agents); expected=$(wc -w <<<"$hosts")
  (( ${n:-0} >= expected )) && say ok "$edge" wazuh-agents "$n active" || say FAIL "$edge" wazuh-agents "${n:-0} active, expected >= $expected"
  [[ "$(v hostmap)" == yes ]] && say ok "$edge" hostmap "/root/hostmap.csv present" || say FAIL "$edge" hostmap "/root/hostmap.csv missing (edge_export.sh needs it)"
fi

# --- 3. Argo CD: everything Synced/Healthy (runbook step 2) ------------------
out=$(ssh "${ssh_opts[@]}" "$cp" bash -s 2>/dev/null <<'EOF'
kubectl -n argocd get applications -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.status.sync.status}{" "}{.status.health.status}{" "}{.status.sync.revision}{"\n"}{end}' 2>/dev/null
EOF
) || out=""
if [[ -z "$out" ]]; then
  say FAIL "$cp" argocd "could not list applications (kubeconfig on $cp?)"
else
  revs=$(awk '$4 != "" {print substr($4, 1, 7)}' <<<"$out" | sort -u | tr '\n' ' ')
  bad=$(awk '$2 != "Synced" || $3 != "Healthy" {printf "%s(%s/%s) ", $1, $2, $3}' <<<"$out")
  total=$(wc -l <<<"$out")
  [[ -z "$bad" ]] && say ok "$cp" argocd "$total/$total Synced/Healthy at ${revs% }" || say FAIL "$cp" argocd "not ready: ${bad% }"
fi

# --- summary --------------------------------------------------------------
echo
echo "time_sync.max_skew_seconds: $worst"
if (( fails == 0 )); then echo "READY"; exit 0; fi
echo "NOT READY: $fails check(s) failed"; exit 1
