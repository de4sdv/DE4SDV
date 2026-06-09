## Summary

- What problem does this PR solve?
- What changed?

## Contribution classification

- Size: `XS` / `S` / `M` / `L`
- Primary lane:
  `modeling` / `docs` / `methodology` / `simulation` / `traceability` /
  `compliance` / `devsecops` / `community`

## Traceability

- Related issue(s): #
- Impacted artifacts (model/docs/specs/tests/evidence):
  - TBD

## Validation evidence

Paste command outputs (or link artifacts):

```bash
python scripts/check_repo.py
python scripts/smoke_test.py
```

For `.sysml` changes, add one of the following:

- Local validation evidence from the Syside Editor VS Code extension, if
  available
- Local CLI evidence from `python scripts/validate_sysml.py`, if available
- A request for maintainer-run privileged Syside CI validation

## SysML validation

If this PR creates or modifies `.sysml` files:

- [ ] Optional: I validated changed SysML files locally with the Syside Editor
      VS Code extension.
- [ ] Optional: I validated changed SysML files locally with
      `python scripts/validate_sysml.py`.
- [ ] I request maintainer-run licensed Syside CI validation.
- [ ] Not applicable; this PR does not change `.sysml` files.

## Checklist

- [ ] Change is focused and reviewable
- [ ] Updated docs/specs/terminology where assumptions changed
- [ ] Preserved traceability across impacted artifacts
- [ ] If `.sysml` files changed, validation status is documented above
- [ ] No secrets or private data included
- [ ] No unsupported compliance/certification claims
