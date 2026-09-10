# R0-8: Required API/export/import closure before implementation

## C1 — Derivation witness closure (K slice; blocks K implementation)

Native derivation relationships (and any Requirement Derivation Library import,
if adopted later) must survive: official validation → export → API import →
read-back with relationship + endpoint UUIDs intact. The importer may report
and remove out-of-export references (plan §9), so closure must be checked
explicitly, not assumed from import success.

Required checks (privileged exact-toolchain run):
1. Serialize a derivation witness; confirm the relationship metaclass and both
   endpoint references in the exported bundle.
2. Import into the API; confirm the relationship object exists with matching
   UUIDs and no out-of-export pruning of endpoints.
3. Read back through the repository; confirm the witness is queryable with
   direction intact.
4. If closure fails: K reports an unsupported boundary — no runtime `.sysml`
   parsing repair, no name-based reconstruction.

## C2 — Verification membership closure (pilot; blocks B)

`verifiedBy` (strategy verification-membership) is implemented, but the pilot
needs the full witness set: RequirementVerificationMembership objects, objective
memberships, subject memberships, and VerificationMethod metadata for
`ConsciousOverrideVerification` and its three evidence-contract requirements.
Check that none of these are pruned at import for the actual AEBS packages.

## C3 — Dependency vs. derivation discrimination (adversarial; blocks K/T)

The model contains many native Dependencies with Requirement/Action-like
endpoints. Closure proof must show the API representation distinguishes a
derivation witness from a generic Dependency with identical endpoint types —
by metaclass/typed marker, never by name or comment. If the serializer shape
cannot distinguish them, the derivation predicate needs an explicit modeled
discriminator (typed marker/definition) before any support claim (UG-05).

## C4 — Out-of-export pruning surface (general; blocks honest completeness)

Enumerate which of the pilot's required references are in-export. Any pruned
reference => affected queries return incomplete/unsupported with diagnostics,
never empty results (plan §9; UG-06).

## C5 — Snapshot acceleration boundary (D; not blocking B)

If validated snapshots accelerate ingestion, snapshot identity must bind the
same validation evidence; equality of canonical conformance payload through API
and snapshot paths is a D-exit case, not a B prerequisite.

## Owner and environment

C1–C4 are privileged exact-toolchain evidence (aarch64 host cannot run the
licensed Syside binary locally — recorded in the Gate A README). They run under
the established privileged runner at an exact head. C5 belongs to D.
