# Purple Team — Agentic Security Orchestration, Detection & Digital Forensics

**Repository:** `purple-team-scc26`  
**Recommended long name:** **Purple Team: Agentic Security Orchestration, Detection & Digital Forensics**  
**Duration:** 10-week core, 12 weeks with stretch/handover  
**Team structure:** two cooperating student teams, 3–5 students per team

## Project summary

This project gives “red versus blue” a deliberately different meaning. Two student teams jointly operate an authorised cyber range built from the same infrastructure and platform components used by the hybrid HPC–QC environment. One team begins as the **Adversary Emulation Cell** and the other as the **Detection & Response Cell**. Midway through the project they rotate roles so that every student must understand both offensive evidence generation and defensive detection/forensics.

The point is not to reward clever exploitation in isolation. The point is to build an evidence-driven purple-team workflow in which controlled adversary actions produce observable signals, defenders turn those signals into detections and incident timelines, and Hermes/`agent-control-plane` helps analysts correlate and explain evidence without becoming an unrestricted administrator.

The project integrates primarily with:

- `infra-hpc-qc-k8s` for the isolated OpenStack/Kubernetes security lab, Wazuh, Suricata, Prometheus/Grafana, Cilium and network boundaries;
- `quantum-platform` for authenticated administrator-facing views and future incident/task surfaces;
- `agent-control-plane` for bounded, auditable agent tasks and persistent run/evidence history;
- Hermes as the primary agent runtime/explanation layer.

## Core question

> Can two student teams build a repeatable purple-team exercise in which every authorised adversary action is detectable, explainable and reconstructable from host, network, Kubernetes and agent-control-plane evidence?

## Learning outcomes

By completion, students should be able to:

- deploy and validate an isolated cloud/Kubernetes security range;
- explain the difference between preventive controls, detection controls and forensic evidence;
- operate Wazuh, Suricata and Prometheus/Grafana together rather than as unrelated dashboards;
- design safe adversary-emulation scenarios with explicit scope and success criteria;
- construct an incident timeline from multiple evidence sources;
- write and test detections against known activity;
- integrate a bounded Hermes analyst profile with read-only evidence sources;
- measure detection and response performance;
- document false positives, false negatives and evidence gaps;
- conduct a blameless purple-team retrospective and improve the system.

## Safety and authorisation boundary

All adversary activity is confined to the project-owned range and explicitly approved scenarios. Students must not probe external systems, production systems, other teams' resources or services outside the assigned OpenStack projects/namespaces.

The repository may contain scenario descriptions, detection rules, replay fixtures and synthetic evidence. It must not contain real credentials, production secrets or uncontrolled destructive payloads.

Hermes is read/report by default. Any mutation capability introduced as a stretch objective must be a fixed, reviewed action behind explicit human approval and full audit logging.

## Two-team operating model

### Cell A — Adversary Emulation

Responsibilities during the first half:

- define approved attack hypotheses;
- generate controlled host/network/application signals;
- record exact start/stop times and expected observables;
- maintain scenario manifests;
- avoid destructive persistence or uncontrolled lateral movement;
- hand defenders enough ground truth after the exercise to calculate detection quality.

### Cell B — Detection & Response

Responsibilities during the first half:

- establish telemetry baselines;
- validate Wazuh agents, Suricata sensors and Prometheus targets;
- author detection/triage rules;
- maintain incident case records and timelines;
- measure `T_detect`, `T_identify`, `T_contain` and `T_recover` where meaningful;
- record false positives and false negatives.

### Rotation

At the midpoint, the cells exchange roles. The second exercise must be materially different enough that students cannot merely replay memorised answers.

## Architecture

```text
                Isolated OpenStack project / cyber range
                              │
                  ┌───────────┴───────────┐
                  │                       │
               edge/security          Kubernetes
                  │                       │
       Suricata + Wazuh agent      workloads / decoys
                  │                       │
                  └──────────┬────────────┘
                             │
                     security telemetry
          ┌──────────────────┼──────────────────┐
          │                  │                  │
       Wazuh              Suricata          Prometheus
          │                  │                  │
          └──────────────────┼──────────────────┘
                             ▼
                    evidence normalisation
                             │
                   agent-control-plane
                   task/run/evidence ledger
                             │
                    bounded Hermes analyst
                             │
                 explanation / correlation
                             │
                  quantum-platform admin
```

## Scope

### Must deliver

1. Reproducible isolated range deployment based on `infra-hpc-qc-k8s` patterns.
2. Wazuh and Suricata telemetry flowing into a documented analysis path.
3. Prometheus/Grafana health/availability context alongside security telemetry.
4. At least four approved adversary-emulation scenarios spanning at least two telemetry layers.
5. Detection rules or queries for every scenario.
6. A structured incident/evidence schema.
7. A read-only Hermes analyst workflow that receives curated evidence, not arbitrary shell access.
8. Persistent task/run/evidence history through `agent-control-plane` or a compatible project fixture.
9. Metrics for detection rate, false positives/negatives and response timing.
10. A full purple-team replay in which another student can reconstruct the event timeline from the repository and retained evidence.

### Should deliver

- Cilium flow/network-policy evidence for at least one scenario;
- automated scenario reset and environment cleanup;
- a small rule-test suite with fixture logs;
- admin UI summary of incidents/tasks and Hermes explanations;
- comparison of human-only triage versus Hermes-assisted triage.

### Stretch

- human-approved containment action such as quarantining a namespace/workload through a fixed control-plane capability;
- ATT&CK-style mapping of scenarios;
- replayable PCAP/log fixture library;
- multi-agent specialist roles such as network analyst, host analyst and incident summariser.

## Explicit non-goals

- unrestricted autonomous remediation;
- generic remote shell tools exposed to Hermes;
- attacking systems outside the range;
- malware development or destructive payload engineering;
- replacing Wazuh/Suricata with an LLM;
- claiming the model is an authority on incident truth without underlying evidence.

## Proposed repository layout

```text
purple-team-scc26/
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── THREAT-MODEL.md
│   ├── RULES-OF-ENGAGEMENT.md
│   ├── EVIDENCE-MODEL.md
│   └── RUNBOOK.md
├── scenarios/
│   ├── scenario-01/
│   ├── scenario-02/
│   ├── scenario-03/
│   └── scenario-04/
├── detections/
│   ├── wazuh/
│   ├── suricata/
│   └── prometheus/
├── fixtures/
│   ├── logs/
│   └── expected/
├── dashboards/
├── agent/
│   ├── prompts/
│   ├── evidence-adapters/
│   └── tests/
├── scripts/
├── tests/
└── .github/workflows/
```

## Ten-week roadmap

### Week 1 — Range and rules of engagement

- clone/read the owning platform repositories;
- document topology, trust boundaries and telemetry sources;
- write `RULES-OF-ENGAGEMENT.md`;
- deploy the smallest isolated test environment;
- verify no exercise traffic can escape the intended scope.

**Exit:** agreed architecture + one reachable target + one Wazuh/Suricata observation.

### Week 2 — Telemetry baseline

- validate Wazuh agent events;
- validate Suricata network events;
- validate Prometheus health context;
- create a common timestamp/event envelope;
- define evidence retention and redaction rules.

**Exit:** one timeline that combines host, network and health evidence.

### Week 3 — Scenario 1 and detection tests

- adversary cell runs one low-risk approved scenario;
- defender cell writes detection and triage notes;
- capture ground truth and calculate detection latency;
- convert evidence into automated test fixtures.

**Exit:** first replayable scenario with expected detections.

### Week 4 — Scenario 2 + agent analyst

- add a second scenario on a different telemetry layer;
- integrate a bounded Hermes profile;
- Hermes receives curated evidence and returns explanation/correlation;
- record task/run/evidence/output in the control-plane ledger.

**Exit:** read-only agent-assisted incident analysis with persistent history.

### Week 5 — Forensics and response

- build incident timeline tooling;
- test missing telemetry and corrupted/partial evidence;
- document false positives/negatives;
- run a tabletop containment decision without autonomous mutation.

**Exit:** defensible incident report from retained evidence.

### Week 6 — Role rotation

Teams swap adversary/defender roles. Build Scenario 3 with different assumptions.

**Exit:** new team demonstrates competence in the opposite role.

### Week 7 — Cross-layer scenario

Create Scenario 4 that crosses at least two of: host, network, Kubernetes/application, identity or agent task evidence.

**Exit:** integrated purple-team exercise and frozen evidence schema.

### Week 8 — Reliability and automation

- one-command lab reset where practical;
- detection regression tests;
- dashboards and runbooks;
- recovery from telemetry component failure.

### Week 9 — Staging exercise

- freeze `stag`;
- run the entire scenario suite from documented instructions;
- a third party or supervisor follows the runbook;
- record all defects as issues.

### Week 10 — Final exercise and release

Live exercise, incident reconstruction, metrics review, lessons learned, `main` release and upstream PR/design proposals.

### Weeks 11–12 — Stretch

Human-approved containment capability, improved agent specialisation, additional scenario fixtures and upstream hardening.

## Metrics

At minimum record:

- scenario detection rate;
- false-positive count/rate;
- false-negative count/rate;
- `T_detect` — event to first detection;
- `T_identify` — detection to correct interpretation;
- `T_contain` — when a containment decision/action is part of the exercise;
- `T_recover` — when recovery is exercised;
- agent evidence coverage — percentage of statements in the generated summary traceable to supplied evidence;
- analyst correction count — material corrections humans make to the agent output.

Do not optimise solely for low timings. A fast but incorrect classification is worse than a slower, evidence-grounded result.

## Acceptance test

The final demonstration should begin with a clean/reproducibly restored range. The adversary cell executes an approved scenario unknown in detail to the active defenders. The defenders must detect, triage and reconstruct it using the platform telemetry. Hermes may assist by explaining evidence but may not receive unrestricted administrative credentials. The team must show the full event/evidence/task history and explain what the system missed as well as what it detected.

## Upstream contribution targets

Potential mature contributions belong in:

- `infra-hpc-qc-k8s`: Wazuh/Suricata deployment, dashboards, safe telemetry adapters, lab isolation improvements;
- `agent-control-plane`: bounded diagnostic/evidence adapters and audit schema improvements;
- `quantum-platform`: admin incident/task-history views;
- `chpc-tech-eval/scc`: carefully sanitised security-observability tutorial material after the exercise.
