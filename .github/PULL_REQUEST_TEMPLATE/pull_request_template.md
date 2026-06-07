## Summary

- What problem does this PR solve?
- What changed?

## Contribution classification

- Size: `XS` / `S` / `M` / `L`
- Primary lane: `modeling` / `docs` / `methodology` / `simulation` / `traceability` / `compliance` / `devsecops` / `community`

## Traceability

- Related issue(s): #
- Impacted artifacts (model/docs/specs/tests/evidence):
  - 

## Validation evidence

Paste command outputs (or link artifacts):

```bash
python scripts/check_repo.py
python scripts/smoke_test.py
python scripts/validate_sysml.py  # required for changed .sysml files
```

## Checklist

- [ ] Change is focused and reviewable
- [ ] Updated docs/specs/terminology where assumptions changed
- [ ] Preserved traceability across impacted artifacts
- [ ] If `.sysml` files were created or modified, validated them with
      Sensmetry SysIDE Modeler CLI via `python scripts/validate_sysml.py`
- [ ] No secrets or private data included
- [ ] No unsupported compliance/certification claims
