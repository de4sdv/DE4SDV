# Time across hosts — measured, not assumed

Every latency number this project publishes is a difference of two timestamps.
On one host that difference is real: all processes share one kernel clock. Across
hosts it is not, because the two clocks drift apart, and the difference carries
that drift. This document measures the drift, tries the two mechanisms available
on the platform, and states what a cross-host claim would need.

Measured 2026-11-15 on two `e2-standard-4` instances in `europe-west4-a`, same
VPC, internal addresses `10.164.0.2` ↔ `10.164.0.3`. Probe:
[`checks/timesync_probe.py`](checks/timesync_probe.py), the four-timestamp
exchange, 200 samples at 10 ms spacing.

## 1. What the platform gives you

Both hosts run chrony against Google's NTP. The offset is not constant, and the
first minutes after boot are the worst.

| condition | offset (B relative to A) | n | p95 | min / max | RTT median |
|---|---|---:|---|---|---|
| fresh boot, chrony still converging | **+0.198 ms** | 200 | +0.258 ms | +0.063 / +0.307 ms | 0.483 ms |
| steady state, chrony converged | **−0.044 ms** | 200 | −0.004 ms | −0.090 / +0.021 ms | 0.499 ms |

Read that as: **a cross-host measurement taken in the first minutes after boot
can be off by a quarter of the quantity this testbed measures** (0.198 ms against
a 0.8 ms routed path). In steady state the error is ~5 %, which is tolerable only
because it is stated.

## 2. What PTP does here

linuxptp 4.0 on both hosts, unicast (the VPC does not carry multicast — with the
default configuration both hosts elected themselves grandmaster and exchanged
nothing):

- grandmaster on A: `unicast_listen 1`, software timestamping;
- slave on B: `unicast_master_table` → `UDPv4 10.164.0.2`, `-s`, chrony stopped
  so PTP could steer;
- `step_threshold 1.0` so the servo slews instead of stepping once a second
  (the default `0` re-steps the clock on every measurement).

It locks: the port reaches `SLAVE`, peer path delay reads **84–126 µs**, and the
servo's own offset readings over 57 samples were **median +16 µs, min −36 µs,
max +135 µs**. The session was not stable — the slave dropped to `LISTENING` on
announce timeouts several times, because the master was a short-lived foreground
process.

So PTP's median beats chrony's (16 µs vs 44 µs) and its tail does not (135 µs vs
91 µs), and neither reaches single-digit microseconds. The reason is structural:
both timestamps are taken in software on a virtual NIC, so the timestamp noise is
the same order as the thing being measured.

## 3. What vxedge's `time_sync` is, and is not

`network.time_sync: { kind: gptp, followers: [...] }` exists in vxedge 0.30 and
runs `ptp4l` from a pinned `linuxptp` image. Its own source is explicit:

> the follower's `ptp4l` reads the host's clock, so it **measures the time-sync
> path and does not steer the clock**

and the grandmaster runs inside the gateway's bridge namespace on the same host.
Both sides are containers on one kernel. So on this testbed `time_sync` is a
*protocol exercise*: it can show that gPTP messages traverse the vehicle network,
and it cannot synchronise anything, because there is only one clock. That is a
correct design for a single-host simulator — and it means `time_sync` cannot
support a cross-host claim.

For the same reason there is no way to split a vehicle across hosts today: the
daemon listens on `unix://` only ("TCP+mTLS arrives with the auth work"), so a
second host cannot be part of the same vehicle.

## 4. What a cross-host claim would need

1. **Measure the offset in the same window as the measurement.** The probe is the
   tool; it takes seconds. A number without it is not attributable.
2. **Wait for chrony to converge.** Minutes, not seconds, after boot. The probe
   is also the gate for that.
3. **State the bound, or correct by it.** A 44 µs offset on a 0.8 ms path is a 5 %
   error; correct it or say it.
4. **Do not deploy PTP on a cloud vNIC expecting microseconds.** It locks, it is
   not better than the platform here, and it costs a service to run. PTP is the
   right tool on a bench with hardware timestamping, where the timestamps come
   from the NIC and not from the kernel's software clock.

For this testbed the honest position is the first one: **one host, one clock,
zero offset by construction** — and every number in [`REPORT.md`](REPORT.md) is
stated that way.
