"""Detection test cases (Week 5). Synthetic, harmless traffic and log lines.

Only RFC 5737 documentation addresses: 198.51.100.0/24 plays the source,
192.0.2.0/24 the protected network (the tests set HOME_NET to it).
"""
import json

ATTACKER = "198.51.100.23"
CLIENT = "198.51.100.40"
TARGET = "192.0.2.10"
HOME_NET = "[192.0.2.0/24]"
TEAM_SIDS = set(range(9000010, 9000020))

# name -> (description, sids that MUST fire, team sids that must NOT fire)
SURICATA = {
    "syn_scan": ("60 SYNs to 60 ports in 2 s from one source", {9000010}, TEAM_SIDS - {9000010}),
    "ssh_burst": ("15 new SSH connections in 30 s from one source", {9000011}, TEAM_SIDS - {9000011}),
    "traversal": ("GET with ../ and %2e%2e%2f in the URI", {9000012}, TEAM_SIDS - {9000012}),
    "sqli_union": ("GET ?id=1 UNION SELECT ...", {9000013}, TEAM_SIDS - {9000013}),
    "sqli_tautology": ("GET ?user=a' OR '1'='1", {9000014}, TEAM_SIDS - {9000014}),
    "scanner_ua": ("GET with a sqlmap user agent", {9000015}, TEAM_SIDS - {9000015}),
    "drill": ("Week-3 drill marker (regression)", {9000001}, TEAM_SIDS),
    "benign": ("normal browsing and 3 SSH sessions: no team rule may fire", set(), TEAM_SIDS),
}


def eve_alert(sid, signature, src=ATTACKER, ts="2026-11-07T08:00:00.000000+0000"):
    return json.dumps(
        {
            "timestamp": ts,
            "flow_id": 1234567890,
            "in_iface": "eth0",
            "event_type": "alert",
            "src_ip": src,
            "src_port": 51234,
            "dest_ip": TARGET,
            "dest_port": 80,
            "proto": "TCP",
            "alert": {"action": "allowed", "gid": 1, "signature_id": sid, "rev": 1,
                      "signature": signature, "category": "Web Application Attack", "severity": 1},
        },
        separators=(",", ":"),
    )


def _sshd(n, msg):
    return f"Nov  7 08:00:{n:02d} edge-01 sshd[{4000 + n}]: {msg}"


# name -> (description, log lines fed into ONE logtest session, rule ids that
# must fire on some line, rule ids that must not fire on any line)
WAZUH = {
    "suricata_team_alert": (
        "a team Suricata alert is raised to level 10",
        [eve_alert(9000012, "SCC26 W5 HTTP path traversal attempt")],
        {"100100"}, {"100101"},
    ),
    "suricata_other_alert": (
        "a non-team Suricata alert stays at the generic 86601",
        [eve_alert(2001219, "ET SCAN Potential SSH Scan")],
        {"86601"}, {"100100"},
    ),
    "suricata_repeat_source": (
        "repeated team alerts from one source correlate (100101)",
        [eve_alert(9000013 + (i % 2), "SCC26 W5 SQL injection attempt") for i in range(5)],
        {"100100", "100101"}, set(),
    ),
    "ssh_bruteforce_then_success": (
        "invalid-user brute force (5712) followed by a successful login (100110)",
        [_sshd(i, f"Invalid user admin{i} from {ATTACKER} port {50000 + i}") for i in range(10)]
        + [_sshd(20, f"Accepted password for ubuntu from {ATTACKER} port 50100 ssh2")],
        {"5712", "100110"}, set(),
    ),
    "ssh_success_without_bruteforce": (
        "a normal login from another source is not escalated",
        [_sshd(1, f"Accepted publickey for ubuntu from {CLIENT} port 50200 ssh2: ED25519 SHA256:abc")],
        {"5715"}, {"100110"},
    ),
}
