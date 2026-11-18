# Paper figure provenance

Every final figure should be reproducible or traceable.

For each figure, retain:

- source script/notebook/tool or original editable diagram;
- input data/log/result file;
- generation date and relevant Git SHA;
- units and axis labels;
- explanation of any filtering/aggregation;
- no secrets, tokens, private IP/address details or other unnecessary sensitive data.

Prefer vector PDF/SVG for diagrams and plots where practical. Avoid unreadable terminal screenshots.

## Figures in this directory

- `architecture.mmd` — the system architecture / experimental boundary, address-free
  (logical and Terraform-variable names only; source of truth `docs/network-design.md`).
  Render to the PDF `main.tex` includes with the mermaid CLI:
  `mmdc -i architecture.mmd -o architecture.pdf` (and `-o architecture.png`). Until
  rendered, `main.tex` shows a placeholder box via `\IfFileExists`. The block under
  *Architecture diagram (inline preview)* below is a copy so GitHub renders it inline —
  edit `architecture.mmd` first, then update the copy.
- `week5/` — Week-5 detection/response figures and the metrics table. **Generated, not
  hand-edited:** run `project/tools/w5paper.sh`, which reads every committed
  `project/runs/<run-id>/` and writes `metrics.tex/.md`, `phases.pdf/.png` and one
  `timeline-<run-id>.pdf/.png` per run. Commit these together with the run directories
  they came from.

## Architecture diagram (inline preview)

Copy of `architecture.mmd` so GitHub renders it without a build (address-free; logical
and Terraform-variable names only). The `.mmd` file is the source of truth for the paper.

```mermaid
flowchart TB
    subgraph INET["Zone: Internet (untrusted)"]
        ws["Team workstation<br/>WireGuard client in vpn_cidr<br/>kubectl only via control plane"]
        gpu(("Approved remote GPU endpoint<br/>A100/H200, one FQDN"))
    end

    subgraph CLOUD["Team OpenStack project (Terraform-owned)"]
        subgraph EDGEZ["Zone: mgmt network (mgmt_cidr)"]
            edge["edge-01 - only floating IP<br/>WireGuard | Pi-hole DNS | nftables<br/>Suricata IDS | Wazuh manager"]
        end
        subgraph K8SZ["Zone: k8s network (k8s_cidr), no floating IPs"]
            lb["api-lb-01<br/>HAProxy :6443"]
            cp["k8s-cp-01<br/>control plane; kubectl here only"]
            w1["k8s-worker-01"]
            w2["k8s-worker-02"]
        end
    end

    ws -- "WireGuard UDP (wireguard_port)" --> edge
    edge -- "routed admin path (no NAT)" --> cp
    lb -- "6443" --> cp

    subgraph CLUSTER["Kubernetes 1.36.4 + Cilium 1.20.1 - Argo CD GitOps"]
        traefik["Traefik ingress (NodePort)"]
        subgraph PLAT["ns: student-platform (defended)"]
            ui["Crypty UI + API"]
            pdb[("platform PostgreSQL")]
        end
        subgraph ACPNS["ns: agent-control-plane (default-deny egress)"]
            acp["ACP API"]
            herm["Hermes worker (singleton)"]
            adb[("ACP PostgreSQL - retain")]
        end
        subgraph MODEL["ns: model-serving"]
            lite["LiteLLM"]
            llama["llama.cpp - qwen2.5-0.5b-instruct (CPU)"]
        end
        subgraph OBS["ns: monitoring"]
            prom["Prometheus / Grafana"]
        end
    end

    traefik --> ui
    ui --> pdb
    ui --> acp
    acp --> adb
    herm --> adb
    herm -- "read-only" --> prom
    herm -- "FQDN egress only" --> gpu
    ui --> lite
    lite --> llama
    cp -. "Wazuh agent" .-> edge
    w1 -. "Wazuh agent" .-> edge
    w2 -. "Wazuh agent" .-> edge
```
