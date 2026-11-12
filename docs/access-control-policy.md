# Access-control and break-glass policy

Who may reach the cluster, how, and how that stays true over time. The design
goal (DICT 432 L4/L6: least privilege, accountability, separation of duties) is
that **every action is traceable to one named person** and no standing access
exists that isn't named here. There is deliberately **no shared or hidden
account** beyond the single audited break-glass identity below — an unnamed or
covert door would be a vulnerability, not a control, and would fail both our own
rules (`~/.claude/CLAUDE.md` §9) and the Week-5 brief ("no uncontrolled
persistence").

## Who has access

The authorised people are the team: **Phathutshedzo (captain, `saxs-14`),
Olerato (`Ole06`), Siyabonga, Rendani**, and the instructor **Nyameko** for
review/oversight. Access is granted only through the named mechanisms below;
there is no other way in.

| Path | Who | How | Named? | Logged? |
| --- | --- | --- | --- | --- |
| Member Linux account | each member | own account in `scc26-admins`, **SSH key only**, sudo via group (`roles/team_users`) | yes (CN = person) | sshd + sudo + Wazuh |
| Member kubeconfig | each member | 30-day client cert (CN = person), rights from their own ClusterRoleBinding (`gitops/resources/cluster-rbac/members.yaml`) | yes | kube-apiserver audit |
| WireGuard | each member | own peer key; the private path to the hosts | yes (per-peer) | `wg` handshakes |
| Break-glass SSH from Internet | members | known public **/32s only**, Terraform rejects `0.0.0.0/0` (`modules/security`) | yes (per-CIDR) | sshd + Wazuh |
| **Break-glass account `rocky`** | the team, in an emergency only | SSH key only; **last-resort recovery when per-member access or WireGuard is broken** | shared → see controls | sshd + Wazuh, **alert on every use** |

## Controls that keep it least-privilege

- **sshd** (`roles/common`): key-only, no root login, `AllowGroups scc26-admins rocky`
  (nobody else may even attempt login), `MaxAuthTries 3`, idle-session timeout,
  no agent/X11 forwarding, modern KEX/ciphers/MACs only.
- **Network**: SSH reachable only over WireGuard or from members' /32s; everything
  else is default-deny (nftables at the edge, CiliumNetworkPolicy in-cluster).
- **Kubernetes**: per-member certs expire in 30 days (a stale credential dies on
  its own); rights come only from each member's ClusterRoleBinding — no shared
  admin token.
- **Break-glass `rocky`**: justified to be the single recovery identity, but shared,
  so it is the most watched. Its use must raise a Wazuh alert the whole team sees,
  its key is rotated after any use and after any member off-boards, and routine
  work never uses it.

## Account recertification (every two weeks, and before each Week-5 phase)

From DICT 432 L6 (recertification, permission/usage auditing). The captain, or a
second member for separation of duties, confirms:

1. `scc26-admins` contains exactly the current members — no extra, no leftover.
2. `~/.ssh/authorized_keys` on every host, and `common_authorized_keys`, list only
   current members' keys (plus the Terraform bootstrap key).
3. `members.yaml` ClusterRoleBindings match the current members and no one has more
   rights than their role needs.
4. Member kubeconfig certs are within their 30-day life (renew by re-running the
   playbook; do not widen the validity).
5. WireGuard `AllowedIPs`/peers match the current members.
6. No unexpected `sudoers.d` entry, SSH key, authorized CIDR, systemd unit or cron
   that would be standing access outside this table.

Record the check (date, who, result) in `project/runs/` or the team log. A finding
is fixed the same day through Git/Ansible, never by a manual edit on a host.

## Off-boarding a member (removes every door at once)

When someone leaves the team, in the **same change**:

1. `team_users_members`: set that member `state: absent` (removes the account and
   its sudo) and remove their key from `common_authorized_keys`.
2. Remove their ClusterRoleBinding from `members.yaml` (Argo CD prunes it).
3. Remove their WireGuard peer and their /32 from `bootstrap_ssh_cidrs`.
4. **Rotate the `rocky` break-glass key** (they may have held it).
5. Run the playbooks; then do a recertification pass to prove the access is gone.

A departed member's forgotten key or cert is the classic "backdoor by accident" —
this list closes all of them together.

## Emergencies

Use `rocky` only to restore access that is genuinely broken. Say in the team
channel that you are using it and why, expect the Wazuh alert, and rotate the key
afterwards. Everything done under `rocky` is still logged and reviewed.
