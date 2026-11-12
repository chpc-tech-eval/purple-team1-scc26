#!/usr/bin/env python3
"""Write one synthetic pcap per Suricata test case (cases.SURICATA and the
known misses in cases.SURICATA_MISS).

  python3 make_pcaps.py <out-dir>

Needs scapy. Full TCP handshakes with correct sequence numbers, so Suricata
reassembles the streams and parses HTTP exactly as on the wire.
"""
import pathlib
import sys

from scapy.all import IP, TCP, UDP, Raw, wrpcap  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cases import ATTACKER, CLIENT, SURICATA, SURICATA_MISS, TARGET  # noqa: E402

T0 = 1_794_038_400.0  # 2026-11-07T08:00:00Z


class Clock:
    def __init__(self, t=T0):
        self.t = t

    def tick(self, dt=0.001):
        self.t += dt
        return self.t


def stamp(pkt, clock, dt=0.001):
    pkt.time = clock.tick(dt)
    return pkt


def session(clock, src, dst, sport, dport, request=b"", response=b""):
    """A complete TCP conversation: handshake, one request, one response, FIN."""
    pkts, c, s = [], 1000, 5000
    ip_c, ip_s = IP(src=src, dst=dst), IP(src=dst, dst=src)
    pkts.append(stamp(ip_c / TCP(sport=sport, dport=dport, flags="S", seq=c), clock))
    pkts.append(stamp(ip_s / TCP(sport=dport, dport=sport, flags="SA", seq=s, ack=c + 1), clock))
    c, s = c + 1, s + 1
    pkts.append(stamp(ip_c / TCP(sport=sport, dport=dport, flags="A", seq=c, ack=s), clock))
    if request:
        pkts.append(stamp(ip_c / TCP(sport=sport, dport=dport, flags="PA", seq=c, ack=s) / Raw(request), clock))
        c += len(request)
        pkts.append(stamp(ip_s / TCP(sport=dport, dport=sport, flags="A", seq=s, ack=c), clock))
    if response:
        pkts.append(stamp(ip_s / TCP(sport=dport, dport=sport, flags="PA", seq=s, ack=c) / Raw(response), clock))
        s += len(response)
        pkts.append(stamp(ip_c / TCP(sport=sport, dport=dport, flags="A", seq=c, ack=s), clock))
    pkts.append(stamp(ip_c / TCP(sport=sport, dport=dport, flags="FA", seq=c, ack=s), clock))
    pkts.append(stamp(ip_s / TCP(sport=dport, dport=sport, flags="FA", seq=s, ack=c + 1), clock))
    pkts.append(stamp(ip_c / TCP(sport=sport, dport=dport, flags="A", seq=c + 1, ack=s + 1), clock))
    return pkts


def http_get(path, ua="Mozilla/5.0 (X11; Linux x86_64) Firefox/140.0"):
    return (f"GET {path} HTTP/1.1\r\nHost: platform.example\r\nUser-Agent: {ua}\r\nAccept: */*\r\n\r\n").encode()


def http_post(path, body, ua="Mozilla/5.0 (X11; Linux x86_64) Firefox/140.0"):
    return (f"POST {path} HTTP/1.1\r\nHost: platform.example\r\nUser-Agent: {ua}\r\n"
            f"Content-Type: application/x-www-form-urlencoded\r\nContent-Length: {len(body)}\r\n\r\n{body}").encode()


OK = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nok"
NOT_FOUND = b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n"
SSH_BANNER = b"SSH-2.0-OpenSSH_9.9\r\n"


def build(name):
    clock, pkts = Clock(), []
    web = lambda req, resp=NOT_FOUND, src=ATTACKER, port=40000: session(clock, src, TARGET, port, 80, req, resp)  # noqa: E731
    if name == "syn_scan":
        for i, port in enumerate(range(1, 61)):
            pkts.append(stamp(IP(src=ATTACKER, dst=TARGET) / TCP(sport=41000 + i, dport=port, flags="S", seq=1), clock, 0.03))
    elif name == "ssh_burst":
        for i in range(15):
            pkts += session(clock, ATTACKER, TARGET, 42000 + i, 22, SSH_BANNER, SSH_BANNER)
            clock.tick(2.0)
    elif name == "traversal":
        pkts += web(http_get("/static/../../etc/passwd"))
        pkts += web(http_get("/static/%2e%2e%2f%2e%2e%2fetc%2fpasswd"), port=40001)
    elif name == "sqli_union":
        pkts += web(http_get("/api/items?id=1%20UNION%20SELECT%20username,password%20FROM%20users"))
    elif name == "sqli_tautology":
        pkts += web(http_get("/api/login?user=a'%20OR%20'1'='1"))
    elif name == "scanner_ua":
        pkts += web(http_get("/", ua="sqlmap/1.8.11#stable (https://sqlmap.org)"))
    elif name == "drill":
        pkts += web(http_get("/scc26-ids-drill"))
    elif name == "benign":
        for i, path in enumerate(["/", "/home/", "/api/me", "/static/app.css", "/crypty/", "/api/items?id=42"]):
            pkts += web(http_get(path), OK, src=CLIENT, port=43000 + i)
            clock.tick(1.5)
        for i in range(3):
            pkts += session(clock, CLIENT, TARGET, 44000 + i, 22, SSH_BANNER, SSH_BANNER)
            clock.tick(20.0)
    # --- known misses (cases.SURICATA_MISS): expected to trigger no team SID ---
    elif name == "slow_scan":
        for i, port in enumerate(range(1, 61)):
            pkts.append(stamp(IP(src=ATTACKER, dst=TARGET) / TCP(sport=41000 + i, dport=port, flags="S", seq=1), clock, 0.3))
    elif name == "distributed_scan":
        for i, port in enumerate(range(1, 61)):
            src = f"198.51.100.{50 + i % 4}"
            pkts.append(stamp(IP(src=src, dst=TARGET) / TCP(sport=41000 + i, dport=port, flags="S", seq=1), clock, 0.03))
    elif name == "udp_scan":
        for i, port in enumerate(range(1, 61)):
            pkts.append(stamp(IP(src=ATTACKER, dst=TARGET) / UDP(sport=41000 + i, dport=port), clock, 0.03))
    elif name == "slow_ssh":
        for i in range(9):
            pkts += session(clock, ATTACKER, TARGET, 42000 + i, 22, SSH_BANNER, SSH_BANNER)
            clock.tick(6.0)
    elif name == "traversal_double_encoded":
        pkts += web(http_get("/static/%252e%252e%252f%252e%252e%252fetc%252fpasswd"))
    elif name == "sqli_union_comment":
        pkts += web(http_get("/api/items?id=1%20UNION/**/SELECT/**/username,password%20FROM%20users"))
    elif name == "sqli_unquoted":
        pkts += web(http_get("/api/items?id=1%20OR%201=1"))
    elif name == "sqli_post_body":
        pkts += web(http_post("/api/login", "user=a'%20OR%20'1'='1&password=x"))
    elif name == "sqli_blind_browser_ua":
        pkts += web(http_get("/api/items?id=1%20AND%20SLEEP(5)"))
    else:
        raise KeyError(name)
    return pkts


def main(out):
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for name in [*SURICATA, *SURICATA_MISS]:
        wrpcap(str(out / f"{name}.pcap"), build(name))
        print(f"wrote {name}.pcap")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "pcaps")
