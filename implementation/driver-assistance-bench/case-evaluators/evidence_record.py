"""Lane D: the evidence record of each run of an S1 session, RetainedAssistanceRunEvidence
(textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml:150-243).

Every attribute of the item is filled from the fetched session tree, each from the one record named in
OBSERVABLES.md ("Lane D: the evidence record"). An attribute that no record fills stays empty and is named in
`missing` with the file and the field it was read from: "A missing or partial record gives inconclusive, never
pass" (:211-212). `setting` is the one attribute that may be empty: it is left empty for the further run (:182-183,
`AssistanceSettingIdentity[0..1]`).

    python3 evidence_record.py --session <incoming session root> --out records.json [--desk-044 file]

The CLI judges the session with evaluate_da_campaign.py (criteriaRecordIdentity, evaluatorRevision and the
outcomes for claimBoundary come from there) and writes the records alone.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from runio_da import STOP, EvidenceError, MissingEvidence, Run, Session  # noqa: E402

ATTRIBUTES = (
    "configurationIdentity", "receiptSha256", "modelRevision", "candidateRecordIdentity", "upstreamRevision",
    "sourceDifference", "networkFileSha256", "configurationFileSha256", "launchSettings", "candidateBuild",
    "visualizationRecorderDelay", "scoreLifecycleVersion", "scoreCommunicationVersion", "scoreSOMEIPGatewayCommit",
    "simulatorBuild", "scenario", "setting", "runIdentity", "simulatedConfiguration", "simulationClockSpan",
    "wallClockSpan", "executionEnvironmentIdentity", "contractIdentity", "criteriaRecordIdentity",
    "evaluatorRevision", "rawObservationArtifact", "benchRecordingArtifact", "independentEngineerIdentity",
    "claimBoundary",
)
COMPLETE = "complete"
INCONCLUSIVE = "inconclusiveMissingEvidence"
SCHEMA = "de4sdv.driving.retained-assistance-run-evidence.v1"
PROPOSAL = "OBSERVABLES.md PROPOSAL, lane D: no producer writes it yet"
NOT_PROVED = ("validation of the needs (this slice has no validation case); compliance with or approval under UNECE R152; "
              "that a driver perceives the warning; the candidate's behavior outside the settings and the runs "
              "recorded here; VC-DRIVING-036 and VC-DRIVING-037 are conditional on ASM-DRIVING-005, the calibration of "
              "the simulated deceleration")


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _nonempty_str(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _session_field(sess: Session, dotted: str, why: str = PROPOSAL) -> str:
    cur = sess.session
    for part in dotted.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else None
    if not _nonempty_str(cur):
        raise MissingEvidence(f"session.json {dotted} is {cur!r} ({why})")
    return cur


class _Ctx:
    def __init__(self, run: Run, sess: Session, criteria, revision, desk, outcomes):
        self.run, self.sess, self.criteria, self.revision = run, sess, criteria, revision
        self.desk, self.outcomes = desk, outcomes or {}

    def candidate_record(self) -> dict:
        rec = self.run.json_file("candidate_record")
        if not isinstance(rec, dict):
            raise EvidenceError(f"{self.run.label('candidate_record')} is not a JSON object")
        return rec

    def entry(self, key: str):
        return self.run.session_entry.get(key)


# ---------------------------------------------------------------- readers, one per attribute
def r_configuration_identity(c: _Ctx) -> str:
    return _session_field(c.sess, "configuration_identity")


def r_receipt(c: _Ctx) -> str:
    return _session_field(c.sess, "configuration_receipt_sha256")


def r_model_revision(c: _Ctx) -> str:
    return _session_field(c.sess, "bench_commit", "da_session.sh: the commit of the tree the session's kit came from")


def r_candidate_record_identity(c: _Ctx) -> str:
    for line in c.run.jsonl_file("identity"):
        d = line.get("data") if isinstance(line.get("data"), dict) else {}
        if line.get("event") == "record" and _nonempty_str(d.get("sha256")):
            return f"sha256:{d['sha256']} ({d.get('path')}, {d.get('bytes')} B)"
    raise MissingEvidence(f"{c.run.label('identity')}: no event record with data.sha256 (the identity recorder)")


def r_upstream(c: _Ctx) -> str:
    v = c.candidate_record().get("upstream_revision")
    if not _nonempty_str(v):
        raise MissingEvidence(f"{c.run.label('candidate_record')} upstream_revision is {v!r}")
    return v


def _patch_names(c: _Ctx) -> list:
    sd = c.candidate_record().get("source_difference")
    files = sd.get("files") if isinstance(sd, dict) else None
    return [f.get("name") for f in files or [] if isinstance(f, dict) and _nonempty_str(f.get("name"))]


def r_source_difference(c: _Ctx) -> str:
    sd = c.candidate_record().get("source_difference")
    if not isinstance(sd, dict) or not _nonempty_str(sd.get("sha256")) or not isinstance(sd.get("bytes"), int):
        raise MissingEvidence(f"{c.run.label('candidate_record')} source_difference.sha256 and .bytes: {sd!r:.80}")
    return f"sha256:{sd['sha256']}, {sd['bytes']} B: {', '.join(_patch_names(c)) or 'no file names'}"


def _file_list(c: _Ctx, key: str) -> str:
    items = c.candidate_record().get(key)
    rows = [f"{x.get('role')} {Path(str(x.get('path'))).name} sha256:{x['sha256']}" for x in items or []
            if isinstance(x, dict) and _nonempty_str(x.get("sha256"))]
    if not rows:
        raise MissingEvidence(f"{c.run.label('candidate_record')} {key}: no entry with sha256")
    return "; ".join(rows)


def r_network_files(c: _Ctx) -> str:
    return _file_list(c, "network_files")


def r_configuration_files(c: _Ctx) -> str:
    return _file_list(c, "configuration_files")


def r_launch_settings(c: _Ctx) -> str:
    ls = c.candidate_record().get("launch_settings")
    if not isinstance(ls, dict) or not ls:
        raise MissingEvidence(f"{c.run.label('candidate_record')} launch_settings is {ls!r:.60}")
    digest = hashlib.sha256(json.dumps(ls, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    n = len(ls.get("components") or [])
    return (f"sha256:{digest} of candidate_record.json launch_settings (canonical JSON; verbatim in that record): "
            f"{ls.get('launch_config_path')}, {n} components")


def r_candidate_build(c: _Ctx) -> str:
    cand = c.sess.session.get("candidate")
    bundle = cand.get("bundle") if isinstance(cand, dict) else None
    name = cand.get("name") if isinstance(cand, dict) else None
    source = "session.json candidate"
    if not _nonempty_str(bundle):
        try:
            st = c.run.json_file("staging")
        except MissingEvidence:
            st = None
        bundle = st.get("bundle") if isinstance(st, dict) else None
        source = c.run.label("staging")
    if not _nonempty_str(bundle):
        raise MissingEvidence(f"session.json candidate.bundle and {c.run.label('staging')} bundle: no bundle")
    patches = _patch_names(c) if c.run.paths.get("candidate_record") else []
    cr = c.candidate_record() if patches else {}
    up = cr.get("upstream_revision")
    what = f" at {up}" if _nonempty_str(up) else ""
    what += f" with {', '.join(patches)}" if patches else ""
    return f"{name or 'vision_pilot'}{what}; bundle {bundle} ({source})"


def r_recorder_delay(c: _Ctx) -> str:
    return _session_field(c.sess, "visualization_recorder_delay")


def r_lifecycle(c: _Ctx) -> str:
    return _session_field(c.sess, "score_platform.lifecycle_version")


def r_communication(c: _Ctx) -> str:
    return _session_field(c.sess, "score_platform.communication_version")


def r_gateway(c: _Ctx) -> str:
    return _session_field(c.sess, "score_platform.someip_gateway_commit")


def r_simulator_build(c: _Ctx) -> str:
    sim = c.run.setting_record().get("simulator")
    v = (sim.get("versions") or {}).get("server") if isinstance(sim, dict) else None
    if not _nonempty_str(v):
        raise MissingEvidence(f"{c.run.label('setting_record')} simulator.versions.server is {v!r} (the world side)")
    return f"{v} (CARLA server, {c.run.label('setting_record')} simulator.versions.server)"


def r_scenario(c: _Ctx) -> str:
    try:
        st = c.run.setting_record().get("setting")
        v = st.get("scenario") if isinstance(st, dict) else None
    except MissingEvidence:
        v = None
    v = v if _nonempty_str(v) else c.entry("scenario")
    if not _nonempty_str(v):
        raise MissingEvidence(f"{c.run.label('setting_record')} setting.scenario and session.json "
                              f"score_runs.{c.run.run_id}.scenario: no scenario")
    return v


def r_setting(c: _Ctx):
    if c.run.kind == "stop" or c.run.setting_id == STOP:
        return None                       # left empty for the further run (:182-183)
    if not _nonempty_str(c.run.setting_id):
        raise MissingEvidence(f"run {c.run.run_id}: no setting in setting_record.json or session.json")
    return c.run.setting_id


def r_run_identity(c: _Ctx) -> str:
    v = c.entry("runIdentity")
    if not _nonempty_str(v):
        raise MissingEvidence(f"session.json score_runs.{c.run.run_id}.runIdentity is {v!r} (da_session.sh, s1)")
    return v


def r_simulated_configuration(c: _Ctx) -> str:
    v = c.entry("simulatedConfiguration")
    sha = v.get("sha256") if isinstance(v, dict) else None
    if not _nonempty_str(sha):
        raise MissingEvidence(f"session.json score_runs.{c.run.run_id}.simulatedConfiguration.sha256 is {sha!r} "
                              "(da_session.sh, s1: the digest of the run's scenario definition)")
    return f"sha256:{sha} ({v.get('rule')}; {', '.join(v.get('files') or [])})"


def r_sim_span(c: _Ctx) -> str:
    t0, t1 = c.run.run_span()
    return f"{t0:.3f} s to {t1:.3f} s of simulation time ({c.run.label('world')} data.simTimeS, first to last tick)"


def _iso(ns: int) -> str:
    return datetime.datetime.fromtimestamp(ns / 1e9, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def r_wall_span(c: _Ctx) -> str:
    r0, r1 = c.run.tick_real_span()
    if not isinstance(r0, int) or not isinstance(r1, int):
        raise MissingEvidence(f"{c.run.label('world')}: t_real_ns of the first or the last tick line is missing")
    return f"{_iso(r0)} to {_iso(r1)} (the simulator host's real clock, {c.run.label('world')} t_real_ns)"


def r_environment(c: _Ctx) -> str:
    ips = c.sess.session.get("internal_ips_from_gcloud")
    ips = ips if isinstance(ips, dict) else {}
    ee = c.sess.session.get("execution_environment")
    ee = ee if isinstance(ee, dict) else {}
    absent = [f"internal_ips_from_gcloud.{r}" for r in ("sim", "score", "guest") if not _nonempty_str(ips.get(r))]
    absent += [f"execution_environment.{k} ({PROPOSAL})" for k in ("score_gpu", "sdv_core_image", "ivi_image")
               if not _nonempty_str(ee.get(k))]
    if absent:
        raise MissingEvidence("session.json " + ", ".join(absent))
    return (f"simulator host {ips['sim']}; S-CORE host {ips['score']} with {ee['score_gpu']}; guest host "
            f"{ips['guest']}: SDV Core image {ee['sdv_core_image']}, IVI image {ee['ivi_image']}")


def r_contract(c: _Ctx) -> str:
    for line in c.run.jsonl_file("receipts"):
        if line.get("event") == "lifecycle" and _nonempty_str(line.get("message")):
            return (f"{line['message']} (unit {line.get('unit')}, {line.get('translation')}; "
                    f"{c.run.label('receipts')} lifecycle)")
    raise MissingEvidence(f"{c.run.label('receipts')}: no lifecycle line with message (the IVI warning app)")


def r_criteria(c: _Ctx) -> str:
    if not _nonempty_str(c.criteria):
        raise MissingEvidence("no criteria record identity given (evaluate_da_campaign.py)")
    return c.criteria


def r_revision(c: _Ctx) -> str:
    if not _nonempty_str(c.revision):
        raise MissingEvidence("no evaluator revision given (evaluate_da_campaign.py)")
    return c.revision


RAW = (   # the retained records the item's doc lists (:199-204), each as the file that holds it
    ("candidate identity record", "candidate_record"),
    ("identity recorder log", "identity"),
    ("driving commands, warning requests and dropped images at the boundary", "score"),
    ("actuation adapter log (with the boundary records: the communication records of the S-CORE path)", "adapter"),
    ("simulator ground truth and control of the vehicle", "world"),
    ("warning presentation log", "receipts"),
)


def r_raw(c: _Ctx) -> str:
    rows, absent = [], []
    for role, key in RAW:
        try:
            p = c.run.file(key)
            rows.append(f"{role}: {c.run.label(key)} sha256:{_sha_file(p)}")
        except MissingEvidence as exc:
            absent.append(f"{role} ({exc})")
    try:
        rrd = c.run.json_file("candidate_rrd")
        rrd = rrd[0] if isinstance(rrd, list) and rrd else rrd
        if not isinstance(rrd, dict) or not _nonempty_str(rrd.get("sha256")):
            raise MissingEvidence(f"{c.run.label('candidate_rrd')}: no sha256")
        rows.append(f"candidate's data log: {rrd.get('path')} sha256:{rrd['sha256']} (kept on the S-CORE host)")
    except MissingEvidence as exc:
        absent.append(f"candidate's data log ({exc})")
    if absent:
        raise MissingEvidence("; ".join(absent))
    return "; ".join(rows)


def r_bench_recording(c: _Ctx) -> str:
    absent, rows = [], []
    try:
        rows.append(f"chase view {c.run.label('chase_view')} sha256:{_sha_file(c.run.file('chase_view'))}")
    except MissingEvidence as exc:
        absent.append(f"the chase view ({exc})")
    vr = c.entry("visualization_recording")
    if isinstance(vr, dict) and _nonempty_str(vr.get("sha256")):
        rows.append(f"the candidate's visualization recording {vr.get('path')} sha256:{vr['sha256']}")
    else:
        absent.append(f"the candidate's visualization recording that the recorder draws: session.json score_runs."
                      f"{c.run.run_id}.visualization_recording.sha256 ({PROPOSAL}; the Launch Manager configuration "
                      "does not set DE4SDV_VISUALIZATION_RECORD yet, score-interface/README.md)")
    if absent:
        raise MissingEvidence("; ".join(absent))
    return "; ".join(rows)


def r_engineer(c: _Ctx) -> str:
    v = (c.desk or {}).get("engineer")
    if not _nonempty_str(v):
        raise MissingEvidence("reproduction_044.json engineer: no desk reproduction of the candidate identity "
                              "(plan lane F2)")
    return v


def r_claim(c: _Ctx) -> str:
    out = c.outcomes.get(c.run.run_id) or {}
    what = "; ".join(f"{vc} {o}" for vc, o in sorted(out.items())) or "no case outcome given with this record"
    who = "the further run, no run of a setting" if c.run.kind == "stop" else f"setting {c.run.setting_id}"
    return (f"Run {c.run.run_id} ({who}). The record supports only these outcomes of the run, each under the named "
            f"criteriaRecordIdentity and evaluatorRevision: {what}. It does not prove: {NOT_PROVED}.")


READERS = {
    "configurationIdentity": r_configuration_identity, "receiptSha256": r_receipt, "modelRevision": r_model_revision,
    "candidateRecordIdentity": r_candidate_record_identity, "upstreamRevision": r_upstream,
    "sourceDifference": r_source_difference, "networkFileSha256": r_network_files,
    "configurationFileSha256": r_configuration_files, "launchSettings": r_launch_settings,
    "candidateBuild": r_candidate_build, "visualizationRecorderDelay": r_recorder_delay,
    "scoreLifecycleVersion": r_lifecycle, "scoreCommunicationVersion": r_communication,
    "scoreSOMEIPGatewayCommit": r_gateway, "simulatorBuild": r_simulator_build, "scenario": r_scenario,
    "setting": r_setting, "runIdentity": r_run_identity, "simulatedConfiguration": r_simulated_configuration,
    "simulationClockSpan": r_sim_span, "wallClockSpan": r_wall_span, "executionEnvironmentIdentity": r_environment,
    "contractIdentity": r_contract, "criteriaRecordIdentity": r_criteria, "evaluatorRevision": r_revision,
    "rawObservationArtifact": r_raw, "benchRecordingArtifact": r_bench_recording,
    "independentEngineerIdentity": r_engineer, "claimBoundary": r_claim,
}


def build(run: Run, sess: Session, *, criteria=None, revision=None, desk=None, outcomes=None) -> dict:
    """The evidence record of one run: every attribute, its value or None, and a missing text per empty one."""
    c = _Ctx(run, sess, criteria, revision, desk, outcomes)
    attrs, missing, empty = {}, [], []
    for name in ATTRIBUTES:
        try:
            attrs[name] = READERS[name](c)
        except (MissingEvidence, EvidenceError) as exc:
            attrs[name] = None
            empty.append(name)
            missing.append(f"{name}: {exc}")
    return {"schema": SCHEMA, "item": "RetainedAssistanceRunEvidence", "run": run.run_id, "kind": run.kind,
            "outcome": INCONCLUSIVE if empty else COMPLETE, "emptyAttributes": empty, "missing": missing,
            "attributes": attrs}


def build_all(sess: Session, *, criteria=None, revision=None, desk=None, outcomes=None) -> dict:
    runs = list(sess.runs) + ([sess.stop_run] if sess.stop_run is not None else [])
    return {r.run_id: build(r, sess, criteria=criteria, revision=revision, desk=desk, outcomes=outcomes)
            for r in runs}


def main(argv=None) -> int:
    import argparse

    import evaluate_da_campaign as edc
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--session", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--desk-044", type=Path, default=None)
    a = ap.parse_args(argv)
    doc = edc.run(a.session, a.desk_044)
    out = {"schema": SCHEMA, "session": doc["session"], "sessionId": doc.get("sessionId"),
           "criteriaRecordIdentity": doc.get("criteriaRecordIdentity"), "evaluatorRevision": doc.get("evaluatorRevision"),
           "refused": doc.get("refused"), "records": doc.get("evidenceRecords", {})}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    if doc.get("refused"):
        print(f"refused: {doc['refused']}")
        return 3
    for rid, rec in out["records"].items():
        print(" ".join([rid, rec["outcome"]] + rec["emptyAttributes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
