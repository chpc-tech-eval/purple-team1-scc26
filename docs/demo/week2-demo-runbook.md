# Demo: Week-2 runbook (Kubernetes, Cilium, Cinder, GitOps)

About 45 minutes. Every command is read-only unless marked. Evidence index: [`evidence/week2/README.md`](../../evidence/week2/README.md); diagram: [`evidence/week2/diagrams/`](../../evidence/week2/diagrams/README.md); problems we hit: [`evidence/week2/troubleshooting.md`](../../evidence/week2/troubleshooting.md).

## Before you share your screen

- VPN up on the presenting machine (`wg show` shows a recent handshake).
- Log in as **yourself** (`ssh <name>@k8s-cp-01`), not `rocky`, so the audience sees per-member access (#58).
- **Never show** `terraform.tfvars`, the private inventory, `~/.config/scc26-secrets/`, `clouds.yaml`, any kubeconfig contents, or `kubectl get secret -o yaml`. Real addresses stay off the shared screen; use host names.
- Close every tab except the terminal and the GitHub PR list.

## 1. Architecture and ownership (Phathutshedzo, ~6 min)

Show the diagram in [`evidence/week2/diagrams/README.md`](../../evidence/week2/diagrams/README.md) and explain the hand-over:

```text
Terraform → VMs, networks, security groups
Ansible   → OS, containerd, kubeadm, Cilium/Argo/Sealed-Secrets bootstrap, member accounts
Argo CD   → everything long-lived inside Kubernetes, from dev
```

Point out: `kubectl` runs only on `k8s-cp-01`; nobody has a cluster admin kubeconfig on a laptop.

## 2. Kubernetes and Cilium (Olerato, ~8 min)

```bash
# RUN ON: k8s-cp-01 (as yourself)
kubectl auth whoami                       # your own identity, not kubernetes-admin
kubectl get nodes -o wide                 # 3 x Ready, v1.36.4, containerd 2.3.4
kubectl get --raw='/readyz?verbose' | tail -3
cilium status --wait
kubectl get ns | grep cilium-test         # connectivity-test workloads are kept on purpose
```

Talking points: kubeadm through the HAProxy endpoint (#48), Cilium `ipam: kubernetes` so it does not overlap our ranges (troubleshooting §2), connectivity test 82/82 (#49).

```bash
# RUN ON: api-lb-01
sudo systemctl is-active haproxy          # active
sudo ss -ltn | grep ':6443'               # HAProxy listening on the stable API endpoint
```

## 3. GitOps: Argo CD and Sealed Secrets (Siyabonga, ~8 min)

```bash
# RUN ON: k8s-cp-01
kubectl -n argocd get applications        # every app Synced/Healthy, root follows dev
kubectl -n kube-system get pods -l app.kubernetes.io/name=sealed-secrets
```

```bash
# RUN ON: WORKSTATION (shows the public cert only, no private key)
grep -c "PRIVATE KEY" ~/.config/scc26-secrets/3ncryp3d-sealed-secrets.cert   # expect 0
```

Then open [#61](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/61) and show the Part G proof: a one-line Git change (whoami 1 → 2) merged, Argo reconciled it, and the Deployment's only field managers are Argo and Kubernetes itself.

```bash
# RUN ON: k8s-cp-01
kubectl -n ingress-test get deploy,rs,pods
kubectl -n ingress-test get deploy whoami -o jsonpath='{range .metadata.managedFields[*]}{.manager}{"\n"}{end}' | sort -u
```

## 4. Storage: Cinder CSI (Olerato, ~6 min)

```bash
# RUN ON: k8s-cp-01
kubectl get storageclass                  # cinder-ssd (default), cinder-hdd, cinder-default
kubectl -n storage-test get pvc,pod
kubectl -n storage-test exec persistence-test -- cat /data/marker.txt
```

Story: write a marker, delete the **pod** (not the PVC), Argo recreates it on the other worker, and the marker is still there ([#51](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/51)). Optional live re-run (writes to the test volume only):

```bash
# RUN ON: k8s-cp-01   (CHANGES the test pod; safe, it is Argo-managed)
kubectl -n storage-test delete pod persistence-test && kubectl -n storage-test wait pod/persistence-test --for=condition=Ready --timeout=180s
kubectl -n storage-test exec persistence-test -- cat /data/marker.txt
```

## 5. Ingress and TLS (Phathutshedzo, ~6 min)

```bash
# RUN ON: k8s-cp-01
kubectl get clusterissuer,certificate -A
kubectl get ingress -A                    # ADDRESS ingress.pt1.internal
```

```bash
# RUN ON: WORKSTATION, once: fetch the team CA's PUBLIC certificate
ssh <name>@k8s-cp-01 "kubectl -n cert-manager get secret pt1-internal-ca -o jsonpath='{.data.ca\.crt}'" | base64 -d > pt1-ca.crt
```

```bash
# RUN ON: WORKSTATION, over the VPN (Pi-hole names; add --resolve <name>:<port>:<worker> if Pi-hole is not your resolver)
curl -sI http://whoami.pt1.internal:30080/ | grep -i location     # -> https://...:30443/
curl -s --cacert pt1-ca.crt https://whoami.pt1.internal:30443/ | head -3
```

Explain: internal domain `pt1.internal` (#13), so a private team CA instead of public ACME (question to the instructor on #55); Traefik on NodePorts because there is no cloud load balancer; rule 14b opens only 30080/30443, only from the VPN.

## 6. Security and operations (Siyabonga, ~5 min)

- Per-member Linux accounts and personal, revocable kubeconfigs ([#58](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/58)).
- Encrypted Terraform state backup any member can restore ([#59](https://github.com/chpc-tech-eval/purple-team1-scc26/pull/59)).
- Pinned versions everywhere (versions table in the evidence index), images by digest, gitleaks on every PR.

## 7. Lessons and Q&A (all, ~6 min)

Pick two from [`troubleshooting.md`](../../evidence/week2/troubleshooting.md): the chart that rejected our redirect value (§6) and the non-revocable binding we caught before it went live (§9) both make good stories.
