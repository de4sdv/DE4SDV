# Governed product-line scope

This directory contains authoritative SysML v2 decisions about which planned
reference members define a product line. The PLEML feature models are
authored against them.

The current governed scope is
[`de4sdv_aebs_product_line_scope.sysml`](de4sdv_aebs_product_line_scope.sysml).
It records:

- the three planned AEBS reference members: the two of the initial scope and
  the S-CORE-integrated member of
  [ADR 0023](../../docs/architecture-decisions/0023-admit-score-integrated-aebs-reference-member.md);
- Vehicle Platform Integration Mode and its three admitted alternatives;
- common/current-scope engineering content, with an HMI display in every
  member since
  [ADR 0026](../../docs/architecture-decisions/0026-hmi-display-in-every-member-product.md);
- derived architecture and technical realization;
- reference-only, deferred, and excluded concerns;
- Development as the only currently justified product-decision binding stage;
- authority and change-control provenance: the initial scope decision and
  the scope decisions of ADR 0023 and ADR 0026, each governing the scope.

Portfolio membership is not an implementation maturity claim. Local increment,
configuration, implementation, and evidence statuses retain their own meanings.

This scope model is not a PLEML feature tree or configuration. It is the
admission authority (ADR 0014): the features of the PLEML feature models
correspond to its elements, and the evaluation receipts decide each
configuration's admission against it, apart from its validity
([ADR 0022](../../docs/architecture-decisions/0022-adopt-pleml-as-product-line-authority.md)).
Future portfolio changes require a reviewed scope decision and a corresponding
update to this model.
