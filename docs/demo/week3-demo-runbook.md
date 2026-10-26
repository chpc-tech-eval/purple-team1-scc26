# Demo: Week-3 runbook (observability, security telemetry, Student Platform)

About 40 minutes, two presenters. Every command is read-only unless marked. Evidence index: [`evidence/week3/README.md`](../../evidence/week3/README.md); diagram: [`evidence/week3/diagrams/`](../../evidence/week3/diagrams/README.md); problems we hit: [`evidence/week3/troubleshooting.md`](../../evidence/week3/troubleshooting.md).

## Before you share your screen

- VPN up; log in as **yourself** (`ssh <name>@<host>`), not `rocky`.
- **Never show** tfvars, the private inventory, `~/.config/scc26-secrets/`, kubeconfigs, Grafana or platform passwords, or `kubectl get secret -o yaml`. Use host names, not addresses.
- Read times from the **server** clock (`date -u` on edge-01); it is NTP-synced.

## 1. The three questions (Phathutshedzo, ~3 min)

Prometheus/Grafana → *is the platform healthy?* · Wazuh → *what host/security events happened?* · Suricata → *what did the network IDS see?* Show the diagram.

## 2. Prometheus data, not just pods (Phathutshedzo, ~6 min)

```bash
# RUN ON: k8s-cp-01
kubectl -n monitoring get pods,pvc
kubectl get --raw '/api/v1/namespaces/monitoring/services/kps-prometheus:9090/proxy/api/v1/query?query=up' | head -c 600; echo
```

Point out: every job is `1`; the four kubeadm-localhost jobs are switched off on purpose (troubleshooting §3).

## 3. Grafana from Git (Phathutshedzo, ~5 min)

Open `https://grafana.pt1.internal:30443` over the VPN (team-CA certificate) → dashboard **SCC26 3NCRYP+3D overview** (UTC). Show that it comes from `gitops/resources/monitoring/dashboard-scc26-overview.yaml`, not the GUI.

## 4. Wazuh: manager and agents (Olerato, ~6 min)

```bash
# RUN ON: edge-01
sudo systemctl is-active wazuh-manager
sudo /var/ossec/bin/agent_control -l        # 4 agents Active + the server
```

## 5. Suricata in IDS mode (Olerato, ~5 min)

```bash
# RUN ON: edge-01
sudo systemctl is-active suricata
sudo -u suricata suricata -T -c /etc/suricata/suricata.yaml   # as the service user (troubleshooting §4)
grep OPTIONS /etc/sysconfig/suricata           # -i <nic> -i wg0: IDS (af-packet), no inline
```

## 6. Live security drill, end to end (Olerato + Phathutshedzo, ~8 min)

Both actions are benign and team-owned (week3 §8). Write down the edge-01 time before and after.

```bash
# RUN ON: edge-01   (note the start time)
date -u +%FT%TZ
```

```bash
# RUN ON: WORKSTATION, over the VPN
curl -s -o /dev/null -w '%{http_code}\n' http://<worker>:30080/scc26-ids-drill   # network drill: our marker, our app
ssh -o PreferredAuthentications=publickey -o IdentitiesOnly=yes -o IdentityFile=/dev/null scc26-drill-nouser@api-lb-01 true   # host drill: fails on purpose
```

```bash
# RUN ON: edge-01   (reconstruct the timeline)
sudo grep '"signature_id":9000001' /var/log/suricata/eve.json | tail -1 | jq '{timestamp, sig: .alert.signature, iface: .in_iface}'
sudo jq -c 'select(.rule.id=="86601" and .data.alert.signature_id=="9000001") | {timestamp, rule: .rule.id, desc: .rule.description}' /var/ossec/logs/alerts/alerts.json | tail -1
sudo jq -c 'select(.rule.id=="5710") | {timestamp, agent: .agent.name, rule: .rule.id, desc: .rule.description}' /var/ossec/logs/alerts/alerts.json | tail -1
date -u +%FT%TZ
```

Select alerts by **rule ID**, not by grepping for the drill text: Wazuh also logs your own `sudo grep` command line (rule 5402), which would match. Rule 86601 is Wazuh's rule for *every* Suricata alert, so also filter on our signature ID. `alerts.json` rotates daily (older alerts are in `/var/ossec/logs/alerts/<year>/<Mon>/`), so run the drill fresh on the day.

Expected: Suricata `sid 9000001` → Wazuh rule **86601** within a second; the failed login → Wazuh rule **5710** from agent `api-lb-01`.

## 7. Student Platform (Phathutshedzo, ~6 min)

```bash
# RUN ON: k8s-cp-01
kubectl -n student-platform get deploy,pod,pvc,ingress
kubectl -n student-platform get deploy platform -o jsonpath='{.spec.template.spec.containers[0].image}'; echo   # sha tag + digest from CI
```

Browser: `https://platform.pt1.internal:30443` → sign in → team home shows your name and the status view (from the backend only) → sign out. Then open the GitHub Actions run that built the image and show the digest in its summary.

## 8. Provenance and Q&A (all, ~3 min)

Show one file in [`evidence/runs/`](../../evidence/runs/README.md): commit, image digest, UTC window, and no secrets (the writer refuses them).
