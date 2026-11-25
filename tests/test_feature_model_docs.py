"""Every feature of the PLEML feature models owns a short doc, its description.

A feature's description is one of its properties beside its ID, its name and its binding time. The viewer's
Feature Configurator shows the doc that a feature owns as that description, and a feature without one shows "The
model declares no documentation for this feature." These tests read the model text; they do not parse SysML.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FEATURE_MODELS = ROOT / "model-based-product-line-engineering" / "feature-models"

#: one feature declaration of a feature tree: ``;`` ends a feature without a body, ``{`` opens its body
_FEATURE = re.compile(
    r"#feature (?:#UnassignedBindingTime )?occurrence <'(?P<id>[^']+)'> (?P<name>\w+)\[[^\]]+\][^;{]*(?P<end>[;{])"
)
_DOC = re.compile(r"doc\s*/\*(?P<text>.*?)\*/", re.S)


def _masked(source: str) -> str:
    """The source with every comment body blanked, offsets kept, so that no brace inside a comment counts."""
    return re.sub(r"/\*.*?\*/", lambda m: "/*" + re.sub(r"[^\n]", " ", m.group()[2:-2]) + "*/", source, flags=re.S)


def _closing(masked: str, opening: int) -> int:
    depth = 0
    for index in range(opening, len(masked)):
        if masked[index] == "{":
            depth += 1
        elif masked[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    raise AssertionError("unbalanced braces")


def _own_doc(source: str, masked: str, opening: int) -> str | None:
    """The text of the doc that the body opened at ``opening`` owns directly, not one of a nested element."""
    depth = 0
    for index in range(opening + 1, _closing(masked, opening)):
        if masked[index] == "{":
            depth += 1
        elif masked[index] == "}":
            depth -= 1
        elif depth == 0 and masked.startswith("doc", index) and not re.match(r"[\w#]", masked[index - 1]):
            match = _DOC.match(source, index)
            if match:
                return " ".join(line.strip().lstrip("*").strip() for line in match["text"].splitlines()).strip()
    return None


def features(source: str) -> list[tuple[str, str, str | None]]:
    """``(ID, name, doc text or None)`` of every feature declared in ``source``, nested features included."""
    masked = _masked(source)
    found = [(m["id"], m["name"], _own_doc(source, masked, m.end() - 1) if m["end"] == "{" else None)
             for m in _FEATURE.finditer(masked)]
    assert masked.count("#feature ") == len(found), "a feature declaration form this reader does not know"
    return found


def _models() -> list[Path]:
    models = sorted(FEATURE_MODELS.glob("*.sysml"))
    assert len(models) == 3, models
    return models


def test_every_feature_of_the_feature_models_owns_a_doc() -> None:
    undocumented = [f"{path.name}: {feature_id} {name}"
                    for path in _models()
                    for feature_id, name, doc in features(path.read_text(encoding="utf-8")) if not doc]
    assert not undocumented, "features without a doc:\n" + "\n".join(undocumented)


def test_each_feature_model_declares_features_for_the_reader() -> None:
    for path in _models():
        assert len(features(path.read_text(encoding="utf-8"))) >= 10, path.name


def test_the_reader_finds_a_missing_doc_and_ignores_a_nested_one() -> None:
    """Synthetic text: a constraint's or a nested feature's doc is not the doc of its owning feature."""
    source = """
    #featureTree occurrence def <'PL-X'> XTree {
        doc /* the tree { with a brace in its comment */
        #feature occurrence <'F-A'> a[1] {
            doc /* A, the group
                 * of two lines. */
        }
        #feature occurrence <'F-B'> b[0..1] :> a default null;
        #feature occurrence <'F-C'> c[0..1] :> a default null {
            assert constraint <'C001'> cRequiresB :> requiresFeatures {
                doc /* only the constraint's doc */
                in occurrence constrainedFeatures = new FeatureOperand(that, b);
            }
        }
        #feature occurrence <'F-D'> d[1] {
            #feature #UnassignedBindingTime occurrence <'F-E'> e[0..1] default null {
                doc /* E only */
            }
        }
    }
    """
    assert features(source) == [
        ("F-A", "a", "A, the group of two lines."),
        ("F-B", "b", None),
        ("F-C", "c", None),
        ("F-D", "d", None),
        ("F-E", "e", "E only"),
    ]
