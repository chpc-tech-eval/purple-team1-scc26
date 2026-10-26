# Week-3 architecture: observability, security telemetry, Student Platform

Editable source: [`observability-security.mmd`](observability-security.mmd) (Mermaid). The block below is a copy of it so GitHub renders it inline; edit the `.mmd` file first, then copy it here. Week-1 network and Week-2 cluster: [`../../week1/diagrams/`](../../week1/diagrams/README.md), [`../../week2/diagrams/`](../../week2/diagrams/README.md).

**Address-free:** only variable names and SG rule numbers from [`docs/network-design.md`](../../../docs/network-design.md) §4.

**The three observability questions (week3):** Prometheus/Grafana answers *is the platform healthy?*, Wazuh answers *what host/security events happened?*, Suricata answers *what did the network IDS see?*

```mermaid
flowchart TB
    subgraph WS["Member workstation (WireGuard, vpn_cidr)"]
        browser["Browser / curl"]
        ans["Ansible (host layer)"]
    end

    subgraph GH["GitHub"]
        repo[("repo: dev = desired state")]
        ci["Actions: platform-image<br/>tests -> image -> GHCR sha-commit"]
        ghcr[("GHCR<br/>student-platform:sha-...")]
        repo --> ci --> ghcr
    end

    subgraph EDGE["edge-01 (mgmt_cidr)"]
        wg["WireGuard wg0"]
        suri["Suricata IDS<br/>af-packet on NIC + wg0<br/>EVE JSON"]
        wm["Wazuh manager 4.14.8<br/>reads EVE + agent events"]
        suri -- "eve.json" --> wm
    end

    subgraph K8S["Kubernetes (k8s_cidr)"]
        argo["Argo CD (follows dev)"]
        subgraph MON["monitoring"]
            prom["Prometheus 20Gi"]
            graf["Grafana 5Gi<br/>dashboards from Git"]
        end
        subgraph SP["student-platform"]
            app["platform x2<br/>Astro + API"]
            pg[("PostgreSQL 17 10Gi<br/>NetworkPolicy: namespace only")]
            app --> pg
        end
        trf["Traefik NodePort 30443<br/>TLS from pt1-internal-ca"]
    end

    agents["Wazuh agents on api-lb-01,<br/>k8s-cp-01, k8s-worker-01/02"]

    browser -- "VPN" --> wg
    wg -- "routed, no NAT" --> trf
    trf -- "grafana.pt1.internal" --> graf
    trf -- "platform.pt1.internal" --> app
    repo -- "poll" --> argo
    argo -. "deploys" .-> MON
    argo -. "deploys" .-> SP
    ghcr -. "image by digest" .-> app
    prom -- "scrapes nodes (SG 17), kubelet, KSM, app /metrics" --> app
    graf --> prom
    agents -- "1514-1515 (SG 15 + nftables)" --> wm
    ans -- "SSH over VPN" --> EDGE
```

| Path | Ports / rule |
| --- | --- |
| Prometheus → node-exporter on every node | 9100/tcp, SG row 17 (`k8s_cidr`) |
| Wazuh agents → manager on edge-01 | 1514-1515/tcp, SG row 15 + edge nftables (private ranges) |
| Browser → Grafana / Platform | VPN → worker NodePort 30443 (rule 14b) → Traefik, team-CA TLS |
| Platform → PostgreSQL | 5432 inside `student-platform` only (NetworkPolicy) |
