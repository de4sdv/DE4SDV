"""DE4SDV ontology-review package tooling (governance artifacts, not runtime authority).

Tools here operate on the governed O4 ontology-review package under
``docs/method-conformance/o4/ontology-review``:

- ``validate_review.py``         hardened validator for the canonical review package
- ``consolidate_review.py``      regenerates ``integrated-review.json`` from ``decisions/``
- ``generate_review_matrix.py``  regenerates ``REVIEW-matrix.md`` from the envelope
- ``normalize_sources.py``       repair-stage provenance: v1->v2 canonicalization (working-archive input)
- ``arch_recheck.py``            repair-stage provenance: architecture-slice recheck (working-archive input)

Nothing in this package is imported by ``de4sdv/`` runtime code. The review is
migration governance; it must never become runtime semantic authority.
"""