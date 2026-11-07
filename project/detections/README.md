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
| 5712 / 5763 | Wazuh built-in | SSH brute force (invalid user / failed password) | T1110 | `ssh_*_bruteforce_then_success` | user mistyping a password 8 times |
| 40112 | Wazuh built-in | authentication failures followed by a success, same source (level 12) | T1110, T1078 | `ssh_*_bruteforce_then_success` | user who finally gets the password right |

Negative tests: `benign` (normal browsing and 3 SSH sessions) must trigger **no** team SID; a non-team Suricata alert must stay at 86601; a normal login must not trigger 40112.

**Duplicates are not added.** A team rule for "SSH success after brute force" was written first, but Wazuh's built-in 40112 already catches the pattern and wins, so the team rule could never fire. It was removed, and the tests assert 40112 instead.

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
