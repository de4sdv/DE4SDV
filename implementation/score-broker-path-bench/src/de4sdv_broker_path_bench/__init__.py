"""DE4SDV bench of the AAOS SDV broker path of INC-MW-011 (phase 10).

The package is the pure evaluation side of the bench:

- ``pcap``: a classic-pcap reader and TCP reassembler;
- ``frames``: the VisualizationFrame wire decoder and the length-delimited
  stream splitter;
- ``relay_log``: the IVI frame relay's logcat events and its phases;
- ``clock``: the host-and-guest offset of ASM-MW-030 from an NTP capture;
- ``probe``: the read side of the REQ-MW-016 reachability check;
- ``evaluators`` and ``outcome``: the verdict of each case (VC-MW-015,
  VC-MW-016, VC-MW-017, VC-MW-020) and the outcome vocabulary;
- ``run``: the command-line replay.

It reads only the raw artifacts of a run directory and returns an outcome of
the middleware evidence vocabulary. It never opens a socket and never runs on
the VM. The VM scripts live under ``scripts/``. Nothing here is evidence of
record. It runs on Python 3.10 (the bench VM) and 3.11 (CI), standard library
only.
"""
