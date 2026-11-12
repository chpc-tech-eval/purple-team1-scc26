# Access recertification pass 1 — response and decisions (2026-11-12)

Response to [`2026-11-12-pass1.md`](./2026-11-12-pass1.md) (Rendani, `Rendani-Anele`, second member for separation of duties). Captain: Phathutshedzo (`saxs-14`).

Status key: ✅ resolved · ❓ pending captain/team input · 🛠️ remediation staged

## F1 — retired key on `rocky` (fix) ✅ RESOLVED (2026-11-12)
- Prune mechanism merged in #113 (`common_revoked_keys` in `roles/common`), live on `main`.
- The retired Swaetc key (`SHA256:s2iR3fOl…`) was added to `common_revoked_keys` in the private inventory, then `bootstrap.yml` was run across all 5 hosts (approved by the captain).
- **Result:** the "Remove revoked SSH keys" task reported `changed` on all 5 hosts; re-verification (`ssh-keygen -lf` over each `rocky` `authorized_keys`) returns **REVOKED-OK on all 5** — the key is gone. No lockout (key-auth sessions kept working through the sshd reload). The same run also rolled the #106 sshd hardening to the four hosts that previously lacked it (edge-01 already had it).
- The revoked entry is retained in the private inventory as a record (access revoked, history kept).
- **"Rotate `rocky` entirely" (policy suggestion): deferred.** A retired machine key is not a confirmed compromise, and rotating the shared break-glass account mid-competition is disruptive. Recorded as a deferred decision; revisit only on evidence of misuse.

## C2 — WireGuard peer owners (confirm) ✅
- Verified against the private inventory: the four peers map one-to-one to the current members (Ole, Rendani, Phathu, Siya); the member who replaced a machine carries only the new key.
- **Correction to pass 1:** two peer owners were transposed in the pass-1 reading. The inventory is authoritative and the mapping is corrected here. Actual addresses stay only in the private inventory.

## C1 — two public /32 break-glass SSH sources (confirm) ✅
- Captain confirmed (2026-11-12): both public `/32` entries in `firewall_ssh_cidrs` (private inventory) are current members' break-glass source IPs. Retained as break-glass fallback. Addresses stay out of Git; re-attribute at the next pass if a member's IP changes.

## C3 — `rocky` NOPASSWD rule in `/etc/sudoers` (confirm) ✅
- Captain confirmed (2026-11-12): accepted as the OpenStack Rocky cloud-image default (cloud-init), consistent with the `90-cloud-init-users` unit already present. **Kept as break-glass** — `rocky` remains the break-glass account. Recorded as an accepted item; not moved under Ansible for now.

## D1 — all members `cluster-admin` (decision) ✅
- Decision (2026-11-12): **accepted with expiry** for the competition window — a four-person team needs operational agility and every member is already break-glass-capable. Recorded as an accepted risk; **re-review at competition close** and narrow to per-role RBAC if `cluster-admin` is retained afterwards.

## Passed (no action)
`scc26-admins` = exactly the four members; each personal account holds only its owner's key; member kubeconfigs within 30 days; no unexpected sudoers, keys, CIDRs, units or cron beyond the documented `scc26-capture-offloads.service` on edge-01.

---
Fixes go through Git/Ansible, never by hand on a host. Next pass: before the next Week-5 phase, no later than 2026-11-26.
