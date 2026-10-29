"""DE4SDV bench of the AAOS SDV broker path of INC-MW-011 (phase 10).

The package holds two kinds of code:

- the pure evaluation side (``pcap``, ``frames``, ``relay_log``, ``clock``,
  ``probe``, ``evaluators``, ``outcome``): it reads only the raw artifacts of
  a run directory and returns an outcome of the middleware evidence
  vocabulary;
- the pure parts of the bench scripts (``settings``, ``changelog``,
  ``dds_ports``, ``nft``, ``launch``, ``acl``) and the command runner
  (``host``) that the scripts under ``scripts/`` use on the bench VM.

Nothing here is evidence of record. It runs on Python 3.10 (the bench VM) and
3.11 (CI) with the standard library only.
"""
