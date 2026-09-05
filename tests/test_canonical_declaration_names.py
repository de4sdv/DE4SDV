"""Naming-only lint regressions; not a SysML semantic parser."""
from scripts import check_naming


def test_compact_dependency_names_are_rejected():
    check = getattr(check_naming, 'check_declaration_names_in_text', None)
    assert callable(check), 'Naming gate does not inspect dependency declarations'
    for name in ('s2002DerivedFromNeed', 'reqS2001DerivedFromNeed002',
                 'req001DerivedFromNeed001', 'need001FromContext',
                 'S2002DerivedFromNeed', 'visualizationS2'):
        assert check(f'dependency {name} from source to target;', 'synthetic.sysml'), name


def test_project_declarations_have_semantic_names():
    check = getattr(check_naming, 'check_sysml_declaration_names', None)
    assert callable(check), 'Declaration naming is not a repository-wide gate'
    assert check() == []


def test_legitimate_names_and_prose_are_preserved():
    check = check_naming.check_declaration_names_in_text
    for name in ('ROS2TopicEndpoint', 'ros2Velocity', 'System2Instrumentation',
                 'system1Subject', 'lidarProducesPointCloud2Message',
                 'boundedClaimToBaselineDecision010', 'sourceDerivedFromTarget'):
        assert check(f'dependency {name} from source to target;', 'synthetic.sysml') == []
    assert check('''doc /* dependency s2002Fake from a to b; */
        // dependency req001Fake from a to b;
        attribute label = "dependency s2002Fake from a to b; EVID-AEBS-S2-001";
        dependency sourceDerivedFromTarget from source to target;
    ''', 'synthetic.sysml') == []
    assert check("dependency 's2002Bad' from source to target;", 'synthetic.sysml')


def test_active_model_discovery_includes_scoping():
    paths = {p.relative_to(check_naming.ROOT).as_posix()
             for p in check_naming.iter_declaration_model_files()}
    assert 'model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml' in paths
    assert any(p.startswith('model-based-product-line-engineering/product-models/') for p in paths)
    assert any(p.startswith('textual-notation-of-model/packages/features/middleware/') for p in paths)
    assert not any('/libraries/' in p or '/snapshots/' in p or '/fixtures/' in p for p in paths)


def test_declaration_naming_is_wired_into_repository_gate(monkeypatch):
    monkeypatch.setattr(check_naming, 'check_sysml_declaration_names',
                        lambda: ['synthetic declaration violation'])
    assert 'synthetic declaration violation' in check_naming.run_all_checks()
