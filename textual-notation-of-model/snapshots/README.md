# Textual model snapshots

This directory is reserved for generated or exported `.sysml` snapshots used to
move model slices between GitHub, SysON, and the SysML v2 API repository pilot.

Snapshots are not authoritative by themselves. They become part of the reviewed
baseline only when committed through a pull request with validation evidence.

The initial SysON workflow expects a future snapshot such as:

```text
textual-notation-of-model/snapshots/de4sdv.sysml
```

Until a normalized exporter exists, use the smallest validated `.sysml` slice
available for import/export spikes.
