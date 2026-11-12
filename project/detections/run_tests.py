#!/usr/bin/env python3
"""Run the Week-5 detection tests against the real engines.

Suricata: replays each generated pcap (make_pcaps.py) through Suricata with
the team rules and checks which SIDs fired. Wazuh: feeds each case's log
lines into one wazuh-logtest session and checks which rule IDs fired.

Known misses (cases.SURICATA_MISS, cases.WAZUH_MISS) are attack variants the
rules are expected NOT to catch. They print as "miss"; one that starts being
detected prints FAIL, so README.md's false-negative list is updated with it.

  # CI (containers):
  run_tests.py suricata --work /tmp/w --cmd "docker run --rm -v /tmp/w:/w --entrypoint suricata IMAGE" --mount /w
  run_tests.py wazuh --cmd "docker exec -i wazuh /var/ossec/bin/wazuh-logtest"
  # edge-01 (live engines, nothing sent on the network):
  run_tests.py suricata --work /tmp/w --cmd "sudo suricata"
  run_tests.py wazuh --cmd "sudo /var/ossec/bin/wazuh-logtest"
"""
import argparse
import json
import pathlib
import re
import shlex
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from cases import HOME_NET, SURICATA, SURICATA_MISS, TEAM_SIDS, WAZUH, WAZUH_ALERT_LEVEL, WAZUH_MISS  # noqa: E402

ROLE = REPO / "infrastructure/ansible/roles/suricata"
PHASE3 = re.compile(r"\*\*Phase 3: Completed filtering \(rules\)\.\s*\n\s*id: '(\d+)'")
PHASE3_LEVEL = re.compile(r"\*\*Phase 3: Completed filtering \(rules\)\.\s*\n\s*id: '(\d+)'\s*\n\s*level: '(\d+)'")


def team_rules():
    """The exact rule text Ansible deploys: rendered drill rule + detections file."""
    defaults = (ROLE / "defaults/main.yml").read_text(encoding="utf-8")
    var = lambda k: re.search(rf"^{k}:\s*(\S+)", defaults, re.M).group(1).strip("\"'")  # noqa: E731
    drill = (ROLE / "templates/local.rules.j2").read_text(encoding="utf-8")
    drill = drill.replace("{{ suricata_drill_marker }}", var("suricata_drill_marker"))
    drill = drill.replace("{{ suricata_drill_sid }}", var("suricata_drill_sid"))
    return drill + "\n" + (ROLE / "files/scc26-detections.rules").read_text(encoding="utf-8")


def run(cmd, **kw):
    return subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=300, **kw)


def suricata(a):
    work = pathlib.Path(a.work)
    mount = a.mount or str(work)
    (work / "team.rules").write_text(team_rules(), encoding="utf-8")
    common = f"-S {mount}/team.rules -k none --set vars.address-groups.HOME_NET={HOME_NET}"
    t = run(f"{a.cmd} -T {common}")
    if t.returncode != 0:
        print(t.stdout[-3000:], t.stderr[-3000:], sep="\n")
        print("FAIL: Suricata rejected the team rules (-T)")
        return 1
    print("ok   suricata -T accepts the team rules")

    def replay(name):
        """Replay one pcap; return (result, alert SIDs, flows seen)."""
        out = work / f"out-{name}"
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        out.chmod(0o777)
        r = run(f"{a.cmd} -r {mount}/{name}.pcap -l {mount}/out-{name} --runmode single {common}")
        eve = out / "eve.json"
        fired, flows = set(), 0
        if eve.exists():
            for line in eve.read_text(encoding="utf-8").splitlines():
                e = json.loads(line)
                if e.get("event_type") == "alert":
                    fired.add(e["alert"]["signature_id"])
                flows += e.get("event_type") == "flow"
        return r, fired, flows

    failures = 0
    for name, (desc, must, must_not) in SURICATA.items():
        r, fired, _ = replay(name)
        missing, unwanted = must - fired, must_not & fired
        ok = r.returncode == 0 and not missing and not unwanted
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name}: {desc}; fired={sorted(fired)}"
              + (f" missing={sorted(missing)}" if missing else "")
              + (f" unwanted={sorted(unwanted)}" if unwanted else "")
              + (f" rc={r.returncode} {r.stderr[-500:]}" if r.returncode else ""))
    for name, (desc, evaded) in SURICATA_MISS.items():
        r, fired, flows = replay(name)
        caught = fired & TEAM_SIDS
        # A miss only counts if Suricata really saw the traffic (no hollow pass).
        ok = r.returncode == 0 and flows > 0 and not caught
        failures += not ok
        print(f"{'miss' if ok else 'FAIL'} {name}: {desc}; evades {evaded}; fired={sorted(fired)}"
              + (f" NOW DETECTED by {sorted(caught)}: move it to SURICATA and update README.md" if caught else "")
              + ("" if flows else " NO FLOWS: Suricata did not see the traffic")
              + (f" rc={r.returncode} {r.stderr[-500:]}" if r.returncode else ""))
    return 1 if failures else 0


def wazuh(a):
    failures = 0
    for name, (desc, lines, must, must_not) in WAZUH.items():
        r = run(a.cmd, input="\n".join(lines) + "\n")
        # wazuh-logtest prints its results on stderr.
        fired = set(PHASE3.findall(r.stdout + "\n" + r.stderr))
        missing, unwanted = must - fired, must_not & fired
        ok = not missing and not unwanted
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name}: {desc}; fired={sorted(fired, key=int)}"
              + (f" missing={sorted(missing)}" if missing else "")
              + (f" unwanted={sorted(unwanted)}" if unwanted else ""))
        if not ok and a.verbose:
            print(r.stdout[-4000:], r.stderr[-2000:], sep="\n")
    for name, (desc, lines) in WAZUH_MISS.items():
        r = run(a.cmd, input="\n".join(lines) + "\n")
        hits = {(i, int(lvl)) for i, lvl in PHASE3_LEVEL.findall(r.stdout + "\n" + r.stderr)}
        alerts = sorted(i for i, lvl in hits if lvl >= WAZUH_ALERT_LEVEL)
        ok = bool(hits) and not alerts
        failures += not ok
        print(f"{'miss' if ok else 'FAIL'} {name}: {desc}; fired={sorted(f'{i}/L{lvl}' for i, lvl in hits)}"
              + (f" NOW DETECTED by {alerts}: move it to WAZUH and update README.md" if alerts else "")
              + ("" if hits else " (no output from wazuh-logtest)"))
    return 1 if failures else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="engine", required=True)
    s = sub.add_parser("suricata")
    s.add_argument("--work", required=True, help="directory holding the pcaps (make_pcaps.py output)")
    s.add_argument("--cmd", required=True, help="command that runs suricata")
    s.add_argument("--mount", help="path of --work as seen by --cmd (containers)")
    w = sub.add_parser("wazuh")
    w.add_argument("--cmd", required=True, help="command that runs wazuh-logtest")
    w.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    return suricata(a) if a.engine == "suricata" else wazuh(a)


if __name__ == "__main__":
    sys.exit(main())
