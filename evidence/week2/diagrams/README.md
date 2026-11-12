# Week-2 architecture: Kubernetes + GitOps

Editable source: [`cluster-gitops.mmd`](cluster-gitops.mmd) (Mermaid). The block below is a copy of it so GitHub renders it inline; edit the `.mmd` file first, then copy it here. The Week-1 network and trust boundaries are unchanged: [`../../week1/diagrams/`](../../week1/diagrams/README.md).

**Address-free (instructor rule on #23):** only variable names (`mgmt_cidr`, `k8s_cidr`, `vpn_cidr`) and SG rule numbers from [`docs/network-design.md`](../../../docs/network-design.md) §4 appear.

**How to read it:** members change the cluster through **Git**, not `kubectl`. A PR merged into `dev` is picked up by Argo CD on `k8s-cp-01` and applied to the workers. Terraform and Ansible (host layer) run from the workstation over the VPN. `kubectl` runs only on `k8s-cp-01`, under each member's own account and kubeconfig (#58). Users reach apps over the VPN on the Traefik NodePorts, with TLS from the team CA.

```mermaid
flowchart TB
    subgraph WS["Member workstation (WireGuard client in vpn_cidr)"]
        git["Git + PRs"]
        tfa["Terraform + Ansible<br/>(state holder: captain;<br/>encrypted backup on edge-01)"]
        kseal["kubeseal<br/>(public cert only)"]
        browser["Browser / curl"]
    end

    gh[("GitHub<br/>chpc-tech-eval/purple-team1-scc26<br/>dev = desired state<br/>4 CI checks on every PR")]
    git --> gh
    kseal -- "SealedSecrets only" --> gh

    subgraph CLOUD["Team OpenStack project on pta.sebowa (Terraform-owned)"]
        subgraph MGMT["mgmt_cidr"]
            edge["edge-01<br/>WireGuard | Pi-hole (*.pt1.internal) | nftables"]
        end
        subgraph K8S["k8s_cidr (no floating IPs)"]
            lb["api-lb-01<br/>HAProxy :6443"]
            cp["k8s-cp-01<br/>kube-apiserver, etcd<br/>kubectl lives here only<br/>Argo CD, Sealed Secrets"]
            w1["k8s-worker-01"]
            w2["k8s-worker-02"]
        end
        cinder[("Cinder volumes<br/>StorageClass cinder-ssd (default)")]
    end

    browser -- "WireGuard UDP (SG rule 2)" --> edge
    tfa -- "SSH over VPN (rule 6)<br/>own Linux account per member (#58)" --> cp
    edge -- "routed, no NAT" --> w1
    edge -- "routed, no NAT" --> w2
    cp -- "API via stable endpoint (rules 7-8)" --> lb
    lb --> cp
    w1 & w2 -- "join + API via HAProxy" --> lb

    subgraph ARGO["Argo CD on k8s-cp-01: root app follows dev/gitops/applications"]
        apps["cinder-csi | cert-manager + cert-manager-config (pt1-internal-ca)<br/>traefik (NodePort 30080/30443, rule 14b)<br/>ingress-test (whoami) | storage-test | cluster-rbac"]
    end
    gh -- "poll dev every ~3 min<br/>prune + selfHeal" --> apps
    apps -. "runs on" .-> w1
    apps -. "runs on" .-> w2
    apps -- "PVCs" --> cinder

    browser -- "https://*.pt1.internal:30443<br/>TLS from team CA" --> w1
    cilium["Cilium 1.20.1 (VXLAN 8472, rule 11)<br/>pod network between all 3 nodes"]
    cp --- cilium
    w1 --- cilium
    w2 --- cilium
```

| Layer | Owner | Where it is defined |
| --- | --- | --- |
| VMs, networks, security groups | Terraform | `infrastructure/terraform` |
| OS, containerd, kubeadm, Cilium/Argo/Sealed-Secrets bootstrap, member accounts | Ansible | `infrastructure/ansible` |
| Everything long-lived inside Kubernetes | Argo CD | `gitops/applications` + `gitops/resources` |
