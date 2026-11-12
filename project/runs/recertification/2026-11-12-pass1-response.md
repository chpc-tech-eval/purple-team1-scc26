# Access recertification pass 1 — response and decisions (2026-11-12)

Response to [`2026-11-12-pass1.md`](./2026-11-12-pass1.md) (Rendani, `Rendani-Anele`, second member for separation of duties). Captain: Phathutshedzo (`saxs-14`).

Status key: ✅ resolved · ❓ pending captain/team input · 🛠️ remediation staged

## F1 — retired key on `rocky` (fix) 🛠️
- Prune mechanism merged in #113 (`common_revoked_keys` in `roles/common`), live on `main`.
- The retired key is still present on all 5 hosts; `common_revoked_keys` is **not yet populated** in the private inventory, so the prune is a no-op until it is.
- **To complete:** add the retired key's text to `common_revoked_keys` (private inventory), then an approved `bootstrap.yml` run across all hosts. The same run also rolls the #106 sshd hardening to the four hosts that still lack it.
- **"Rotate `rocky` entirely" (policy suggestion): deferred.** A retired machine key is not a confirmed compromise, and rotating the shared break-glass account mid-competition is disruptive. Recorded as a deferred decision; revisit only on evidence of misuse.

## C2 — WireGuard peer owners (confirm) ✅
- Verified against the private inventory: the four peers map one-to-one to the current members (Ole, Rendani, Phathu, Siya); the member who replaced a machine carries only the new key.
- **Correction to pass 1:** two peer owners were transposed in the pass-1 reading. The inventory is authoritative and the mapping is corrected here. Actual addresses stay only in the private inventory.

## C1 — two public /32 break-glass SSH sources (confirm) ❓
- The two public `/32` entries in `firewall_ssh_cidrs` (private inventory) are pending captain attribution to current members. _[captain: confirm each /32 → member; addresses stay out of Git]_

## C3 — `rocky` NOPASSWD rule in `/etc/sudoers` (confirm) ❓
- Assessment: almost certainly the OpenStack Rocky cloud-image default (cloud-init), consistent with the `90-cloud-init-users` unit already present.
- _[captain: confirm image default; keep as break-glass (recommended short-term) or move under Ansible-managed `sudoers.d` as part of #106]_

## D1 — all members `cluster-admin` (decision) ❓
- Recommendation: **accept with expiry** for the competition window — a four-person team needs operational agility and every member is already break-glass-capable. Re-review at competition end; narrow per role afterwards if retained.
- _[team: accept-with-expiry / narrow now]_

## Passed (no action)
`scc26-admins` = exactly the four members; each personal account holds only its owner's key; member kubeconfigs within 30 days; no unexpected sudoers, keys, CIDRs, units or cron beyond the documented `scc26-capture-offloads.service` on edge-01.

---
Fixes go through Git/Ansible, never by hand on a host. Next pass: before the next Week-5 phase, no later than 2026-11-26.
