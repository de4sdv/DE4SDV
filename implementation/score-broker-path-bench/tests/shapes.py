"""Real output shapes of the tools the bench scripts run, for the tests.

Each constant is text a tool printed: ``ss`` on this development host and in
the feasibility runs of 2026-10-28, ``nft list table`` of those runs (with
``-a`` handles added where the script asks for them), ``ip -o`` listings as
Android and Linux print them. The /proc builder writes the files the
ASM-MW-031 scan reads, in their kernel formats (NUL-separated environ and
cmdline, maps lines). Nothing here is evidence; it only keeps the tests on
the shapes the scripts meet.
"""

from __future__ import annotations

import os
from pathlib import Path

# ss -H -u -l -n -p on this host (one protocol: no Netid column).
SS_UDP_HOST = (
    "UNCONN 0      0                          0.0.0.0:30160 0.0.0.0:* users:((\"python3\",pid=1292790,fd=3)) \n"
    "UNCONN 0      0                                *:30161       *:* users:((\"python3\",pid=1292790,fd=4)) \n"
    "UNCONN 0      0                       127.0.0.53:53    0.0.0.0:*                                      \n"
)
# ss -H -u -t -l -n -p on this host (two protocols: a Netid column).
SS_BOTH_HOST = (
    "udp UNCONN 0      0                          0.0.0.0:30160 0.0.0.0:* users:((\"python3\",pid=1292790,fd=3))      \n"
    "udp UNCONN 0      0                                *:30161       *:* users:((\"python3\",pid=1292790,fd=4))      \n"
    "tcp LISTEN 0      1                          0.0.0.0:4721  0.0.0.0:* users:((\"python3\",pid=1292790,fd=5))      \n"
)
# ss -H -t -l -n -p of the feasibility host (t8_isolation.log).
SS_TCP_SPIKE = (
    "LISTEN 0      4096            192.168.98.1:30509      0.0.0.0:*    users:((\"someipd\",pid=11224,fd=23))      \n"
    "LISTEN 0      1                  127.0.0.1:4721       0.0.0.0:*    users:((\"python3\",pid=11257,fd=3))       \n"
    "LISTEN 0      128                  0.0.0.0:22         0.0.0.0:*                                             \n"
    "LISTEN 0      128                     [::]:22            [::]:*                                             \n"
    "LISTEN 0      4096                       *:1443             *:*                                             \n"
)
# The claims review's line (repro/ss_layer.txt): the adapter, comm truncated to 15.
SS_LAYER_CLAIMS = "UNCONN 0      0        0.0.0.0:30160      0.0.0.0:*    users:((\"de4sdv_score_ad\",pid=11,fd=3))\n"
# The integration harness ground truth (probe-runs-v2/*/ss_listeners.txt).
SS_UDP_HARNESS = "UNCONN 0      0      0.0.0.0:30160 0.0.0.0:* users:((\"adapter\",pid=1257259,fd=3))\n"
SS_TCP_HARNESS = "LISTEN 0      1      0.0.0.0:4721 0.0.0.0:* users:((\"nc\",pid=1257260,fd=3))\n"
# ss -H -t -n -p state established '( sport = :4721 )' and '( dport = :4721 )'
# on this host: one state selected, so no State column.
SS_SPORT_HOST = "0      0      127.0.0.1:4721 127.0.0.1:33766 users:((\"python3\",pid=1292790,fd=7))\n"
SS_DPORT_HOST = "0      0      127.0.0.1:33766 127.0.0.1:4721 users:((\"python3\",pid=1292790,fd=6))\n"

# The layer's DDS sockets as a running adapter binds them (one participant:
# the two multicast ports and two unicast ports), with Netid.
SS_LAYER_ADAPTER = (
    "UNCONN 0      0                          0.0.0.0:30150 0.0.0.0:* users:((\"de4sdv_score_ad\",pid=4101,fd=7))\n"
    "UNCONN 0      0                          0.0.0.0:30151 0.0.0.0:* users:((\"de4sdv_score_ad\",pid=4101,fd=8))\n"
    "UNCONN 0      0                          0.0.0.0:30160 0.0.0.0:* users:((\"de4sdv_score_ad\",pid=4101,fd=9))\n"
    "UNCONN 0      0                          0.0.0.0:30161 0.0.0.0:* users:((\"de4sdv_score_ad\",pid=4101,fd=10))\n"
)
SS_OTHER_ROS = "UNCONN 0      0                          0.0.0.0:30162 0.0.0.0:* users:((\"component_conta\",pid=4200,fd=9))\n"
SS_TCP_ASSEMBLER = "LISTEN 0      1                          0.0.0.0:4721  0.0.0.0:* users:((\"python3\",pid=4300,fd=5))\n"

# nft list table inet de4sdv_bench of the feasibility run (counters, no -a).
NFT_TABLE_SPIKE = """table inet de4sdv_bench {
\tset dds_domain91_udp {
\t\ttype inet_service
\t\tflags interval
\t\telements = { 30150-30151, 30160-30401 }
\t}

\tchain input {
\t\ttype filter hook input priority filter; policy accept;
\t\tiifname "cvd-ebr" ip saddr 192.168.98.0/24 udp dport @dds_domain91_udp counter packets 8 bytes 396 drop comment "DDS d91 from guest eth1 segment"
\t\tip saddr { 192.168.99.0-192.168.101.255 } udp dport @dds_domain91_udp counter packets 0 bytes 0 drop comment "DDS d91 from guest SDV VLAN subnets"
\t}
}
"""


def nft_table(dds_packets: int, tcp_packets: int, *, duplicate: bool = False) -> str:
    """``nft -a list table inet de4sdv_bench`` of the bench's table, with counters."""
    lines = [
        "table inet de4sdv_bench { # handle 7",
        "\tset dds_domain_udp { # handle 1",
        "\t\ttype inet_service",
        "\t\tflags interval",
        "\t\telements = { 30150-30151, 30160-30401 }",
        "\t}",
        "",
        "\tchain input { # handle 2",
        "\t\ttype filter hook input priority filter; policy accept;",
        "\t\tiifname \"lo\" accept # handle 3",
        f"\t\tudp dport @dds_domain_udp counter packets {dds_packets} bytes {dds_packets * 62} drop comment "
        "\"REQ-MW-016: DDS ports off the guest, every interface but lo\" # handle 4",
        f"\t\ttcp dport 4721 counter packets {tcp_packets} bytes {tcp_packets * 60} drop comment "
        "\"ASM-MW-029: frame assembler off the guest\" # handle 5",
    ]
    if duplicate:
        lines += [
            "\t\tudp dport @dds_domain_udp counter packets 0 bytes 0 drop comment "
            "\"REQ-MW-016: DDS ports off the guest, every interface but lo\" # handle 6",
            "\t\ttcp dport 4721 counter packets 0 bytes 0 drop comment \"ASM-MW-029: frame assembler off the guest\" # handle 7",
        ]
    lines += ["\t}", "}", ""]
    return "\n".join(lines)


NFT_TABLE_TWO_ADDS = nft_table(16, 4, duplicate=True)
NFT_TABLE_WITHOUT_COUNTERS = """table inet de4sdv_bench { # handle 7
\tchain input { # handle 2
\t\ttype filter hook input priority filter; policy accept;
\t\tiifname "lo" accept # handle 3
\t\tudp dport @dds_domain_udp drop # handle 4
\t}
}
"""

# The guest inventory the probe records: per namespace, ip -o link and ip -o -4 addr.
GUEST_INVENTORY_IVI = """# netns:
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000\\    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
14: buried_eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP mode DEFAULT group default qlen 1000\\    link/ether 00:1a:11:e1:ce:02 brd ff:ff:ff:ff:ff:ff
16: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP mode DEFAULT group default qlen 1000\\    link/ether 00:1a:11:e1:cf:02 brd ff:ff:ff:ff:ff:ff
18: sdv_rpc@eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP mode DEFAULT group default qlen 1000\\    link/ether 00:1a:11:e1:cf:02 brd ff:ff:ff:ff:ff:ff
19: wlan0: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN mode DEFAULT group default qlen 1000\\    link/ether 02:00:00:44:55:66 brd ff:ff:ff:ff:ff:ff
1: lo    inet 127.0.0.1/8 scope host lo\\       valid_lft forever preferred_lft forever
14: buried_eth0    inet 192.168.97.2/24 brd 192.168.97.255 scope global buried_eth0\\       valid_lft forever preferred_lft forever
16: eth1    inet 192.168.98.118/24 brd 192.168.98.255 scope global eth1\\       valid_lft forever preferred_lft forever
18: sdv_rpc    inet 192.168.101.4/24 brd 192.168.101.255 scope global sdv_rpc\\       valid_lft forever preferred_lft forever
# netns: sd_mesh_ns
1: lo: <LOOPBACK> mtu 65536 qdisc noop state DOWN mode DEFAULT group default qlen 1000\\    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
17: sd_mesh@if16: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP mode DEFAULT group default qlen 1000\\    link/ether 00:1a:11:e1:cf:02 brd ff:ff:ff:ff:ff:ff link-netnsid 0
17: sd_mesh    inet 192.168.99.4/24 brd 192.168.99.255 scope global sd_mesh\\       valid_lft forever preferred_lft forever
# netns: sdv_dt_ns
1: lo: <LOOPBACK> mtu 65536 qdisc noop state DOWN mode DEFAULT group default qlen 1000\\    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
15: sdv_dt@if16: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP mode DEFAULT group default qlen 1000\\    link/ether 00:1a:11:e1:cf:02 brd ff:ff:ff:ff:ff:ff link-netnsid 0
15: sdv_dt    inet 192.168.100.4/24 brd 192.168.100.255 scope global sdv_dt\\       valid_lft forever preferred_lft forever
"""

# ip -o -4 addr show on the bench host (the cvd-* interfaces and others).
HOST_IP_ADDR = """1: lo    inet 127.0.0.1/8 scope host lo\\       valid_lft forever preferred_lft forever
2: ens4    inet 10.164.0.2/32 metric 100 scope global dynamic ens4\\       valid_lft 3355sec preferred_lft 3355sec
5: cvd-ebr    inet 192.168.98.1/24 brd 192.168.98.255 scope global cvd-ebr\\       valid_lft forever preferred_lft forever
9: cvd-mtap-03    inet 192.168.97.1/30 brd 192.168.97.3 scope global cvd-mtap-03\\       valid_lft forever preferred_lft forever
10: cvd-wtap-02    inet 192.168.96.1/30 brd 192.168.96.3 scope global cvd-wtap-02\\       valid_lft forever preferred_lft forever
11: docker0    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0\\       valid_lft forever preferred_lft forever
"""

# --------------------------------------------------------------- /proc

_HUMBLE_LIBS = [
    "aaaab0000000-aaaab0001000 r-xp 00000000 103:02 1001 /opt/ros/humble/lib/librcl.so",
    "aaaab0002000-aaaab0003000 r-xp 00000000 103:02 1002 /opt/ros/humble/lib/librmw_cyclonedds_cpp.so",
    "aaaab0004000-aaaab0005000 r-xp 00000000 103:02 1003 /opt/ros/humble/lib/libddsc.so.0.10.5",
]
ROS_HUMBLE_ADAPTER = {
    "pid": 4101, "cmdline": ["/tmp/de4sdv-score-bench/bin/de4sdv_score_adapter", "--mw-com-config", "x.json"],
    "environ": {"RMW_IMPLEMENTATION": "rmw_cyclonedds_cpp", "ROS_DOMAIN_ID": "91", "ROS_DISTRO": "humble",
                "CYCLONEDDS_URI": "file://{cyclonedds}"},
    "maps": _HUMBLE_LIBS,
}
ROS_HUMBLE_AUTOWARE = {
    "pid": 4200, "cmdline": ["/opt/autoware/lib/rclcpp_components/component_container_mt"],
    "environ": {"RMW_IMPLEMENTATION": "rmw_cyclonedds_cpp", "ROS_DOMAIN_ID": "91", "ROS_DISTRO": "humble",
                "CYCLONEDDS_URI": "file://{cyclonedds}", "AMENT_PREFIX_PATH": "/opt/ros/humble"},
    "maps": _HUMBLE_LIBS,
}
ROS_JAZZY_DEFAULTS = {
    "pid": 4400, "cmdline": ["/usr/bin/python3", "/opt/ros/jazzy/bin/ros2", "topic", "list"],
    "environ": {"ROS_DISTRO": "jazzy", "AMENT_PREFIX_PATH": "/opt/ros/jazzy"},
    "maps": ["aaaab0000000-aaaab0001000 r-xp 00000000 103:02 2001 /opt/ros/jazzy/lib/librcl.so"],
}
ROS_BY_MAPS_ONLY = {
    "pid": 4500, "cmdline": ["/home/bench/install/lib/observer/observer_node"],
    "environ": {"HOME": "/home/bench", "PATH": "/usr/bin"},
    "maps": _HUMBLE_LIBS,
}
PLAIN_DAEMON = {
    "pid": 812, "cmdline": ["/usr/sbin/chronyd", "-F", "1"], "environ": {"PATH": "/usr/sbin"},
    "maps": ["aaaab0000000-aaaab0001000 r-xp 00000000 103:02 3001 /usr/sbin/chronyd"],
}
UNREADABLE = {"pid": 977, "cmdline": ["/usr/lib/some/daemon"], "environ": None, "maps": None}


def fake_proc(root: Path, processes: list[dict], *, cyclonedds_index: int) -> Path:
    """A /proc tree with the files the ASM-MW-031 scan reads, in their kernel formats."""
    proc = root / "proc"
    proc.mkdir(parents=True, exist_ok=True)
    cyclonedds = root / "cyclonedds.xml"
    cyclonedds.write_text(
        "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n<CycloneDDS xmlns=\"https://cdds.io/config\">\n"
        "  <Domain Id=\"any\">\n    <General><Interfaces><NetworkInterface name=\"lo\"/></Interfaces>"
        "<AllowMulticast>false</AllowMulticast></General>\n"
        f"    <Discovery><ParticipantIndex>auto</ParticipantIndex>"
        f"<MaxAutoParticipantIndex>{cyclonedds_index}</MaxAutoParticipantIndex></Discovery>\n"
        "  </Domain>\n</CycloneDDS>\n")
    for entry in processes:
        directory = proc / str(entry["pid"])
        directory.mkdir()
        (directory / "cmdline").write_bytes(b"\0".join(part.encode() for part in entry["cmdline"]) + b"\0")
        if entry["environ"] is None:
            for name in ("environ", "maps"):
                path = directory / name
                path.write_text("")
                os.chmod(path, 0)
            continue
        environ = {key: value.replace("{cyclonedds}", str(cyclonedds)) for key, value in entry["environ"].items()}
        (directory / "environ").write_bytes(b"".join(f"{k}={v}".encode() + b"\0" for k, v in environ.items()))
        (directory / "maps").write_text("\n".join(entry["maps"]) + "\n")
    (proc / "self").mkdir()  # not a pid directory; the scan skips it
    return proc
