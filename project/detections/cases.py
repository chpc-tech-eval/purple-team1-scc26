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

# Known misses (false negatives, documented on purpose). Each is an attack
# variant the current rules are EXPECTED to miss. run_tests.py reports them as
# "miss"; if one starts being detected (a rule improved), it fails, so the
# catalogue in README.md is updated in the same change.
# name -> (description, team SID it evades)
SURICATA_MISS = {
    "slow_scan": ("60 SYNs 0.3 s apart (~18 s, like nmap -T2): never 40 in 10 s", 9000010),
    "distributed_scan": ("60 SYNs in 2 s split over 4 sources: the threshold counts per source", 9000010),
    "udp_scan": ("60 UDP probes to 60 ports in 2 s: the scan rule is TCP only", 9000010),
    "slow_ssh": ("9 new SSH connections in 60 s: one under the threshold", 9000011),
    "traversal_double_encoded": ("%252e%252e%252f: double-encoded traversal", 9000012),
    "sqli_union_comment": ("UNION/**/SELECT: a comment instead of whitespace", 9000013),
    "sqli_unquoted": ("?id=1 OR 1=1 without quotes: 9000014 needs a quote", 9000014),
    "sqli_post_body": ("tautology in a POST body: the SQLi rules read the URI only", 9000014),
    "sqli_blind_browser_ua": ("time-based blind SQLi (AND SLEEP(5)) sent with a browser user agent", 9000015),
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
    return f"Nov  7 08:{n // 60:02d}:{n % 60:02d} edge-01 sshd[{4000 + n}]: {msg}"


def _preauth(n, user, port):
    """What sshd logs on a key-only host when a login to an existing user is rejected."""
    return _sshd(n, f"Connection closed by authenticating user {user} {ATTACKER} port {port} [preauth]")


def _pam(prog, n, service, user, by):
    """A PAM session line, e.g. su - rocky or sudo -u rocky."""
    uid = 0 if user == "root" else 1000
    return (f"Nov  7 08:00:{n:02d} edge-01 {prog}[{4100 + n}]: pam_unix({service}:session): "
            f"session opened for user {user}(uid={uid}) by {by}(uid=1001)")


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
        "invalid-user brute force (5712) followed by a successful login (built-in 40112)",
        [_sshd(i, f"Invalid user admin{i} from {ATTACKER} port {50000 + i}") for i in range(10)]
        + [_sshd(20, f"Accepted password for ubuntu from {ATTACKER} port 50100 ssh2")],
        {"5712", "40112"}, set(),
    ),
    "ssh_password_bruteforce_then_success": (
        "failed-password brute force on a real user (5763) followed by a successful login (40112)",
        [_sshd(i, f"Failed password for ubuntu from {ATTACKER} port {51000 + i} ssh2") for i in range(10)]
        + [_sshd(20, f"Accepted password for ubuntu from {ATTACKER} port 51100 ssh2")],
        {"5763", "40112"}, set(),
    ),
    "ssh_success_without_bruteforce": (
        "a normal login from another source is not escalated",
        [_sshd(1, f"Accepted publickey for ubuntu from {CLIENT} port 50200 ssh2: ED25519 SHA256:abc")],
        {"5715"}, {"40112", "100110"},
    ),
    "break_glass_login": (
        "any login as the shared break-glass account rocky alerts (100110)",
        [_sshd(1, f"Accepted publickey for rocky from {CLIENT} port 50300 ssh2: ED25519 SHA256:abc")],
        {"100110"}, {"40112"},
    ),
    "break_glass_bruteforce_then_success": (
        "a brute force on rocky still correlates (5763, 40112): failures are left to the built-ins",
        [_sshd(i, f"Failed password for rocky from {ATTACKER} port {52000 + i} ssh2") for i in range(10)]
        + [_sshd(20, f"Accepted password for rocky from {ATTACKER} port 52100 ssh2")],
        {"5760", "5763", "40112"}, set(),
    ),
    "break_glass_lookalike": (
        "a member whose name only contains 'rocky' is not treated as break-glass",
        [_sshd(1, f"Accepted publickey for rockyb from {CLIENT} port 50500 ssh2: ED25519 SHA256:abc"),
         _pam("su", 2, "su-l", "rockyb", "member1")],
        {"5715", "5501"}, {"100110", "100113"},
    ),
    "su_to_rocky": (
        "a member switches to rocky with su - rocky (100113)",
        [_pam("su", 1, "su-l", "rocky", "member1")],
        {"100113"}, set(),
    ),
    "sudo_as_rocky": (
        "a member runs a shell as rocky with sudo -u rocky (100113 on the PAM session line)",
        [f"Nov  7 08:00:01 edge-01 sudo[4001]:  member1 : TTY=pts/0 ; PWD=/home/member1 ; USER=rocky ; COMMAND=/bin/bash",
         _pam("sudo", 2, "sudo", "rocky", "member1")],
        {"100113"}, set(),
    ),
    "rocky_sudo_to_root_not_switch": (
        "rocky running sudo to root (what Ansible does) is not a switch to rocky; its SSH login already alerts",
        [_pam("sudo", 1, "sudo", "root", "rocky")],
        {"5501"}, {"100113"},
    ),
    "rocky_ssh_pam_line_not_switch": (
        "sshd's own PAM line for a rocky login is left to 100110, not counted twice",
        [f"Nov  7 08:00:01 edge-01 sshd[4001]: pam_unix(sshd:session): session opened for user rocky(uid=1000) by (uid=0)"],
        {"5501"}, {"100113"},
    ),
    "key_only_bruteforce": (
        "12 rejected logins to existing accounts in 12 s on a key-only host (100112)",
        [_preauth(i, "ubuntu" if i % 2 else "rocky", 53000 + i) for i in range(12)],
        {"100112"}, set(),
    ),
    "key_only_below_threshold": (
        "7 rejected logins (a member with a wrong key retrying) stay below the burst rule",
        [_preauth(i, "member1", 53100 + i) for i in range(7)],
        set(), {"100112"},
    ),
    "preauth_probe_not_bruteforce": (
        "12 plain connect-and-close probes (no login attempted) are not counted as login failures",
        [_sshd(i, f"Connection closed by {ATTACKER} port {53200 + i} [preauth]") for i in range(12)],
        {"5722"}, {"100111", "100112"},
    ),
}


# Wazuh known misses: name -> (description, log lines). A case is a miss while
# no rule of level >= WAZUH_ALERT_LEVEL fires on any of its lines.
# Slow attacks can't be cases here: wazuh-logtest times events by arrival, not
# by the syslog timestamp, so spacing lines out in the text has no effect.
WAZUH_ALERT_LEVEL = 7
WAZUH_MISS = {
    "stolen_member_key": (
        "a stolen member key used from an unknown source looks like a normal login (5715, level 3)",
        [_sshd(1, f"Accepted publickey for member1 from {ATTACKER} port 53100 ssh2: ED25519 SHA256:stolen")],
    ),
}
