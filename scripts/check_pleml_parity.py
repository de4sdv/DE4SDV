#!/usr/bin/env python3
"""The parity of the PLEML receipts with the YAML path (ADR 0022, plan step S4).

Until S7 the YAML path, ``tools/configure_variant.py`` on the catalogues and
the bills of features, is the oracle, and from S4 on this check gates every
step. It compares the committed PLEML receipts with the YAML path on the 25
rows of plan section 5:

* the 8 files of ``feature-configurations/``, each with its PLEML
  configuration;
* the 10 probes of the retained PLE-S comparison, their selections and names
  frozen from ``comparison.json``, whose digest is pinned (N12);
* 7 closed-world probes: the four unsupported application-middleware pairs,
  one hand-picked adapter, and the two allowed pairs that no other row
  exercises (R10).

A probe is a fenced PLEML configuration in ``fixtures/parity-probes/``, which
the licensed authority job serializes into the receipts like the invalid
fixture. Its YAML side is generated from the same frozen selection in a
temporary directory and never committed; it takes its description from the
probe, so that a valid row's bodies can be compared.

Each row compares validity, the reasons (R11), the derived variants, the
normalised projection body of a valid row (R19), and admission where the
retained record holds the YAML-era verdict. Two rejections need the same
multiset of (class, constraint, location) reasons, in count: a bound is
located by its group or feature, a pair exclusion by its pair of choices and a
hand-picked variant by its derived variation. No invalid configuration may be
admitted, on any row: admission requires validity. The receipt must restate
the row's selection, feature by feature through the catalogue paths it
records.
``not-expressible`` needs a construct on the pinned list as the sole YAML
violation, and the remainder is still compared (N3), its admission with the
verdict of the retained row that states the remainder. Every run asserts the
plan's histogram: 16 ``equal``, 8 ``both-reject``, 1 ``not-expressible`` and
0 ``defect``. Each of the seven committed projections must have one
normalised body on all three sides: the committed file, the YAML path and the
receipt, through the configurator's receipt mode.

The receipts are replayed first; a stale or non-reproducing receipt refuses
the run. Nothing here is a licensed run, a qualification or a native execution
of a PLEML expression.

Exit codes: 0 parity holds; 1 a defect, a histogram or a body differs;
2 refused (a receipt or the frozen record does not hold).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from de4sdv.semantic import pleml_receipts as receipts  # noqa: E402
from de4sdv.semantic import pleml_shadow  # noqa: E402
from scripts.run_pleml_configuration_evaluation import yaml_reason_keys, yaml_reasons  # noqa: E402

SCHEMA = "de4sdv.pleml-parity/v1"
PLE = Path("model-based-product-line-engineering")
CONFIGURATIONS = PLE / "feature-configurations"
PROBES = CONFIGURATIONS / "fixtures/parity-probes"
RECEIPTS = PLE / "feature-models/receipts"
PRODUCT_MODELS = PLE / "product-models"
CONFIGURATOR = pleml_shadow.CONFIGURATOR
#: The retained PLE-S comparison: the YAML-era record whose probe selections, names and admission verdicts the
#: parity freezes (N12). Its digest pins it; it is history and is never regenerated.
RECORD = Path("docs/product-line-engineering/ple-s-scope-alignment-evidence/comparison.json")
RECORD_SHA256 = "859f01acd248830dc1fe8ab11221d7eb45d0a3c3a90b94dc5ea8c9a98b9a2491"
#: The selection the closed-world probes vary: the standalone member, as the retained record holds it.
TEMPLATE = "standalone-member"
#: The histogram of plan section 5, asserted on every run until S7.
EXPECTED = {"equal": 16, "both-reject": 8, "not-expressible": 1, "defect": 0}
#: The states in which a feature is selected.
SELECTED = {"enabled", "implied"}


@dataclass(frozen=True)
class Probe:
    """A probe row: its PLEML configuration (by file stem) and its projection name.

    A frozen probe takes its selection and its name from the retained record,
    under its row identifier; the other probes vary the template's selection.
    """

    row: str
    stem: str
    name: str
    kind: str
    overrides: tuple[tuple[str, Any], ...] = ()

    @property
    def document(self) -> str:
        return (PROBES / f"{self.stem}.sysml").as_posix()


def _pair(application: str, middleware: str) -> tuple[tuple[str, Any], ...]:
    return (("PlatformStack.VehicleApplication", application), ("PlatformStack.Middleware", middleware))


#: The 17 probe rows, in the order of the runner's ``PARITY_PROBES``.
PROBE_ROWS = (
    Probe("both-alternatives", "both_integration_modes_probe", "BothIntegrationModesProbe", "frozen"),
    Probe("no-alternative", "no_integration_mode_probe", "NoIntegrationModeProbe", "frozen"),
    Probe("ug-09-autosar-acrn", "autosar_adaptive_acrn_probe", "AUTOSARAdaptiveACRNProbe", "frozen"),
    Probe("ug-10-openpilot-no-middleware", "openpilot_no_middleware_probe", "OpenpilotNoMiddlewareProbe", "frozen"),
    Probe("ug-10-radar-only", "radar_only_sensing_probe", "RadarOnlySensingProbe", "frozen"),
    Probe("ug-10-lidar-only", "lidar_only_sensing_probe", "LidarOnlySensingProbe", "frozen"),
    Probe("ug-10-camera-only", "camera_only_sensing_probe", "CameraOnlySensingProbe", "frozen"),
    Probe("ug-10-vehicle-target-aebs-false", "vehicle_target_aebs_off_probe", "VehicleTargetAEBSOffProbe", "frozen"),
    Probe("catalogue-only-adaptive-cruise-control", "adaptive_cruise_control_probe", "AdaptiveCruiseControlProbe",
          "frozen"),
    Probe("derived-set-mixed", "mixed_derived_set_probe", "MixedDerivedSetProbe", "frozen"),
    Probe("unsupported-openpilot-android-sdv", "openpilot_android_sdv_pair_probe", "OpenpilotAndroidSDVPairProbe",
          "closed-world", _pair("Openpilot", "AndroidSDV")),
    Probe("unsupported-openpilot-autosar-adaptive", "openpilot_autosar_adaptive_pair_probe",
          "OpenpilotAUTOSARAdaptivePairProbe", "closed-world", _pair("Openpilot", "AUTOSARAdaptive")),
    Probe("unsupported-apollo-android-sdv", "apollo_android_sdv_pair_probe", "ApolloAndroidSDVPairProbe",
          "closed-world", _pair("Apollo", "AndroidSDV")),
    Probe("unsupported-apollo-autosar-adaptive", "apollo_autosar_adaptive_pair_probe",
          "ApolloAUTOSARAdaptivePairProbe", "closed-world", _pair("Apollo", "AUTOSARAdaptive")),
    Probe("hand-picked-adapter", "hand_picked_adapter_probe", "HandPickedAdapterProbe", "closed-world",
          (("PlatformStack.ApplicationMiddlewareAdapter", "none"),)),
    Probe("pair-openpilot-eclipse-score", "openpilot_eclipse_score_pair_probe", "OpenpilotEclipseSCOREPairProbe",
          "pair", _pair("Openpilot", "EclipseSCORE")),
    Probe("pair-apollo-no-middleware", "apollo_no_middleware_pair_probe", "ApolloNoMiddlewarePairProbe", "pair",
          _pair("Apollo", "None")),
)

_BULLET = re.compile(r"^\s+[•-] (.+)$")
_VARIANT = re.compile(r"^\s*part :>> (\w+) = \w+::(\w+);\s*$", re.MULTILINE)
_REGENERATE = re.compile(r"^ \* Regenerate from: (.+)$", re.MULTILINE)
#: The configuration a projection names when the configurator wrote it from a receipt (since the switch, S6).
_CONFIGURATION = re.compile(r"^ \* Feature configuration: (\S+) \(", re.MULTILINE)


def projection_bill(text: str) -> str | None:
    """The bill of features of a committed projection, or ``None`` for a file that is no configured projection.

    A projection of the YAML path names its bill; one written from a receipt
    names its PLEML configuration, whose shadow is the bill beside it with the
    same stem in kebab case (ADR 0022, step S6).
    """
    source = _REGENERATE.search(text)
    if source is not None:
        return source.group(1).strip()
    configuration = _CONFIGURATION.search(text)
    if configuration is None:
        return None
    path = Path(configuration.group(1).strip())
    return path.with_name(path.stem.replace("_", "-") + ".yaml").as_posix()


class ParityRefused(ValueError):
    """The parity cannot run: a receipt or the frozen record does not hold, or the configurator refuses an input."""


@dataclass(frozen=True)
class Evaluated:
    """One configuration of a committed receipt, with what the projection writer reads beside it."""

    receipt_path: Path
    receipt: Mapping[str, Any]
    model: Mapping[str, Any]
    configuration: Mapping[str, Any]
    writer: Mapping[str, Any]
    catalogue: Path
    shared_assets: str


# -- inputs ---------------------------------------------------------------------------------


def load_record(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    """The retained comparison's rows by case, refused unless its bytes are the pinned ones."""
    data = (root / RECORD).read_bytes()
    if receipts.sha256(data) != RECORD_SHA256:
        raise ParityRefused(f"{RECORD} is not the retained record the probes freeze (N12): its sha256 is "
                            f"{receipts.sha256(data)}")
    return {row["case"]: row for row in json.loads(data)["rows"]}


def load_receipts(configurator: Any, root: Path = ROOT) -> dict[str, Evaluated]:
    """Every configuration of the committed receipts by its source document, after an offline replay."""
    paths = sorted((root / RECEIPTS).glob("*.receipt.json"))
    if not paths:
        raise ParityRefused(f"{RECEIPTS} holds no receipt")
    failures = receipts.replay_receipts(paths, root)
    if failures:
        raise ParityRefused("the committed receipts do not hold: " + "; ".join(failures))
    evaluated: dict[str, Evaluated] = {}
    elements: dict[Path, Mapping[str, str]] = {}
    for path in paths:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        shadow = receipt.get("shadow") or {}
        if not shadow.get("catalogue"):
            raise ParityRefused(f"{path.name} records no YAML shadow; the parity needs its catalogue until S7")
        writers = {item["tree"]: item["writer_inputs"] for item in shadow["feature_models"]}
        source = path.parent / receipt["elements"]["path"]
        if source not in elements:
            elements[source] = receipts.read_elements(source)["element_sources"]
        for model in receipt["evaluation"]["feature_models"]:
            try:
                shared = configurator.receipt_shared_assets(model, elements[source])
            except ValueError as exc:
                raise ParityRefused(str(exc)) from exc
            for configuration in model["configurations"]:
                if configuration["source"] in evaluated:
                    raise ParityRefused(f"{configuration['source']} is evaluated by two receipts")
                writer = writers.get(model["tree"]["name"], {}).get(configuration["configuration"])
                if writer is None:
                    raise ParityRefused(f"{path.name} records no writer inputs for {configuration['configuration']}")
                evaluated[configuration["source"]] = Evaluated(path, receipt, model, configuration, writer,
                                                               Path(shadow["catalogue"]["path"]), shared)
    return evaluated


def configuration_of(bill: Path) -> str:
    """The PLEML configuration of a bill of features: its stem in snake case, beside it (step S3)."""
    return bill.with_name(bill.stem.replace("-", "_") + ".sysml").as_posix()


# -- the two sides ----------------------------------------------------------------------------


def yaml_outcome(bill: Path, selections: Mapping[str, Any], evaluated: Evaluated, workspace: Path, label: str,
                 root: Path = ROOT) -> dict[str, Any]:
    """The configurator's verdict on one bill of features, as parity reason keys, with its projection body."""
    output = workspace / f"{label}.sysml"
    try:
        result = subprocess.run(
            [sys.executable, str(root / CONFIGURATOR), "--feature-model", str(root / evaluated.catalogue),
             "--bof", str(bill), "--shared-assets-model", str(root / evaluated.shared_assets), "--output",
             str(output)],
            capture_output=True, text=True, cwd=root, check=False, timeout=120)
    except subprocess.TimeoutExpired as exc:
        raise ParityRefused(f"{label}: the configurator did not finish within {exc.timeout} s") from exc
    if result.returncode not in (0, 1):
        raise ParityRefused(f"{label}: the configurator refused the input (exit {result.returncode}): "
                            f"{result.stderr.strip()[-400:]}")
    messages = [match.group(1).strip() for match in map(_BULLET.match, result.stderr.splitlines()) if match]
    catalogue = pleml_shadow.Catalogue(root / evaluated.catalogue, root)
    try:
        keys, counted = yaml_reason_keys(messages, selections, catalogue)
        located = yaml_reasons(messages, selections, catalogue)
    except ValueError as exc:
        raise ParityRefused(f"{label}: {exc}; the reason map of the parity needs it (R11)") from exc
    text = output.read_text(encoding="utf-8") if result.returncode == 0 else None
    return {"valid": result.returncode == 0, "keys": keys, "violations": counted,
            "reasons": [(item["class"], item["constraint"], tuple(item["location"]) if item["location"] else None)
                        for item in located],
            "derived_variants": dict(_VARIANT.findall(text or "")),
            "body": receipts.normalised_body(text) if text is not None else None, "messages": messages}


#: The classes whose reasons are compared by location: a bound by its group or feature, a pair exclusion by its
#: pair of choices (catalogue paths, until S7) and a hand-picked variant by its derived variation. A constraint
#: is located by its ID; the other classes are compared by class.
LOCATED_BY_FEATURES = {"lower-bound", "upper-bound", "pair-exclusion"}


def pleml_reasons(configuration: Mapping[str, Any], paths: Mapping[str, str | None]) -> list[tuple[Any, ...]]:
    """The receipt's reasons of a configuration as (class, constraint, location), comparable with the YAML's."""
    found = []
    for reason in configuration["reasons"]:
        kind = reason["class"]
        location = None
        if kind in LOCATED_BY_FEATURES:
            location = tuple(sorted(paths.get(feature) or f"{feature} (no catalogue path)"
                                    for feature in reason.get("features") or []))
        elif kind == "derived-variant-not-selectable":
            location = tuple(sorted(name.lower() for name in reason.get("variations") or []))
        found.append((kind, reason.get("constraint") if kind == "constraint" else None, location))
    return found


def pleml_outcome(evaluated: Evaluated, configurator: Any, root: Path = ROOT) -> dict[str, Any]:
    """The receipt's verdict on one configuration, with the body of its projection from the receipt."""
    configuration = evaluated.configuration
    body = None
    if configuration["valid"]:
        body = receipts.normalised_body(configurator.projection_file(configurator.receipt_projection(
            evaluated.receipt_path, evaluated.receipt, evaluated.model, configuration, evaluated.writer,
            evaluated.shared_assets, root)))
    return {"valid": configuration["valid"], "keys": receipts.reason_keys(configuration),
            "reasons": pleml_reasons(configuration, evaluated.writer["catalogue_paths"]),
            "derived_variants": {item["variation"]: item["variant"] for item in configuration["derived_variants"]},
            "rules": {item["variation"]: item["rule"] for item in configuration["derived_variants"] if "rule" in item},
            "body": body}


# -- what a row compares beyond classify_row ----------------------------------------------------


def restatement_errors(selections: Mapping[str, Any], evaluated: Evaluated) -> list[str]:
    """Where the configuration does not state the row's selection, feature by feature.

    The catalogue paths the receipt records (by short name, until S7) pair the
    two. A selection path without a feature (common content, or a path the
    catalogue does not know) is compared by its reason class instead.
    """
    paths = evaluated.writer["catalogue_paths"]
    by_catalogue = {catalogue: path for path, catalogue in paths.items() if catalogue}
    features = {feature["path"]: feature for feature in evaluated.model["features"]}
    states = evaluated.configuration["states"]
    errors = []
    stated = set()
    for key, value in selections.items():
        path = by_catalogue.get(key)
        if path is None:
            continue
        stated.add(path)
        feature = features[path]
        if feature["members"]:
            chosen = [value] if isinstance(value, str) else list(value) if isinstance(value, list) else None
            if chosen is None:
                errors.append(f"{key}: the selection {value!r} is no choice")
                continue
            want = sorted(f"{key}.{choice}" for choice in chosen)
            have = sorted(paths.get(member) or f"{member} (no catalogue path)" for member in feature["members"]
                          if states.get(member) in SELECTED)
            if want != have:
                errors.append(f"{key}: the selection chooses {want}, the configuration {have}")
        elif isinstance(value, bool):
            if states.get(path) != ("enabled" if value else "disabled"):
                errors.append(f"{key}: the selection is {value}, the configuration {states.get(path)}")
        else:
            errors.append(f"{key}: the selection {value!r} is no YAML Boolean")
    for path, feature in features.items():
        if path in stated or feature["group"] is not None:
            continue
        state = states.get(path)
        if feature["members"]:
            sets = state == "enabled" or any(states.get(member) in SELECTED for member in feature["members"])
        elif any(item["owner"] == path for item in features.values()):
            continue  # a grouping feature is structure, stated through its own features
        else:
            sets = state in {"enabled", "disabled"} and feature["multiplicity"]["lower"] == 0
        if sets:
            errors.append(f"{paths.get(path) or path}: the configuration sets it, the selection does not")
    return errors


def _admission(record_row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    verdict = (record_row or {}).get("admitted_by_governed_scope")
    if not verdict:
        return None
    return {"admitted": verdict["admitted"], "alternative": verdict.get("implied_alternative") if verdict["admitted"]
            else None}


def admission_of(configuration: Mapping[str, Any]) -> dict[str, Any]:
    admission = configuration["admission"]
    return {"admitted": admission.get("admitted"),
            "alternative": admission.get("alternative") if admission.get("admitted") else None}


def admission_problems(configuration: Mapping[str, Any], expected: Mapping[str, Any] | None) -> list[str]:
    """Where a configuration's admission breaks a rule: validity first, then the retained verdict.

    Admission requires validity: an invalid configuration is never admitted,
    on any row and whatever the retained record says.
    """
    problems = []
    admission = admission_of(configuration)
    if not configuration["valid"] and admission["admitted"] is not False:
        problems.append(f"an invalid configuration is admitted ({admission['admitted']}); admission requires "
                        "validity")
    if expected is not None and admission != dict(expected):
        problems.append(f"admission {admission} differs from the retained YAML-era verdict {dict(expected)}")
    return problems


def remainder(selections: Mapping[str, Any], catalogue: pleml_shadow.Catalogue) -> tuple[dict[str, Any], list[str]]:
    """The selection without the pinned construct (a common capability set to false), and the paths it drops."""
    dropped = [key for key, value in selections.items() if value is False and catalogue.nodes.get(key) is not None
               and str(catalogue.nodes[key].feature_id).startswith("C-")]
    return {key: value for key, value in selections.items() if key not in dropped}, dropped


def _record_row_with(record: Mapping[str, Mapping[str, Any]], selections: Mapping[str, Any]) -> Mapping[str, Any] | None:
    found = [row for row in record.values() if row["operational_input"]["selections"] == dict(selections)]
    return found[0] if len(found) == 1 else None


# -- the rows -----------------------------------------------------------------------------------


@dataclass
class Row:
    row: str
    kind: str
    bill: Path
    selections: dict[str, Any]
    name: str
    document: str
    expected_admission: dict[str, Any] | None
    #: The case of the retained record row whose admission verdict the row is compared with.
    admission_case: str | None = None


def rows(record: Mapping[str, Mapping[str, Any]], evaluated: Mapping[str, Evaluated], workspace: Path,
         root: Path = ROOT) -> list[Row]:
    """The 25 rows: the configuration files, then the probes."""
    by_path = {row["operational_input"].get("path"): row for row in record.values()
               if row["operational_input"].get("kind") == "committed"}
    result = []
    for bill in sorted((root / CONFIGURATIONS).rglob("*.yaml")):
        relative = bill.relative_to(root)
        data = pleml_shadow.load_configurator(root).load_yaml_unique(bill.read_text(encoding="utf-8"))
        retained = by_path.get(relative.as_posix())
        result.append(Row(relative.relative_to(CONFIGURATIONS).as_posix(), "file", bill, dict(data["selections"]),
                          data["name"], configuration_of(relative), _admission(retained),
                          retained["case"] if retained else None))
    template = record[TEMPLATE]["operational_input"]["selections"]
    for probe in PROBE_ROWS:
        evaluated_probe = evaluated.get(probe.document)
        if evaluated_probe is None:
            raise ParityRefused(f"{probe.row}: no committed receipt evaluates {probe.document}")
        if probe.kind == "frozen":
            source = record[probe.row]
            if source["operational_input"]["name"] != probe.name:
                raise ParityRefused(f"{probe.row}: the retained record names it {source['operational_input']['name']}")
            selections, expected, case = dict(source["operational_input"]["selections"]), _admission(source), probe.row
        else:
            selections, expected, case = {**template, **dict(probe.overrides)}, None, None
        bill = workspace / f"{probe.stem}.yaml"
        bill.write_text(yaml.safe_dump({"name": probe.name, "description": evaluated_probe.writer["description"],
                                        "selections": selections}, sort_keys=False), encoding="utf-8")
        result.append(Row(probe.row, probe.kind, bill, selections, probe.name, probe.document, expected, case))
    return result


def compare(row: Row, evaluated: Evaluated, configurator: Any, record: Mapping[str, Mapping[str, Any]],
            workspace: Path, root: Path = ROOT) -> dict[str, Any]:
    """One parity row: both outcomes, its class and every difference found."""
    label = row.row.replace("/", "-").removesuffix(".yaml")
    yaml_side = yaml_outcome(row.bill, row.selections, evaluated, workspace, label, root)
    pleml_side = pleml_outcome(evaluated, configurator, root)
    yaml_remainder = None
    expected_admission, admission_case = row.expected_admission, row.admission_case
    if any(item["row"] == row.row for item in receipts.NOT_EXPRESSIBLE):
        catalogue = pleml_shadow.Catalogue(root / evaluated.catalogue, root)
        kept, dropped = remainder(row.selections, catalogue)
        bill = workspace / f"{label}-remainder.yaml"
        bill.write_text(yaml.safe_dump({"name": row.name, "description": evaluated.writer["description"],
                                        "selections": kept}, sort_keys=False), encoding="utf-8")
        yaml_remainder = yaml_outcome(bill, kept, evaluated, workspace, f"{label}-remainder", root)
        # The row's own retained verdict counts the construct PLEML cannot state; its remainder is compared
        # with the verdict of the retained row that states the remainder's selection (N3).
        restored = {**kept, **{key: True for key in dropped}}
        retained = _record_row_with(record, restored)
        expected_admission, admission_case = _admission(retained), retained["case"] if retained else None
    result = receipts.classify_row(row.row, yaml_side, pleml_side, yaml_remainder=yaml_remainder)
    problems = [] if result["class"] != "defect" else [result["detail"]]
    if evaluated.configuration["projection_name"] != row.name:
        problems.append(f"the configuration projects {evaluated.configuration['projection_name']}, the row {row.name}")
    problems += [f"restatement: {error}" for error in restatement_errors(row.selections, evaluated)]
    problems += admission_problems(evaluated.configuration, expected_admission)
    admission = admission_of(evaluated.configuration)
    return {
        "row": row.row, "kind": row.kind, "class": "defect" if problems else result["class"],
        "detail": "; ".join(problems) if problems else result["detail"],
        "configuration": row.document,
        "yaml": {"valid": yaml_side["valid"], "reasons": sorted(_key(key) for key in yaml_side["keys"]),
                 "located": sorted(map(_located, yaml_side["reasons"])), "violations": yaml_side["violations"],
                 "derived_variants": yaml_side["derived_variants"]},
        "pleml": {"valid": pleml_side["valid"], "reasons": sorted(_key(key) for key in pleml_side["keys"]),
                  "located": sorted(map(_located, pleml_side["reasons"])),
                  "derived_variants": pleml_side["derived_variants"], "rules": pleml_side["rules"]},
        "admission": {"pleml": admission, "retained": expected_admission, "retained_case": admission_case,
                      "compared": expected_admission is not None},
        "bodies": {"yaml": yaml_side["body"], "pleml": pleml_side["body"]},
    }


def _key(key: tuple[str, str | None]) -> str:
    return key[0] if key[1] is None else f"{key[0]} {key[1]}"


def _located(reason: tuple[Any, ...]) -> str:
    kind, constraint, location = reason
    return " ".join([kind] + ([constraint] if constraint else []) + ([f"@{', '.join(location)}"] if location else []))


def projection_bodies(results: Iterable[Mapping[str, Any]], root: Path = ROOT) -> list[dict[str, Any]]:
    """Each committed projection's normalised body against the YAML path's and the receipt's (R19)."""
    by_bill = {(CONFIGURATIONS / result["row"]).as_posix(): result for result in results if result["kind"] == "file"}
    checked = []
    for projection in sorted((root / PRODUCT_MODELS).glob("*.sysml")):
        text = projection.read_text(encoding="utf-8")
        bill = projection_bill(text)
        if bill is None:
            continue  # not a configured projection
        result = by_bill.get(bill)
        committed = receipts.normalised_body(text)
        yaml_body = result["bodies"]["yaml"] if result else None
        pleml_body = result["bodies"]["pleml"] if result else None
        checked.append({"projection": projection.relative_to(root).as_posix(), "bill": bill,
                        "yaml_equal": yaml_body == committed, "pleml_equal": pleml_body == committed,
                        "equal": yaml_body == committed == pleml_body})
    return checked


def run(root: Path = ROOT) -> dict[str, Any]:
    """The parity report of the tree at ``root``; :class:`ParityRefused` when it cannot be decided."""
    record = load_record(root)
    configurator = pleml_shadow.load_configurator(root)
    evaluated = load_receipts(configurator, root)
    with tempfile.TemporaryDirectory(prefix="de4sdv-pleml-parity-") as directory:
        workspace = Path(directory)
        results = []
        planned = rows(record, evaluated, workspace, root)
        for row in planned:
            if row.document not in evaluated:
                raise ParityRefused(f"{row.row}: no committed receipt evaluates {row.document}")
            results.append(compare(row, evaluated[row.document], configurator, record, workspace, root))
    bodies = projection_bodies(results, root)
    histogram, failures = gate(results, bodies, set(evaluated) - {row.document for row in planned})
    return {"schema": SCHEMA, "rows": results, "histogram": histogram, "expected": EXPECTED, "bodies": bodies,
            "failures": failures, "native_expression_executed": False, "qualified": False}


#: The committed projections, one per valid configuration file, whose bodies the step compares.
PROJECTIONS = 7


def gate(results: Iterable[Mapping[str, Any]], bodies: Iterable[Mapping[str, Any]],
         uncovered: Iterable[str] = ()) -> tuple[dict[str, int], list[str]]:
    """The histogram of the rows and every reason the parity fails.

    It fails on a defect, on any histogram but the plan's, on a configuration
    without a parity row, and unless each valid configuration file has one
    committed projection whose body is equal on all three sides.
    """
    results, bodies = list(results), list(bodies)
    counts = Counter(result["class"] for result in results)
    histogram = {name: counts.get(name, 0) for name in EXPECTED}
    failures = [f"{result['row']}: defect: {result['detail']}" for result in results if result["class"] == "defect"]
    uncovered = sorted(uncovered)
    if uncovered:
        failures.append(f"configurations without a parity row: {uncovered}; parity gates every step, so each "
                        "PLEML configuration restates a bill of features or is a probe row")
    if histogram != EXPECTED or set(counts) - set(EXPECTED):
        failures.append(f"the histogram is {dict(counts)}, the plan expects {EXPECTED}")
    expected_bills = sorted((CONFIGURATIONS / result["row"]).as_posix() for result in results
                            if result["kind"] == "file" and result["pleml"]["valid"])
    if sorted(item["bill"] for item in bodies) != expected_bills or len(bodies) != PROJECTIONS:
        failures.append(f"the committed projections are {[item['projection'] for item in bodies]}, one per valid "
                        f"bill of features expected: {expected_bills}")
    failures += [f"{item['projection']}: the normalised bodies differ (YAML path equal: {item['yaml_equal']}, "
                 f"receipt equal: {item['pleml_equal']})" for item in bodies if not item["equal"]]
    return histogram, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", type=Path, help="write the full report here (a new file outside the repository)")
    args = parser.parse_args(argv)
    if args.json is not None and (args.json.exists() or args.json.resolve().is_relative_to(ROOT.resolve())):
        print("refused: --json must be a new file outside the repository", file=sys.stderr)
        return 2
    try:
        report = run(ROOT)
    except ParityRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    for result in report["rows"]:
        detail = f"  ({result['detail']})" if result["detail"] else ""
        print(f"{result['class']:16} {result['kind']:13} {result['row']}{detail}")
    print("histogram: " + ", ".join(f"{name} {count}" for name, count in report["histogram"].items())
          + f"  (expected: {', '.join(f'{name} {count}' for name, count in EXPECTED.items())})")
    for item in report["bodies"]:
        print(f"body {'equal' if item['equal'] else 'DIFFERS'}: {item['projection']}")
    for failure in report["failures"]:
        print(f"failed: {failure}", file=sys.stderr)
    if args.json is not None:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
