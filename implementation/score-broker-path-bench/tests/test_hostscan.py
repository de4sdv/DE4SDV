"""Tests of the host-side readers that the VM scripts run (hostscan).

Every input is the text a real tool prints: ``ss`` with and without its
Netid and State columns, ``nft -a list table`` with counters, ``ip -o``
listings and a /proc tree. So the parser the scripts call is the parser
these tests run. The ss lines are the shapes of this host and of the
feasibility runs; the parser at e4863f71 read the peer column and turned
them into no listener at all (review R28 / R2b).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import builders as b  # noqa: E402
import shapes  # noqa: E402
from de4sdv_broker_path_bench import hostscan  # noqa: E402


# ------------------------------------------------------------------ ss

def test_ss_udp_listing_without_netid_reads_the_local_column():
    rows = hostscan.parse_ss(shapes.SS_UDP_HOST, "udp")
    ports = {row["port"]: row for row in rows}
    assert ports[30160]["address"] == "0.0.0.0"
    assert ports[30160]["processes"] == [{"name": "python3", "pid": 1292790}]
    assert ports[30161]["address"] == "*"  # a dual-stack socket on ::
    assert all(row["protocol"] == "udp" for row in rows)


def test_ss_listing_with_netid_reads_the_same_columns():
    rows = hostscan.parse_ss(shapes.SS_BOTH_HOST, None)
    by_port = {(row["protocol"], row["port"]) for row in rows}
    assert ("udp", 30160) in by_port and ("udp", 30161) in by_port and ("tcp", 4721) in by_port


def test_ss_feasibility_lines_with_and_without_users():
    rows = hostscan.parse_ss(shapes.SS_TCP_SPIKE, "tcp")
    ports = {row["port"]: row for row in rows}
    assert ports[30509]["address"] == "192.168.98.1"
    assert ports[30509]["processes"][0]["name"] == "someipd"
    assert ports[22]["processes"] == []  # no users field: owner unknown
    assert ports[1443]["address"] == "*"


def test_r28_layer_listener_from_a_real_ss_line_is_listed_and_in_the_layer():
    # The claims review's line: the adapter's comm is truncated to 15 characters.
    rows = hostscan.listeners(shapes.SS_LAYER_CLAIMS, "")
    assert rows == [{"address": "0.0.0.0", "port": 30160, "protocol": "udp", "element": "de4sdv_score_ad",
                     "pid": 11, "element_in_layer": True}]


def test_r28_harness_ground_truth_listeners_are_both_recorded():
    rows = hostscan.listeners(shapes.SS_UDP_HARNESS, shapes.SS_TCP_HARNESS)
    assert {(row["protocol"], row["port"]) for row in rows} == {("udp", 30160), ("tcp", 4721)}
    # "adapter" is not the layer's executable name; membership is by exact name.
    assert all(row["element_in_layer"] is False for row in rows)


def test_membership_is_unknown_without_the_users_field():
    rows = hostscan.listeners("UNCONN 0      0      0.0.0.0:30162 0.0.0.0:*\n", "")
    assert rows[0]["element_in_layer"] is None and rows[0]["element"] == ""


def test_membership_does_not_match_a_substring():
    line = 'UNCONN 0 0 0.0.0.0:30163 0.0.0.0:* users:(("my_adapter_tool",pid=5,fd=3))\n'
    assert hostscan.listeners(line, "")[0]["element_in_layer"] is False


def test_established_client_check_needs_both_steps():
    check = hostscan.client_check(shapes.SS_SPORT_HOST.replace("python3", "frame_assembler"),
                                  shapes.SS_DPORT_HOST.replace("python3", "de4sdv_score_ad"), "before")
    assert check["holds"] is True and check["peers"] == ["127.0.0.1:33766"]
    assert check["adapter_peer"] == "127.0.0.1:33766"


def test_r17_a_lone_loopback_client_that_is_not_the_adapter_does_not_hold():
    sport = '0 0 127.0.0.1:4721 127.0.0.1:50002 users:(("python3",pid=2,fd=4))\n'
    dport = '0 0 127.0.0.1:50002 127.0.0.1:4721 users:(("ros2bag",pid=2,fd=4))\n'
    check = hostscan.client_check(sport, dport, "after")
    assert check["holds"] is False
    assert "not the adapter" in check["detail"]


def test_r17_two_clients_do_not_hold_and_both_records_are_kept(tmp_path):
    before_sport = ('0 0 127.0.0.1:4721 127.0.0.1:50000 users:(("python3",pid=1,fd=3))\n'
                    '0 0 127.0.0.1:4721 127.0.0.1:50002 users:(("python3",pid=1,fd=4))\n')
    before_dport = ('0 0 127.0.0.1:50000 127.0.0.1:4721 users:(("de4sdv_score_ad",pid=9,fd=3))\n'
                    '0 0 127.0.0.1:50002 127.0.0.1:4721 users:(("ros2bag",pid=2,fd=4))\n')
    after_sport = '0 0 127.0.0.1:4721 127.0.0.1:50000 users:(("python3",pid=1,fd=3))\n'
    after_dport = '0 0 127.0.0.1:50000 127.0.0.1:4721 users:(("de4sdv_score_ad",pid=9,fd=3))\n'
    record = tmp_path / "frame_assembler_clients.json"
    hostscan.record_client_check(record, hostscan.client_check(before_sport, before_dport, "before"))
    hostscan.record_client_check(record, hostscan.client_check(after_sport, after_dport, "after"))
    data = json.loads(record.read_text())
    assert [check["phase"] for check in data["checks"]] == ["before", "after"]
    assert data["checks"][0]["holds"] is False and data["checks"][1]["holds"] is True
    assert data["adapter_only"] is False  # both checks must hold


def test_a_remote_peer_does_not_hold():
    sport = '0 0 192.168.98.1:4721 192.168.98.118:40000 users:(("python3",pid=1,fd=3))\n'
    check = hostscan.client_check(sport, "", "before")
    assert check["holds"] is False and "loopback" in check["detail"]


# ------------------------------------------------------------------ nft

def test_nft_counters_sum_every_dds_rule_and_read_tcp():
    counters = hostscan.nft_counters(shapes.NFT_TABLE_TWO_ADDS)
    assert counters == {"table": True, "dds_rules": 2, "dds_packets": 16, "tcp_rules": 2, "tcp_packets": 4}


def test_nft_counters_absent_table_or_no_counter_is_unreadable():
    assert hostscan.nft_counters("Error: No such file or directory\nlist table inet de4sdv_bench\n")["table"] is False
    unreadable = hostscan.nft_counters(shapes.NFT_TABLE_WITHOUT_COUNTERS)
    assert unreadable["table"] is True and unreadable["dds_packets"] is None


def test_nft_counters_of_the_feasibility_listing():
    counters = hostscan.nft_counters(shapes.NFT_TABLE_SPIKE)
    assert counters["dds_packets"] == 8 and counters["dds_rules"] == 2


# ------------------------------------------------------------------ ip

def test_guest_inventory_reads_each_namespace_and_interfaces_without_ipv4():
    inventory = hostscan.parse_guest_inventory(shapes.GUEST_INVENTORY_IVI)
    assert inventory[""]["eth1"] == ["192.168.98.118"]
    assert inventory[""]["buried_eth0"] == ["192.168.97.2"]
    assert inventory[""]["wlan0"] == []  # listed, no IPv4 address
    assert inventory["sdv_dt_ns"]["sdv_dt"] == ["192.168.100.4"]
    assert "lo" in inventory[""]


def test_host_addresses_take_every_cvd_interface():
    assert hostscan.host_addresses(shapes.HOST_IP_ADDR) == ["192.168.96.1", "192.168.97.1", "192.168.98.1"]


def test_route_and_neighbour_readers():
    assert hostscan.route_device("192.168.98.1 dev eth1 table 199 src 192.168.98.118 uid 0 \n    cache \n") == \
        ("eth1", "192.168.98.118")
    assert hostscan.route_device("RTNETLINK answers: Network is unreachable\n") is None
    assert hostscan.neigh_state("192.168.98.1 dev eth1 lladdr 02:00:00:00:00:01 REACHABLE\n") == "REACHABLE"
    assert hostscan.neigh_state("192.168.97.1 dev eth1  FAILED\n") == "FAILED"
    assert hostscan.neigh_state("") is None


# ------------------------------------------------------------------ ASM-MW-031

def test_asm_mw_031_holds_for_one_humble_environment(tmp_path):
    proc = shapes.fake_proc(tmp_path, [shapes.ROS_HUMBLE_ADAPTER, shapes.ROS_HUMBLE_AUTOWARE, shapes.PLAIN_DAEMON],
                            cyclonedds_index=120)
    record = hostscan.asm_mw_031(proc)
    assert record["holds"] is True, record
    assert len(record["processes"]) == 2


def test_r16_a_jazzy_process_breaks_the_assumption(tmp_path):
    proc = shapes.fake_proc(tmp_path, [shapes.ROS_HUMBLE_ADAPTER, shapes.ROS_JAZZY_DEFAULTS], cyclonedds_index=120)
    record = hostscan.asm_mw_031(proc)
    assert record["holds"] is False
    assert any("jazzy" in problem for problem in record["problems"])


def test_r16_another_participant_range_breaks_the_assumption(tmp_path):
    proc = shapes.fake_proc(tmp_path, [shapes.ROS_HUMBLE_ADAPTER], cyclonedds_index=9)
    assert hostscan.asm_mw_031(proc)["holds"] is False


def test_r16_an_unreadable_process_gives_unknown(tmp_path):
    proc = shapes.fake_proc(tmp_path, [shapes.ROS_HUMBLE_ADAPTER, shapes.UNREADABLE], cyclonedds_index=120)
    record = hostscan.asm_mw_031(proc)
    assert record["holds"] is None
    assert record["unreadable"] and record["unreadable"][0]["pid"] == shapes.UNREADABLE["pid"]


def test_r16_a_ros_process_found_only_by_its_libraries_is_checked(tmp_path):
    proc = shapes.fake_proc(tmp_path, [shapes.ROS_HUMBLE_ADAPTER, shapes.ROS_BY_MAPS_ONLY], cyclonedds_index=120)
    record = hostscan.asm_mw_031(proc)
    assert record["holds"] is False  # no domain or RMW in its environment
    assert any(entry["pid"] == shapes.ROS_BY_MAPS_ONLY["pid"] for entry in record["processes"])


# ------------------------------------------------------------------ capture witness

def test_capture_reads_udp_markers_and_a_4721_syn(tmp_path):
    from de4sdv_broker_path_bench import hostscan as hs
    records = [
        (1, b.udp_datagram("192.168.98.118", "192.168.98.1", 40000, 30160, b"MARK:ivi-eth1-192.168.98.1-30160")),
        (2, b.udp_datagram("192.168.98.3", "192.168.98.1", 40000, 30150, b"MARK:core-eth1-192.168.98.1-30150extra")),
        (3, b.tcp_segment("192.168.98.118", "192.168.98.1", 55000, 4721, 1000, 0, b.SYN)),
        (4, b.tcp_segment("192.168.98.118", "192.168.98.1", 55000, 4721, 1001, 5001, b.ACK)),  # not a SYN: ignored
    ]
    path = tmp_path / "cvd-ebr.pcap"
    path.write_bytes(b.pcap(records))
    found = hs.capture_markers([path])
    assert "MARK:ivi-eth1-192.168.98.1-30160" in found["udp_markers"]
    assert "MARK:core-eth1-192.168.98.1-30150extra" in found["udp_markers"]
    assert found["tcp_syns"] == [{"host": "192.168.98.1", "port": 4721}]


def test_capture_sees_a_dropped_datagram_too(tmp_path):
    # The capture is pre-netfilter, so a datagram the rule drops is still here;
    # the counter, not the capture, decides reached vs dropped.
    from de4sdv_broker_path_bench import hostscan as hs
    path = tmp_path / "cvd-ebr.pcap"
    path.write_bytes(b.pcap([(1, b.udp_datagram("192.168.98.118", "192.168.98.1", 40000, 30160,
                                                b"MARK:ivi-eth1-192.168.98.1-30160"))]))
    assert hs.capture_markers([path])["udp_markers"] == ["MARK:ivi-eth1-192.168.98.1-30160"]


def test_capture_missing_and_unreadable_files_are_tolerated(tmp_path):
    from de4sdv_broker_path_bench import hostscan as hs
    bad = tmp_path / "bad.pcap"
    bad.write_bytes(b"\x0a\x0d\x0d\x0a" + b"\x00" * 40)  # pcapng, refused
    found = hs.capture_markers([tmp_path / "missing.pcap", bad])
    assert found["udp_markers"] == [] and found["problems"]
