"""Synthetic API protocol tests; NOT licensed model ingestion/run evidence."""
from __future__ import annotations
import asyncio
from contextlib import contextmanager
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

import pytest
from test_approved_relationship_successor import fixture_service, rebuild, ROOT, REVISION
from model_contract_fixtures import model_service
from de4sdv.semantic.relationship_successor import route_successor_bindings
from de4sdv.sysml_api.errors import IdentityNotFoundError


def extension_binding(binding):
    """Simulate real ontology extension-class names, not profile category names."""
    return replace(binding, kernel_bindings=tuple(
        replace(b, ontology_class=b.declaration.split()[-1])
        for b in binding.kernel_bindings))


def test_ingested_extension_pins_route_without_renaming_global_binding():
    _, elements, original, contract = fixture_service()
    binding = extension_binding(original)
    snapshot = binding.to_dict()
    service = rebuild(elements, binding, contract)
    report = service.semantic_neighbors('use-Requirement', predicates=['allocatedTo'])
    assert report['edges'][0]['api_object_id'] == 'allocation'
    assert binding.to_dict() == snapshot
    route = next(r for r in report['semantic_authority']['binding_routes'] if r['profile_class'] == 'Function')
    assert route['ingestion_class'] == 'AllocatableFunction'
    assert route['element_id'] == 'root-Function'
    assert service.binder.bind_class('Function').sysml.element_id == 'root-Function'


def test_exact_pin_ambiguity_refuses_even_same_uuid():
    _, _, binding, contract = fixture_service()
    duplicate = replace(binding.kernel_bindings[0], ontology_class='OtherRequirement')
    with pytest.raises(IdentityNotFoundError, match='ambiguous exact'):
        route_successor_bindings(contract, replace(binding, kernel_bindings=binding.kernel_bindings + (duplicate,)))


@contextmanager
def supplied_synthetic_api(elements):
    reads = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            reads.append(('GET', self.path))
            if '/elements?' not in self.path:
                self.send_error(404)
                return
            data = json.dumps(elements).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        def log_message(self, format, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}', reads
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def http_service(binding, url):
    """The production service assembly reading a supplied API over HTTP.

    The non-production successor CLI (scripts/relationship_successor.py) was
    deleted in O4 Wave C2; the model-authority runtime with the production
    SysMLRepository/ApiClient is the surviving read path.
    """
    from de4sdv.sysml_api.client import ApiClient
    from de4sdv.sysml_api.repository import SysMLRepository
    return model_service(binding, SysMLRepository(ApiClient(url, timeout=30)),
                         expected_git_revision=REVISION)


def test_supplied_http_api_is_read_with_extension_pins():
    _, elements, binding, _ = fixture_service()
    binding = extension_binding(binding)
    with supplied_synthetic_api(elements) as (url, reads):
        report = http_service(binding, url).semantic_neighbors(
            'use-Requirement', predicates=['allocatedTo'])
        assert report['semantic_status'] == 'complete'
        assert report['edges'][0]['api_object_id'] == 'allocation'
        assert report['semantic_authority']['kind'] == 'model'
        assert reads and all(method == 'GET' for method, _ in reads)
        assert all(f'/projects/{binding.sysml_project_id}/commits/{binding.sysml_commit_id}/elements?' in p for _, p in reads)


def test_mcp_surface_uses_same_read_only_service():
    from de4sdv.semantic.mcp_server import create_mcp_server
    _, elements, binding, _ = fixture_service()
    with supplied_synthetic_api(elements) as (url, reads):
        server = create_mcp_server(http_service(extension_binding(binding), url))
        tool = next(t for t in server._tool_manager.list_tools() if t.name == 'semantic_neighbors')
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        report = asyncio.run(server._tool_manager.call_tool(
            'semantic_neighbors', {'identifier': 'use-Requirement', 'predicates': ['allocatedTo']}))
        assert report['edges'][0]['api_object_id'] == 'allocation'
        assert reads and all(method == 'GET' for method, _ in reads)


def test_authored_slice_wires_existing_occurrence_not_duplicate_model():
    base = ROOT / 'textual-notation-of-model/packages/features/aebs'
    functional = (base / 'aebs_functional_architecture.sysml').read_text()
    logical = (base / 'aebs_logical_architecture.sysml').read_text()
    needs = (base / 'aebs_needs_requirements.sysml').read_text()
    assert 'action def AcquireVehicleAndTargetState :> AllocatableFunction' in functional
    assert 'part def StateAcquisitionAndNormalization :> LogicalAllocationElement' in logical
    assert 'allocate functionalFlow.acquireState' in logical
    assert 'to DE4SDV_AEBSLogicalArchitecture::functionalFlow.acquireState;' in needs
    assert 'connection commonCapabilityValidationPlanning : ValidationPlanningAssociation' in needs
    assert 'connection pedestrianResponseSourceProvenance : RegulatorySourceAssociation' in needs
    assert 'E/ECE/TRANS/505/Rev.3/Add.151/Rev.2' in needs
    assert 'dependency reqDetectForwardCollisionRiskTracedToAcquireStateCandidate' in needs
    assert 'action def AllocatableFunction' not in functional


def test_native_reference_shadow_and_specialized_function_lineage():
    service, elements, _, _ = fixture_service()
    function = next(e for e in elements if e['@id'] == 'use-Function')
    function['type'] = [{'@id':'derived-function'}]
    elements.extend([
        {'@id':'derived-function', '@type':'ActionDefinition'},
        {'@id':'specialization', '@type':'Subclassification',
         'subclassifier':{'@id':'derived-function'}, 'superclassifier':{'@id':'root-Function'}},
        {'@id':'target-shadow', '@type':'ReferenceUsage'},
        {'@id':'reference', '@type':'ReferenceSubsetting',
         'owningRelatedElement':{'@id':'target-shadow'}, 'referencedFeature':{'@id':'use-Function'}},
    ])
    allocation = next(e for e in elements if e['@id'] == 'allocation')
    allocation['target'] = [{'@id':'target-shadow'}]
    report = service.semantic_neighbors('use-Requirement', predicates=['allocatedTo'])
    assert report['semantic_status'] == 'complete'
    witness = report['edges'][0]['witness']
    assert witness['native_target'] == 'use-Function'
    assert witness['reference_witnesses'][0]['api_object_id'] == 'reference'
    assert witness['target_root'] == 'root-Function'
