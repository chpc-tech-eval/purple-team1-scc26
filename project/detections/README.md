# Week-5 detections

The team's tested detections for the controlled exercise (`week5/README.md`: "at least one tested detection/rule/query per scenario"). Rules are deployed by Ansible; this directory holds the tests.

| Source of truth | Deployed to (edge-01) |
| --- | --- |
| [`roles/suricata/files/scc26-detections.rules`](../../infrastructure/ansible/roles/suricata/files/scc26-detections.rules) | merged by `suricata-update`, then `suricata -T` before any restart |
| [`roles/wazuh_manager/files/scc26_rules.xml`](../../infrastructure/ansible/roles/wazuh_manager/files/scc26_rules.xml) | `/var/ossec/etc/rules/`, `wazuh-analysisd -t`, rolled back on failure |

## Catalogue

| ID | Engine | Detects | ATT&CK | Test case | Known false positives |
| --- | --- | --- | --- | --- | --- |
| 9000010 | Suricata | ≥ 40 SYNs in 10 s from one source (scan or sweep) | T1046 | `syn_scan` | load tests, a busy NAT gateway |
| 9000011 | Suricata | ≥ 10 new SSH connections in 60 s from one source | T1110 | `ssh_burst` | Ansible without connection reuse |
| 9000012 | Suricata | path traversal in the raw URI (`../`, `%2e%2e%2f`, backslash forms) | T1190 | `traversal` | rare; some legacy clients |
| 9000013 | Suricata | SQL injection, `UNION [ALL] SELECT` in the URI | T1190 | `sqli_union` | search fields containing those words |
| 9000014 | Suricata | SQL injection, quoted tautology (`' OR '1'='1`) | T1190 | `sqli_tautology` | rare |
| 9000015 | Suricata | scanner user agents (sqlmap, nikto, nmap NSE, gobuster, nuclei, …) | T1595 | `scanner_ua` | our own authorised scans |
| 9000001 | Suricata | Week-3 drill marker (regression) | n/a | `drill` | none (benign marker) |
| 100100 | Wazuh | a team Suricata detection, raised from level 3 to 10 | n/a | `suricata_team_alert` | inherits the Suricata rule's |
| 100101 | Wazuh | ≥ 3 team detections from one source within 5 min (level 12) | n/a | `suricata_repeat_source` | inherits |
| 100110 | Wazuh | any SSH login as the shared break-glass account `rocky` (level 12), as `docs/access-control-policy.md` requires | T1078 | `break_glass_login` | **Ansible runs that connect as `rocky`** (see below) |
| 100113 | Wazuh | a member switches to `rocky` inside a host (`su - rocky`, `sudo -u rocky`), level 12 | T1078 | `su_to_rocky`, `sudo_as_rocky` | none expected: routine work doesn't switch to `rocky` |
| 100111 / 100112 | Wazuh | 100111: one rejected SSH login to an existing account on a key-only host (level 3). 100112: 8 or more of them within 2 min on one host (level 10) | T1110 | 5712 / 5763 | Wazuh built-in | SSH brute force (invalid user / failed password) | T1110 | `ssh_*_bruteforce_then_success` | user mistyping a password 8 times |
| 5712 / 5763 | Wazuh built-in | SSH brute force (invalid user / failed password) | T1110 | `ssh_*_bruteforce_then_success` | user mistyping a password 8 times |
| 40112 | Wazuh built-in | authentication failures followed by a success, same source (level 12) | T1110, T1078 | `ssh_*_bruteforce_then_success` | user who finally gets the password right |

Negative tests: `benign` (normal browsing and 3 SSH sessions) must trigger **no** team SID; a non-team Suricata alert must stay at 86601; a normal login must not trigger 40112 or 100110; a user named like `rockyb` must not match the break-glass rules; `rocky` running sudo to root (Ansible) and sshd's own PAM line must not trigger 100113; 7 rejected logins must not trigger 100112; plain connect-and-close probes must not count as rejected logins.

**Break-glass alert and Ansible.** The policy says `rocky` is for emergencies only, but the inventory still connects as `ansible_user: rocky`, so every playbook run currently raises 100110 on each host it touches. That is the rule working as written, not a false positive to suppress. The fix is on the Ansible side: run playbooks from a named member account (each member now has one, `roles/team_users`) and keep `rocky` for recovery. Until then, expect 100110 during announced playbook runs and treat any other one as a real break-glass use.

**Failed logins to `rocky` have no team rule, on purpose.** A first version added one (level 8 on 5760), but the test `break_glass_bruteforce_then_success` showed it took the events away from the built-in brute-force counter: a brute force on `rocky` stopped producing 5763 and 40112. It was removed. Failures stay on the built-ins (5760, then 5763 and 40112), and a brute force that ends in a `rocky` login is reported by 40112 (level 12) on the success line.

**Duplicates are not added.** A team rule for "SSH success after brute force" was written first, but Wazuh's built-in 40112 already catches the pattern and wins, so the team rule could never fire. It was removed, and the tests assert 40112 instead.

## Known misses (false negatives, tested)

Attack variants the current rules are **expected to miss**. They are in the test suite (`SURICATA_MISS`, `WAZUH_MISS` in `cases.py`) and print as `miss`. If a rule change starts catching one, the test fails with `NOW DETECTED`, so this table is updated in the same change. A Suricata miss only counts if Suricata really saw the traffic (at least one flow), so a broken pcap can't pass as a miss.

| Case | Evades | Why | How it could be closed |
| --- | --- | --- | --- |
| `slow_scan` | 9000010 | 60 SYNs 0.3 s apart (nmap `-T2` pace) never reach 40 in 10 s | a second, slower threshold (e.g. 100 SYNs / 5 min); flow-based detection in Wazuh |
| `distributed_scan` | 9000010 | the threshold counts per source; 4 sources × 15 SYNs | `track by_dst` variant (many sources → one target) |
| `udp_scan` | 9000010 | the scan rule matches TCP only | a UDP threshold rule |
| `slow_ssh` | 9000011 | 9 connections / 60 s is one under the threshold | lower it (baseline peak is 2 / 60 s) or add a 5-minute window |
| `traversal_double_encoded` | 9000012 | `%252e%252e%252f` decodes to `%2e%2e%2f`, not `../` | add `%25` forms to the pcre |
| `sqli_union_comment` | 9000013 | `UNION/**/SELECT`: a comment instead of whitespace | allow `/\*.*?\*/` between the keywords |
| `sqli_unquoted` | 9000014 | `OR 1=1` without quotes; the rule needs a `'` | a numeric-tautology variant (higher FP risk: test against the baseline) |
| `sqli_post_body` | 9000013/14 | the rules read the URI only, not the request body | `http.request_body` variants |
| `sqli_blind_browser_ua` | 9000015 | time-based blind SQLi (`AND SLEEP(5)`) with a browser user agent: no UNION, no quote, no scanner UA | a `sleep(`/`benchmark(`/`waitfor delay` rule |
| `stolen_member_key` | all | a valid key from an unknown source is a normal login (5715, level 3) | source allow-list per user, or alert on logins not from the VPN range |

Closed on 10 November (were known misses, now positive tests): brute force on key-only hosts (100111/100112) and switching to `rocky` with `su`/`sudo -u` (100113).

**Brute force on key-only hosts: why it needed a team rule.** With password login off, sshd logs a rejected login to an existing account only as `Connection closed by authenticating user <u> <ip> port <n> [preauth]`. Wazuh files that as 5722 (level 0), and the built-in brute-force rules (5712/5763) never see it. Two Wazuh behaviours shaped the fix, both found by tests: the stock decoder extracts no source address from this line, so the burst is counted **per host**, not per source (the address is still in the alert's full log); and Wazuh doesn't count level-0 events towards a frequency rule, so 100111 is level 3.

Not testable with `wazuh-logtest`: **slow** attacks (e.g. one rejected login every 20 s, which never reaches 8 in 2 min). logtest times events by arrival, not by the log timestamp, so spacing lines out has no effect. The rule's window is 2 min, so anything slower is a known miss by design.

Not testable with a pcap, recorded here: everything to the platform over **HTTPS** (below), and traffic **inside the cluster** (pod to pod, node to node), which never passes edge-01's Suricata.

## Limits (recorded, not hidden)

- **HTTPS:** the student platform is served over TLS that terminates at Traefik inside the cluster. Suricata on edge-01 sees only encrypted bytes for it, so the HTTP rules (9000012–9000015) cover plaintext HTTP only. Detecting web attacks on the platform needs its application logs in Wazuh, which is a separate change.
- **Thresholds** (9000010, 9000011) are starting points. Tune them only against a recorded baseline (`docs/week5-runbook.md`, step 4), never during an exercise.

## Running the tests

The tests use synthetic traffic and log lines with RFC 5737 documentation addresses only. Nothing is sent on any network.

```bash
pip install scapy==2.6.1
python3 project/detections/make_pcaps.py /tmp/w5pcaps
# CI: the same engine versions as edge-01, in containers pinned by digest (.github/workflows/detections.yml)
# On edge-01 against the deployed engines (read-only):
python3 project/detections/run_tests.py suricata --work /tmp/w5pcaps --cmd "sudo suricata"
python3 project/detections/run_tests.py wazuh --cmd "sudo /var/ossec/bin/wazuh-logtest"
```
