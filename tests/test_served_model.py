"""Served-model digest: one content identity for the export and the API listing.

The pinned Systems Modeling API returns every exported element with all its
fields equal and pads it with schema fields that carry no value (null or
empty). The digest must be equal for both forms, independent of listing
order, and must change when any element, field value or carried field changes.
"""
import pytest

from de4sdv.sysml_api.served_model import (
    SERVED_MODEL_SCHEMA,
    ServedModel,
    element_digests,
    normalized_element,
    payload_differences,
    served_model_digest,
)

EXPORT = [
    {"@id": "a", "@type": "PartUsage", "declaredName": "brake", "owner": {"@id": "p"},
     "isAbstract": False, "multiplicity": 0},
    {"@id": "b", "@type": "RequirementUsage", "declaredName": "req",
     "ownedRelationship": [{"@id": "a"}]},
    {"@id": "p", "@type": "Package", "declaredName": "pkg"},
]


def _api_form(elements):
    """The API listing shape: same fields, plus valueless schema padding."""
    padded = []
    for element in reversed(elements):
        padded.append({**element, "qualifiedName": None, "documentation": [],
                       "aliasIds": [], "shortName": "", "extra": {}})
    return padded


def test_normalized_element_drops_only_valueless_top_level_fields():
    element = {"@id": "x", "none": None, "empty_list": [], "empty_map": {}, "empty_str": "",
               "zero": 0, "false": False, "nested": {"inner": None, "list": []}}
    assert normalized_element(element) == {
        "@id": "x", "zero": 0, "false": False, "nested": {"inner": None, "list": []}}


def test_export_and_api_listing_have_the_same_digest():
    assert served_model_digest(EXPORT) == served_model_digest(_api_form(EXPORT))


def test_digest_shape_and_order_independence():
    digest = served_model_digest(EXPORT)
    assert digest.startswith("sha256:") and len(digest) == len("sha256:") + 64
    assert served_model_digest(list(reversed(EXPORT))) == digest


@pytest.mark.parametrize("mutate", [
    lambda els: els["a"].__setitem__("declaredName", "brakes"),          # changed value
    lambda els: els["b"].__setitem__("ownedRelationship", [{"@id": "p"}]),  # changed reference
    lambda els: els.pop("p"),                                              # missing element
    lambda els: els.__setitem__("c", {"@id": "c", "@type": "PartUsage"}),  # extra element
    lambda els: els["p"].__setitem__("documentation", ["carried text"]),  # padding with a value
    lambda els: els["a"].__setitem__("multiplicity", None),               # value dropped
])
def test_any_content_change_changes_the_digest(mutate):
    changed = {element["@id"]: dict(element) for element in _api_form(EXPORT)}
    mutate(changed)
    assert served_model_digest(list(changed.values())) != served_model_digest(EXPORT)


@pytest.mark.parametrize("elements,match", [
    ([{"@type": "PartUsage"}], "no element id"),
    ([{"@id": "a"}, {"@id": "a"}], "duplicate element id"),
    (["not an object"], "not a JSON object"),
    ([], "empty"),
])
def test_malformed_corpus_is_refused(elements, match):
    with pytest.raises(ValueError, match=match):
        served_model_digest(elements)


def test_payload_differences_names_the_differing_ids():
    api = {element["@id"]: element for element in _api_form(EXPORT)}
    export = {element["@id"]: element for element in EXPORT}
    assert payload_differences(export, api) == []
    api["b"] = {**api["b"], "declaredName": "other"}
    assert payload_differences(export, api) == ["b"]
    assert set(element_digests(EXPORT)) == {"a", "b", "p"}


def _record(**changes):
    value = {"schema": SERVED_MODEL_SCHEMA, "source_export_sha256": "f" * 64,
             "element_count": 3, "content_sha256": served_model_digest(EXPORT)}
    value.update(changes)
    return value


def test_served_model_record_round_trips():
    record = ServedModel.from_dict(_record())
    assert record.to_dict() == _record()
    assert ServedModel.from_elements(EXPORT, source_export_sha256="f" * 64) == record


@pytest.mark.parametrize("changes,match", [
    ({"schema": "other/v1"}, "schema"),
    ({"source_export_sha256": "F" * 64}, "source_export_sha256"),
    ({"source_export_sha256": "sha256:" + "f" * 64}, "source_export_sha256"),
    ({"element_count": 0}, "element_count"),
    ({"element_count": True}, "element_count"),
    ({"content_sha256": "f" * 64}, "content_sha256"),
    ({"unexpected": 1}, "exactly"),
])
def test_malformed_served_model_record_is_refused(changes, match):
    with pytest.raises(ValueError, match=match):
        ServedModel.from_dict(_record(**changes))


def test_numbers_compare_by_value_like_the_api_serializer():
    """The export writes a LiteralRational value as 0, the pinned API as 0.0
    (4 elements of the 063c4fb1 release); the same number is the same value.
    Booleans stay booleans and non-integral numbers keep their exact value."""
    export = [{"@id": "r", "@type": "LiteralRational", "value": 0, "nested": [{"x": 2}]}]
    api = [{"@id": "r", "@type": "LiteralRational", "value": 0.0, "nested": [{"x": 2.0}],
            "qualifiedName": None}]
    assert served_model_digest(export) == served_model_digest(api)
    assert payload_differences({"r": export[0]}, {"r": api[0]}) == []
    assert served_model_digest([{"@id": "r", "value": True}]) != served_model_digest(
        [{"@id": "r", "value": 1}])
    assert served_model_digest([{"@id": "r", "value": 0.5}]) != served_model_digest(
        [{"@id": "r", "value": 0}])


def test_payload_differences_agree_with_the_digest_on_booleans():
    assert payload_differences({"r": {"@id": "r", "v": True}}, {"r": {"@id": "r", "v": 1}}) == ["r"]


# ---------------------------------------------------------------------------
# The revision binding carries the served-model record the importer wrote.
# ---------------------------------------------------------------------------


def test_binding_carries_the_served_model_record():
    from de4sdv.sysml_api.revisions import RevisionBinding
    from tests.model_contract_fixtures import binding_dict

    document = binding_dict(served_model=_record())
    binding = RevisionBinding.from_dict(document)
    assert binding.served_model == ServedModel.from_dict(_record())
    assert binding.to_dict()["served_model"] == _record()


def test_binding_without_a_served_model_keeps_its_exact_shape():
    from de4sdv.sysml_api.revisions import RevisionBinding
    from tests.model_contract_fixtures import binding_dict

    document = binding_dict()
    binding = RevisionBinding.from_dict(document)
    assert binding.served_model is None
    assert "served_model" not in binding.to_dict()
    assert set(binding.to_dict()) == set(document)


def test_binding_with_a_malformed_served_model_is_refused():
    from de4sdv.sysml_api.revisions import RevisionBinding
    from tests.model_contract_fixtures import binding_dict

    with pytest.raises(ValueError, match="served_model"):
        RevisionBinding.from_dict(binding_dict(served_model=_record(element_count=-1)))


# ---------------------------------------------------------------------------
# The repository adopts a corpus only after the installed guard accepts it.
# ---------------------------------------------------------------------------


class _Client:
    base_url = "http://api.invalid"

    def __init__(self, elements):
        self.elements = elements
        self.calls = 0

    def get_all(self, path):
        self.calls += 1
        return [dict(element) for element in self.elements]


def _guard_for(expected_digest):
    from de4sdv.sysml_api.errors import ServedModelMismatchError

    def guard(project_id, commit_id, elements):
        if served_model_digest(elements) != expected_digest:
            raise ServedModelMismatchError("served corpus differs from the validated export")
    return guard


def test_repository_refuses_a_network_corpus_the_guard_rejects():
    from de4sdv.sysml_api.errors import RevisionMismatchError, ServedModelMismatchError
    from de4sdv.sysml_api.repository import SysMLRepository

    repository = SysMLRepository(_Client(EXPORT[:-1]))
    written = []
    repository.install_corpus_source(lambda p, c: None, sink=lambda p, c, e: written.append(e))
    repository.install_corpus_guard(_guard_for(served_model_digest(EXPORT)))
    with pytest.raises(ServedModelMismatchError):
        repository.list_elements("p", "c")
    assert issubclass(ServedModelMismatchError, RevisionMismatchError)
    assert written == [] and repository._element_cache == {}
    with pytest.raises(ServedModelMismatchError):  # never memoized: refused again
        repository.list_elements("p", "c")


def test_repository_treats_a_rejected_snapshot_as_a_miss():
    from de4sdv.sysml_api.repository import SysMLRepository

    client = _Client(_api_form(EXPORT))
    repository = SysMLRepository(client)
    written = []
    stale = [{"@id": "stale", "@type": "Package"}]
    repository.install_corpus_source(lambda p, c: stale, sink=lambda p, c, e: written.append(e))
    repository.install_corpus_guard(_guard_for(served_model_digest(EXPORT)))
    elements = repository.list_elements("p", "c")
    assert client.calls == 1 and served_model_digest(elements) == served_model_digest(EXPORT)
    assert written == [elements]


def test_repository_adopts_a_snapshot_the_guard_accepts():
    from de4sdv.sysml_api.repository import SysMLRepository

    client = _Client([])
    repository = SysMLRepository(client)
    repository.install_corpus_source(lambda p, c: _api_form(EXPORT))
    repository.install_corpus_guard(_guard_for(served_model_digest(EXPORT)))
    assert served_model_digest(repository.list_elements("p", "c")) == served_model_digest(EXPORT)
    assert client.calls == 0
