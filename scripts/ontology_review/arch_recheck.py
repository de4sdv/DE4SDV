"""Architecture-slice independent recheck -> architecture-decisions-v2.json (canonical schema; provenance tool).

Recheck of the 24 architecture identities: reads the v1 candidate set
(architecture-decisions.json), preserves its semantic decisions, and rebuilds
each row into the canonical machine-readable schema with re-verified repository
evidence at the pinned revision (bc2b65abb623e50032f177d566e34e1a41c09f34).

This tool operated on the review working archive (pre-repair sources are
audit-only and are NOT committed to the governed tree). It is retained to
document the exact recheck/canonicalization transform; the canonical output it
produced lives under docs/method-conformance/o4/ontology-review/decisions/.

Usage:
    python scripts/ontology_review/arch_recheck.py <review-working-archive-dir>
"""
from pathlib import Path
import json, sys

if len(sys.argv) != 2:
    raise SystemExit("usage: arch_recheck.py <review-working-archive-dir>")
WORK = Path(sys.argv[1])
V1 = json.loads((WORK / 'architecture-decisions.json').read_text())
INPUT = json.loads((WORK / 'architecture-input.json').read_text())
ASSIGNED = [r['identity'] for r in INPUT]
assert len(ASSIGNED) == 24
assert {r['identity'] for r in V1} == set(ASSIGNED), 'v1 arch set mismatch'

REPO = 'repo/'
# ---- re-verified evidence overrides (repo-relative anchors at bc2b65a) ----
R = {
 'Stakeholder': dict(
   refs=[('SysML 2.0', '§7.21.3 Concern Definitions and Usages (stakeholder mechanism)'),
         ('SysML 2.0', '§8.3.21.12 StakeholderMembership (PartUsage owned via StakeholderMembership must specialize the stakeholder parameter typing)')],
   extra_evidence=[('model', 'textual-notation-of-model/packages/methods/de4sdv/de4sdv_stakeholders.sysml:13-17',
                    'part def Stakeholder base (risk/effort/contact/categories attributes); header comment states stakeholder parameters are part usages typed by part definitions'),
                   ('model', 'textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml:52',
                    'native stakeholder parameter usages inside governed concern definitions')],
   delta_add=' The native stakeholder mechanism (StakeholderMembership; §8.3.21.12) is a usage-site witness; the class itself is the DE4SDV role/typing catalogue.'),
 'Concern': dict(
   refs=[('SysML 2.0', '§7.21.3 Concern Definitions and Usages'),
         ('SysML 2.0', '§8.3.21.3 ConcernDefinition; §8.3.21.4 ConcernUsage; §8.3.21.5 FramedConcernMembership'),
         ('SysML 2.0', '§8.4.17.4 Concern Definitions; §8.4.17.5 Concern Usages')],
   extra_evidence=[('model', 'textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_concerns_and_viewpoints.sysml:26-50',
                    'native concern defs (ProductLineCapabilityClassificationConcern, RegulatoryScopeWithoutComplianceClaimConcern, IncrementBoundaryConcern)'),
                   ('model', 'textual-notation-of-model/packages/methods/saf/SAF_Viewpoints.sysml',
                    'SAF viewpoint catalogue; DE4SDV viewpoints frame these concerns')]),
 'Viewpoint': dict(
   refs=[('SysML 2.0', '§7.26.3 Viewpoint Definitions and Usages'),
         ('SysML 2.0', '§8.3.26.8 ViewpointDefinition; §8.3.26.9 ViewpointUsage'),
         ('SysML 2.0', '§8.4.22.3 Viewpoint Definitions; §8.4.22.4 Viewpoint Usages')],
   extra_evidence=[('model', 'textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_concerns_and_viewpoints.sysml:85-129',
                    'native viewpoint defs (IncrementFramingViewpoint, ProductLineClassificationViewpoint, RegulatoryScopeViewpoint, ProductLineConfigurationViewpoint, ProductModelAssemblyViewpoint)')]),
 'View': dict(
   refs=[('SysML 2.0', '§8.3.26.7 ViewDefinition; §8.3.26.11 ViewUsage'),
         ('SysML 2.0', '§8.4.22 Views and Viewpoints Semantics'),
         ('SysML 2.0', '§9.2.16 Views (Systems Library base)')],
   extra_evidence=[('model', 'textual-notation-of-model/packages/features/aebs/aebs_bicycle_verification.sysml:92',
                    'assurance view usages (aebsBicycleVerificationAssuranceView)'),
                   ('model', 'textual-notation-of-model/packages/features/aebs/aebs_evidence.sysml:312',
                    'aebsNominalEvidenceAssuranceView')]),
 'VerificationMethod': dict(
   source_add=' Model-resident usage verified: @VerificationMethod{ kind = ... } native metadata annotations in AEBS/middleware verification slices; the ADR 0009 amendment adds the ODE4HERA verificationMethod (NRM A8, upstream String[0..1]) as an adopted carrier populated with the native VerificationMethodKind vocabulary.',
   refs=[('SysML 2.0', '§7.26.3 Viewpoint/verification metadata overview; §9.2.17.2.6 VerificationMethod; §9.2.17.2.7 VerificationMethodKind'),
         ('DE4SDV-governance', 'ADR 0009 amendment: verificationMethod (NRM A8) typed upstream String[0..1]; DE4SDV populates it with the standard VerificationMethodKind vocabulary')],
   extra_evidence=[('model', 'textual-notation-of-model/packages/features/aebs/aebs_degraded_input_verification.sysml:84-117',
                    '@VerificationMethod{ kind = test | analyze | (test, analyze) } annotations on verification case items'),
                   ('model', 'textual-notation-of-model/packages/features/aebs/aebs_regulatory_criterion_verification.sysml:100-130',
                    '@VerificationMethod{ kind = inspect | analyze } annotations'),
                   ('ADR', 'docs/architecture-decisions/0009-adopt-ode4hera-requirements-attributes.md:8-14',
                    'NRM A8 verificationMethod adoption statement with native method-kind vocabulary')]),
 'EvidenceStatus': dict(
   delta_add=' Re-verified split: the accepted-library claim covers the requirement-verification-status dimension (VVStatus, NRM A13+A14, adopted); evidence-artifact outcome vocabularies (MiddlewareEvidenceOutcome/Disposition, ExecutionEnvironmentEvidenceStatus) are governed slice-local enums and are not part of the accepted-library claim; no acceptance semantics follow.',
   extra_evidence=[('model', 'textual-notation-of-model/packages/methods/de4sdv/de4sdv_sysmod_adapter.sysml:24',
                    'public import RequirementsManagement::VVStatus (adapter seam)'),
                   ('model', 'textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml:111',
                    'attribute :>> verificationStatus = VVStatus::NotStarted (adopted library values in governed usages)')]),
 'AssuranceClaim': dict(
   source_add=' Re-verified mechanism: claim/argument layer modeled with requirement defs (VisualizationClaim, VisualizationCounterClaim), argument usages, and explicit argument/evidence dependency traces, framed by ArgumentationAssuranceConcern/ArgumentationAssuranceViewpoint across AEBS slices; middleware evidence records carry claimBoundary attributes. No assert constraint usages exist in the model (verified: zero `assert` declarations).',
   extra_evidence=[('model', 'textual-notation-of-model/packages/features/aebs/aebs_visualization_verification_evidence.sysml:618-742',
                    'claims/counterclaims as requirement defs, argument usages, dependency traces argument->claim and evidence->claim'),
                   ('model', 'textual-notation-of-model/packages/features/aebs/aebs_degraded_input_verification.sysml:139-145',
                    'ArgumentationAssuranceConcern framed by ArgumentationAssuranceViewpoint'),
                   ('model', 'textual-notation-of-model/packages/features/middleware/middleware_verification_evidence.sysml:254-304',
                    'bounded claimBoundary attributes on retained evidence records')]),
 'Scenario': dict(
   extra_evidence=[('model', 'textual-notation-of-model/packages/features/aebs/aebs_degraded_input_verification.sysml:11-72',
                    'enum def DegradedInputScenarioIdentity + scenario-typed attributes on evidence-contract items'),
                   ('test', 'scripts/check_model_sync.py:59-142',
                    'sync point 1: SysML scenario-identity enums <-> Python evaluator scenario identities, parity-enforced')]),
 'ValidationScenario': dict(
   extra_evidence=[('model', 'textual-notation-of-model/packages/features/middleware/middleware_verification_evidence.sysml:422,453,485',
                    'in-model statement: "(SysML v2 provides no native validation-case keyword)" with bounded validation usage notes')]),
 'AcceptanceCriterion': dict(
   delta_add=' Re-verified representation: exactly two per-slice criterion definitions (MiddlewareAcceptanceCriterion, VisualizationAcceptanceCriterion); c5 measured 14 declared acceptance-criterion-role usages. Requirement-def representation expresses the criterion condition but does not by itself establish the result/artifact acceptance role, which stays DE4SDV application semantics with an open identity contract.',
   extra_evidence=[('model', 'textual-notation-of-model/packages/features/middleware/middleware_verification_evidence.sysml:146',
                    'requirement def MiddlewareAcceptanceCriterion (kernel-mapped slice definition)'),
                   ('model', 'textual-notation-of-model/packages/features/aebs/aebs_visualization_verification_evidence.sysml:158',
                    'requirement def VisualizationAcceptanceCriterion'),
                   ('review', 'repo/docs/method-conformance/o1/c5-relevance-realization-review.md',
                    'c5: 7 middleware + 7 visualization acceptance-criterion-role usages; role distinct from EvidenceContract')]),
 'EvidenceContract': dict(
   delta_add=' Re-verified count: eight lineage-less per-slice evidence-contract requirement defs (DegradedInput, Bicycle, Nominal, RegulatoryCriterion, NonActivation, Pedestrian, PartialIntervention, Override) plus one distinct traceability bridge candidate (EvidenceContractTraceabilityRequirementCandidate :> RequirementCandidate, method_context.sysml:152) that heads claims/arguments/counterclaims and is NOT the contract role.',
   extra_evidence=[('model', 'textual-notation-of-model/packages/features/aebs/aebs_degraded_input_verification.sysml:41',
                    'requirement def DegradedInputEvidenceContract (bare, no specialization)'),
                   ('model', 'textual-notation-of-model/packages/features/aebs/aebs_bicycle_verification.sysml:31',
                    'requirement def BicycleEvidenceContract (bare)'),
                   ('model', 'textual-notation-of-model/packages/features/aebs/aebs_evidence.sysml:192',
                    'requirement def NominalEvidenceContractRequirement (bare)'),
                   ('model', 'textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml:152',
                    'EvidenceContractTraceabilityRequirementCandidate :> RequirementCandidate (distinct traceability role)')]),
 'ArchitectureElement': dict(
   extra_evidence=[('repository', 'approach/framework/ontology/de4sdv-basic-ontology.yaml',
                    'YAML-only declaration; verified no model-resident declaration at bc2b65a'),
                   ('model', 'textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml:122',
                    'only model occurrence of the name is a TraceLink string literal (toElement = "ArchitectureElement")'),
                   ('review', 'repo/de4sdv/semantic/traversal.py:200-300',
                    'hasRelevantArchitecture runtime engine: declared range carried in the ontology mapping; executable constituent filter admits part/action usages+definitions (c5)')]),
 'Function': dict(
   extra_evidence=[('repository', 'approach/framework/ontology/de4sdv-basic-ontology.yaml',
                    'YAML-only declaration; verified no model-resident declaration at bc2b65a'),
                   ('review', 'repo/docs/method-conformance/o1/c5-relevance-realization-review.md',
                    'specifiesFunction executable target filter is action-typed constituents; declared umbrella is broader (action/state/behavior)')]),
 'LogicalElement': dict(
   extra_evidence=[('repository', 'approach/framework/ontology/de4sdv-basic-ontology.yaml',
                    'YAML-only declaration; verified no model-resident declaration at bc2b65a; allocatedTo range (vocabulary-only)')]),
 'PhysicalElement': dict(
   extra_evidence=[('repository', 'approach/framework/ontology/de4sdv-basic-ontology.yaml',
                    'YAML-only declaration; verified no model-resident declaration at bc2b65a; deployedTo range (blocked redesign)')]),
 'Interface': dict(
   extra_evidence=[('repository', 'approach/framework/ontology/de4sdv-basic-ontology.yaml',
                    'YAML-only declaration; verified no model-resident declaration at bc2b65a; no predicate in the executable set names it as domain/range')]),
 'RegulatoryConstraint': dict(
   extra_evidence=[('model', 'textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml:154-157',
                    'requirement def RegulatoryConstraintCandidate doc: "Grounds the ontology RegulatoryConstraint class and R003 derivation targets"'),
                   ('test', 'scripts/check_model_sync.py:805,1118,934',
                    'R003 origin set enforcement (Need | RegulatoryConstraint | ArchitectureDecisionRecord) and ProblemStatement exclusion')]),
 'ProblemStatement': dict(
   extra_evidence=[('test', 'scripts/check_model_sync.py:934',
                    'R003 exclusion grounding: ProblemStatement is traced INTO, not out of (excluded from origin set)')]),
 'Requirement': dict(
   extra_evidence=[('model', 'textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml:125-150',
                    'RequirementCandidate :> SYSMODRequirementBase, RequirementsManagementAttributeBase + named sub-candidates')]),
 'Need': dict(
   extra_evidence=[('model', 'textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml:98-123',
                    'StakeholderNeedCandidate :> RequirementsManagementAttributeBase + need specializations')]),
 'DerivesFromNeed': dict(
   extra_evidence=[('review', 'repo/de4sdv/semantic/model_authority.py:1-14',
                    'projection/predicate semantics read from the validated model (ends, direction, strength, boundary); the module locates, never defines'),
                   ('review', 'repo/docs/method-conformance/k-slice/v11-final-decision.md',
                    'K slice final decision: minimal application connection; standard Derivation library rejected (originalImpliesDerived overclaims)')]),
 'EvidenceArtifact': dict(
   extra_evidence=[('model', 'textual-notation-of-model/packages/features/middleware/middleware_verification_evidence.sysml:86,231-291',
                    'item def RetainedMiddlewareEvidence + four retained runtime evidence records (reference-shaped, not byte-carrying)')]),
 'Assumption': dict(
   extra_evidence=[('model', 'textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml:164',
                    'part def IncrementAssumption'),
                   ('model', 'textual-notation-of-model/packages/features/aebs/aebs_visualization_framing.sysml:142,148',
                    'governed assumption usages (asmSystem1Unchanged, asmRealSourcesRequired)')]),
 'Gap': dict(
   extra_evidence=[('model', 'textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml:168',
                    'part def IncrementGap')]),
 'Stakeholder_extra': dict(),
}

def canon_consumers(v):
    """v1 arch consumers were free-text strings; rebuild into structured objects."""
    if isinstance(v, list):
        items = v
    else:
        items = str(v).split(';')
    out = []
    for it in items:
        s = str(it).strip().rstrip('.')
        if not s:
            continue
        if ' ' in s:
            head, _, tail = s.partition(' ')
            if ('/' in head or head.endswith(('.sysml', '.py', '.md', '.json', '.yaml'))):
                out.append({'path': head, 'symbol_or_surface': tail or None, 'role': None})
                continue
        if '/' in s and ' ' not in s:
            out.append({'path': s, 'symbol_or_surface': None, 'role': None})
        else:
            out.append({'path': None, 'symbol_or_surface': s, 'role': None})
    return out

def canon_evidence(v):
    out = []
    items = v if isinstance(v, list) else [v]
    for it in items:
        s = str(it).strip()
        if not s:
            continue
        if ' ' not in s and ('/' in s):
            out.append({'type': classify(s), 'path_or_reference': s, 'finding': None})
        else:
            out.append({'type': 'review', 'path_or_reference': s, 'finding': None})
    return out

def classify(p):
    if p.startswith('docs/architecture-decisions'):
        return 'ADR'
    if 'docs/method-conformance' in p or p.startswith('review'):
        return 'review'
    if p.startswith('tests/') or '/test_' in p or p.startswith('scripts/'):
        return 'test'
    if p.startswith('evidence/'):
        return 'evidence-artifact'
    if '§' in p or p.startswith('SysML') or p.startswith('KerML'):
        return 'normative-spec'
    if p.startswith('textual-notation-of-model') or p.startswith('model-based-product-line-engineering'):
        return 'model'
    if p.startswith('de4sdv/') or p.startswith('tools/'):
        return 'runtime'
    return 'repository'

rows = []
for v1 in V1:
    n = v1['identity']
    ov = R.get(n, {})
    refs = ov.get('refs') or ([(v1['normative_reference'].split(' ')[0], v1['normative_reference'])] if v1.get('normative_reference') else [])
    normative_reference = [{'source': s, 'reference': r} for s, r in refs]
    source = v1['source'] + ov.get('source_add', '')
    delta = v1['delta'] + ov.get('delta_add', '')
    ev = canon_evidence(v1.get('evidence')) + [{'type': t, 'path_or_reference': p, 'finding': f} for t, p, f in ov.get('extra_evidence', [])]
    # fill finding for canon evidence
    for e in ev:
        if not e.get('finding'):
            e['finding'] = f"Reviewed anchor for {n} ({e['type']})."
    rows.append({
        'identity': n,
        'kind': 'class',
        'o3_protected': False,
        'classification': v1['classification'],
        'source': source,
        'normative_reference': normative_reference,
        'delta': delta,
        'disposition': v1['disposition'],
        'target_authority': v1['target_authority'],
        'target_definition': v1['target_definition'],
        'migration': v1['migration'],
        'rationale': v1['rationale'],
        'consumers': canon_consumers(v1.get('consumers')),
        'evidence': ev,
        'dependencies': [str(x) for x in (v1.get('dependencies') or [])],
        'decisions': ([str(v1['decisions'])] if isinstance(v1.get('decisions'), str) else [str(x) for x in (v1.get('decisions') or [])]),
        'blocker': v1.get('blocker'),
        'change_summary': v1.get('change_summary') or f"Recheck at bc2b65a: decision confirmed ({v1['disposition']}); evidence anchors re-verified and strengthened.",
        'implicit_rule': v1.get('implicit_rule'),
        'rename_or_merge_target': v1.get('rename_or_merge_target'),
        'recheck': {'status': 'confirmed-unchanged', 'evidence_updates': [f'{t}:{p}' for t, p, _ in ov.get('extra_evidence', [])]},
    })

assert len(rows) == 24
(WORK / 'architecture-decisions-v2.json').write_text(json.dumps(rows, indent=2) + '\n')
print('wrote architecture-decisions-v2.json:', len(rows), 'rows')
for r in rows:
    assert r['classification'] in {'NATIVE_EXPLICIT','NATIVE_IMPLICIT','NATIVE_GROUNDED_DE4SDV','ACCEPTED_LIBRARY','REPRESENTATION_ONLY','NO_NATIVE_SEMANTIC_FIT'}
    assert r['disposition'] in {'KEEP_NATIVE','KEEP_ACCEPTED_LIBRARY','KEEP_DE4SDV_APPLICATION_SEMANTIC','KEEP_EXTERNAL_REFERENCE','KEEP_VOCABULARY_ONLY','KEEP_CONDITIONAL','REDESIGN','MERGE','DEPRECATE','REMOVE','BLOCKED','O3_AMENDMENT_REQUIRED'}
    assert r['migration'] in {'ALREADY_COMPLETE','CURRENT_O3_13','PROJECTION_ONLY','MODEL_AUTHORITY_PARITY','NEW_APPLICATION_SEMANTICS','NATIVE_OR_LIBRARY_ADOPTION','EXTERNAL_BOUNDARY','PLE_DEPENDENT','REQUIRES_SEMANTIC_MIGRATION','REMOVE_FROM_ONTOLOGY','BLOCKED'}
    assert r['consumers'] and all(len(c['path'] or '') != 1 for c in r['consumers'])
    assert r['evidence']
print('enum + shape assertions passed; no v1-v2 disposition or classification changes (all confirmed).')