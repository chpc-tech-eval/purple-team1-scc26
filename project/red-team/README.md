# Red-team readiness (Purple Team 1)

This is the **offensive** half of the purple-team remit: how we run a red-team
engagement, the capability we keep ready, and the one thing we are still waiting on.
It is a readiness and methodology document, not a record of any action taken against
another team.

## Authorization boundary — read first

**No cross-team offensive action happens without a written Rules of Engagement from
the programme.** The instructor flagged a "reconnaissance of other teams' infra"
mission informally, but the scoped RoE we need to act on it is still open as
[#103](../../issues) (unanswered at the time of writing). Until that RoE exists:

- **Authorized now:** red-team activity against **our own range only**, under a
  per-run `SELF-RANGE-ATTACK-AUTH.md` (the offensive twin of the Week-5
  `SELF-RANGE-AUTH.md`). This is how we build and prove capability.
- **Blocked until the RoE lands:** any scan, probe, recon, or exploitation aimed at
  another team's systems. That authorization comes from the programme (which owns all
  the ranges), not from our own captain — a team cannot authorize action against
  systems it does not own. Acting without it is unauthorized access, full stop.

The point of this document is that when the RoE does land, we execute the same day
instead of starting to think then.

## What the RoE must pin down (so we can act immediately)

When we get scope from the programme, it must state, in writing:

1. **Targets in scope** — which teams/hosts/networks, by their programme identifiers.
2. **Techniques in scope / out of scope** — e.g. recon and enumeration yes;
   destructive actions, data destruction, DoS no (unless explicitly permitted).
3. **Time window** — start/stop, and any blackout periods.
4. **Deconfliction** — who to notify, and how to signal a real problem vs. an exercise
   action.
5. **Evidence handling** — what we may collect and where it is stored.
6. **Stop conditions** — what makes us halt immediately.

We keep a filled-in request on #103 so the programme only has to approve, not author.

## Capability we keep ready

Standard, open-source, non-destructive tooling — nothing exotic, nothing that needs a
paid licence:

| Phase (MITRE ATT&CK) | What we do | Tooling |
| --- | --- | --- |
| Reconnaissance (TA0043) | host/service discovery, version fingerprinting | `nmap`, `masscan` (rate-limited), `httpx` |
| Resource development (TA0042) | wordlists, non-destructive test payloads | `seclists`, our own benign markers |
| Initial access (TA0001) | exposed-service and default-credential checks | `nmap` scripts, manual review |
| Execution / Discovery (TA0002/TA0007) | enumerate reachable services, map trust | `curl`, `kubectl` (our cluster only) |
| Lateral movement (TA0008) | prove/deny segmentation holds | path testing from a scoped host |
| Collection (TA0009) | capture **marked, benign** evidence only | `tcpdump`, screenshots, hashes |
| Exfiltration (TA0010) | measured, declared, over an agreed channel | only if the RoE permits |

Every action is **pre-declared and benign-marked**, the same discipline as the Week-5
self-range runs, so our own detection stack (and the defenders' on the other side)
can tell an exercise action from a real incident.

## Self-range practice (authorized now)

We validate the capability against our own range exactly as a Week-5 run, but from the
attacker's seat:

1. Create a run dir and a `SELF-RANGE-ATTACK-AUTH.md` declaring the scenario, scope
   (our own `student-platform` / range hosts), window and marked actions.
2. Recon -> enumerate -> attempt a pre-declared benign action against our own platform.
3. Export evidence with the Week-5 tooling
   (`project/tools/w5run.py`, `w5paper.sh`) so the run is provenance-tracked like any
   other, and failed attempts are kept, not deleted.
4. Cross-check: did our own Suricata/Wazuh detections fire? Gaps found here feed both
   the detection set (defense) and our technique list (offense).

This doubles as defender training: every technique we can execute is one our
[`project/detections/`](../detections/) rules should catch.

## Readiness checklist

- [ ] Filled-in RoE request sitting on #103, ready for programme approval.
- [ ] Toolkit installed on a scoped workstation (not on the range hosts themselves).
- [ ] One self-range attack run completed and provenance-tracked.
- [ ] Detection coverage reviewed against the techniques above.
- [ ] Deconfliction contact + stop conditions agreed with the team.

## Rules we never break

- Our own range until the RoE scopes otherwise; other teams only under written scope.
- Non-destructive by default: no data destruction, no DoS, no persistence we don't
  remove, nothing left running on another team's systems.
- Address-free in this public repo: no real CIDRs, IPs, or host specifics here or in
  any committed run — those live in private material only.
- Keep every run, including failures. A blocked attempt is a valid result.
