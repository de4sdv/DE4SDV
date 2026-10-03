#!/usr/bin/env python3
"""Explicit non-production, supplied-API relationship CLI or stdio MCP server.

No environment-based selection, write commands, activation or production fallback.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.composition_construction import build_relationship_successor_runtime
from de4sdv.semantic.relationship_successor_contract import generate_contract
from de4sdv.semantic.authority_selection import AuthoritySelectionError
from de4sdv.sysml_api.errors import SysMLApiError


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--non-production', action='store_true', required=True)
    parser.add_argument('--predecessor', choices=['legacy', 'o3+definitions'], required=True)
    parser.add_argument('--api-url', required=True)
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--expected-git-revision', required=True)
    parser.add_argument('--ontology', type=Path, default=ROOT / 'approach/framework/ontology/de4sdv-basic-ontology.yaml')
    parser.add_argument('--api-timeout', type=float, default=600.0)
    parser.add_argument('--o3-authority-bundle', type=Path)
    parser.add_argument('--o3-authority-bundle-id')
    parser.add_argument('--activate', action='store_true', help='always refused')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('model-status')
    sub.add_parser('mcp')
    for name in ['resolve', 'inspect', 'neighbors', 'impact', 'verification-coverage']:
        p = sub.add_parser(name)
        p.add_argument('identifier')
        if name == 'neighbors':
            p.add_argument('--predicate', action='append')
    p = sub.add_parser('trace')
    p.add_argument('source')
    p.add_argument('target')
    p.add_argument('--max-depth', type=int, default=4)
    args = parser.parse_args(argv)
    if args.activate:
        parser.error('relationship successor is non-production; activation refused')
    runtime = dict(api_url=args.api_url, binding_path=args.binding,
                   expected_git_revision=args.expected_git_revision,
                   ontology_path=args.ontology, api_timeout=args.api_timeout)
    if args.predecessor == 'o3+definitions':
        if not args.o3_authority_bundle or not args.o3_authority_bundle_id:
            parser.error('o3+definitions requires an exact O3 bundle and bundle id')
        document = json.loads(args.o3_authority_bundle.read_text())
        if document.get('bundle_id') != args.o3_authority_bundle_id:
            parser.error('O3 bundle id mismatch')
        runtime['semantic_authority'] = document
    elif args.o3_authority_bundle or args.o3_authority_bundle_id:
        parser.error('O3 bundle supplied with explicit legacy predecessor')
    try:
        service, _ = build_relationship_successor_runtime(
            contract=generate_contract(ROOT), predecessor=args.predecessor,
            root=ROOT, **runtime)
        if args.command == 'mcp':
            from de4sdv.semantic.mcp_server import create_mcp_server
            create_mcp_server(service).run(transport='stdio')
            return 0
        if args.command == 'model-status':
            result = service.model_status()
        elif args.command == 'resolve':
            result = service.resolve_element(args.identifier)
        elif args.command == 'inspect':
            result = service.inspect_element(args.identifier)
        elif args.command == 'neighbors':
            result = service.semantic_neighbors(args.identifier, predicates=args.predicate)
        elif args.command == 'impact':
            result = service.impact(args.identifier)
        elif args.command == 'verification-coverage':
            result = service.verification_coverage(args.identifier)
        else:
            result = service.trace(args.source, args.target, max_depth=args.max_depth)
    except (ValueError, AuthoritySelectionError, SysMLApiError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
