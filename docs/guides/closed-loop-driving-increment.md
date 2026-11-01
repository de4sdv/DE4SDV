# Closed-loop driving increment

DE4SDV needs to distinguish a driving function that actually influences vehicle
behavior from a prediction overlay on a separately driven car. This increment
proposes the former: real camera-based learned planning, a functional S-CORE
integration path, and an AAOS SDV application showing genuine plan/state/health.

**Status: Phase 0 framing proposal.** No implementation, successful driving run,
performance result or product-line admission is claimed.

## Authoritative frame

- [SysML framing model](../../textual-notation-of-model/packages/features/driving/closed_loop_driving_framing.sysml):
  `INC-DRIVING-001`, its engineering question, charter, scope and open gaps.
- [Pilot index](../../methodologies/sysmod-sysmlv2/pilots/driving-001-closed-loop.yaml):
  artifact locations only; it does not duplicate the model's meaning.
- [Syside framing review view](../../textual-notation-of-model/packages/features/driving/VIEWS.md):
  the generated, dense model review artifact, not a runtime architecture claim.
- [Upstream provenance and questions](../../textual-notation-of-model/packages/features/driving/upstream.md).

Orkun Yilmaz owns the increment. One identity covers phases 0 through 12;
CARLA closed-loop verification belongs to Phase 10 of this increment, with
readiness probes earlier in phases 6 through 8.

## Intended outcome, not an implemented architecture

The learned planner's output must influence steering and acceleration through
the S-CORE functional path and a controller back to CARLA. A direct bypass or
CARLA autopilot with an AI overlay is not equivalent evidence. AAOS SDV
Core/Gateway/IVI consumes the real plan, vehicle state and health; display
rendering does not belong in the fast vehicle-control loop.

The proposed driving-function boundary is a candidate **System 1** subject.
CARLA, cloud hosts and evidence/capture instruments are **System 2** enablers,
not vehicle features. Detailed boundaries and interfaces follow in Phase 2.
This framing does not modify the existing AEBS behavior, admit an automated-driving
member under [the current scope decision](../architecture-decisions/0014-ratify-initial-aebs-product-line-scope.md),
or claim production readiness, on-road suitability or safety approval.

## Timing and evidence boundary

The planning objective is at least **20 fresh rendered frames per wall-clock
second**, targeting **24 fps live capture** without speeding up a slow simulation.
These numbers are not model-invocation rates or fulfilled requirements. Simulation
real-time factor, inference cadence, input-to-actuation age, observation age and
capture continuity need separate evidence. Phase 5 must fix scenario, resolution,
duration, windows, drop tolerance and freshness/control deadlines before testing.

The released checkpoint must be evaluated with its compatible geometry and
history. Fast synthetic-input results do not prove its performance. Neither
interface compatibility nor recorded-input inference proves useful closed-loop
driving on CARLA imagery. Invalid, lost or stale plans require a defined
stop/disable response in simulation and retained failure-path evidence.

## Next obligation and execution limits

Use the reviewed revision's **Method Check** export to identify the first
unmet model-content obligation; it is not proof that earlier engineering
work is complete. The next work for this framing is **Phase 1 concern
framing**. The increment-boundary concern alone cannot open its exit: model
at least one concern of the driving capability's engineering scope, with
native stakeholders and a frame from a viewpoint of an increment view.
Review stakeholder and risk coverage and the selected viewpoints; the
structural gates do not assess their adequacy.

Phase 2 then develops the operational context: exactly one context holding
the system of interest, with stories bound to the subject and context actors.
Do not jump from this charter to implementation or claim a passed runtime gate.

Before deep adoption, involve upstream maintainers and resolve source,
checkpoint and data-use terms. Before a paid cloud run, refresh the regional
quote, capacity/storage and available credit; obtain campaign authorization and
verify bounded shutdown plus evidence export. Starting this increment does not
launch compute or authorize spend.

## Check the framing change

Run `sysand sync`, `python scripts/check_repo.py`, `python scripts/smoke_test.py`
and `python -m pytest tests/test_closed_loop_driving_framing.py tests/test_check_naming.py -q`.
These are repository/lexical checks, not SysML semantic or runtime verification.
Use `python scripts/validate_sysml.py` when a supported licensed validator is
available, or request maintainer-run **Privileged Syside Validation** on the
reviewed head. The framing view and its published artifacts must come from that
Syside run; no hand-drawn substitute establishes model validation.
