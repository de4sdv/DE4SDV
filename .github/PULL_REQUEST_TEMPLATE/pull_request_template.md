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
- Impacted artifacts (model/docs/tests/evidence):
  - TBD

## Validation evidence

Paste command outputs (or link artifacts):

```bash
python scripts/check_repo.py
python scripts/smoke_test.py
```

For `.sysml` changes, choose one validation path:

1. Local validation, if Syside is available:
   - Syside Editor VS Code extension evidence, or
   - `python scripts/validate_sysml.py` output
2. Maintainer-run privileged validation:
   - Request the `Privileged Syside Validation` workflow after initial review.
     Include the branch, tag, or commit SHA to validate and the model path if it
     is not `textual-notation-of-model`.

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
- [ ] Updated docs/terminology where assumptions changed
- [ ] Preserved traceability across impacted artifacts
- [ ] If `.sysml` files changed, validation status is documented above
- [ ] No secrets or private data included
- [ ] No unsupported compliance/certification claims
