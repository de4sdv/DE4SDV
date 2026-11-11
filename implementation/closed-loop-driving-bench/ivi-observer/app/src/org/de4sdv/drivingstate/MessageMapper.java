// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The one class that touches the generated protobuf message: it copies the typed
// DrivingOperationalState into StateRecord.Fields and names any contract problem
// it sees. Nothing is decoded from bytes here, because nothing arrives as bytes:
// the broker translated the SOME/IP struct in REFLECTION mode and the gateway
// hands this process the protobuf message.
//
// Two checks are worth having even though the platform did the translation:
//
//  * schema_major: the ICD pins 2 (section 3, row 1). A wrong value means the
//    S-CORE side and this reader disagree about the contract, which is exactly
//    the drift the typed path is supposed to make impossible to miss.
//  * all-defaults-per-kind: protobuf cannot tell "field absent" from "field
//    zero", so if every field of the message's kind is still at its default the
//    likely cause is a field_name that does not match the protobuf field name
//    (REFLECTION matches by name), and the record says so instead of drawing an
//    idle car. It applies to PLAN and VEHICLE_STATE, whose real messages always
//    carry a non-default field; a HEALTH heartbeat before the agent's first mode
//    is all defaults by value and is left alone.
package org.de4sdv.drivingstate;

// The generated lite class: the contract has no java_multiple_files option, so
// protoc nests the message in the file's outer class De4SdvDrivingOperationalState.
import de4sdv.driving.v1.De4SdvDrivingOperationalState.DrivingOperationalState;

import java.util.List;

final class MessageMapper {

    static final long SCHEMA_MAJOR = 2;

    private MessageMapper() {}

    static final class Mapped {
        final StateRecord.Fields fields;
        final String contractProblem;
        final boolean allDefaults;

        Mapped(StateRecord.Fields fields, String contractProblem, boolean allDefaults) {
            this.fields = fields;
            this.contractProblem = contractProblem;
            this.allDefaults = allDefaults;
        }

        boolean ok() {
            return contractProblem.isEmpty();
        }
    }

    static long u32(int value) {
        // protobuf's uint32 is generated as a signed Java int.
        return Integer.toUnsignedLong(value);
    }

    static Mapped map(DrivingOperationalState message) {
        final StateRecord.Fields f = new StateRecord.Fields();
        f.schemaMajor = u32(message.getSchemaMajor());
        f.schemaMinor = u32(message.getSchemaMinor());
        f.kind = u32(message.getKind());
        f.sequence = u32(message.getSequence());
        f.producer = message.getProducer();
        f.publishRealS = u32(message.getPublishRealS());
        f.publishRealNs = u32(message.getPublishRealNs());
        f.publishMonoS = u32(message.getPublishMonoS());
        f.publishMonoNs = u32(message.getPublishMonoNs());

        f.planFrameIndex = u32(message.getPlanFrameIndex());
        f.planCaptureMs = u32(message.getPlanCaptureMs());
        f.planProductionMonoS = u32(message.getPlanProductionMonoS());
        f.planProductionMonoNs = u32(message.getPlanProductionMonoNs());
        f.planReference = message.getPlanReference();
        f.runRecord = message.getRunRecord();
        f.planProducer = message.getPlanProducer();
        f.planSampleCount = u32(message.getPlanSampleCount());
        f.planHorizonS = message.getPlanHorizonS();
        f.planAcceleration = floats(message.getPlanAccelerationList());
        f.planCurvature = floats(message.getPlanCurvatureList());
        f.planX = floats(message.getPlanXList());
        f.planY = floats(message.getPlanYList());

        f.speedKmh = message.getSpeedKmh();
        f.longitudinalAcceleration = message.getLongitudinalAcceleration();
        f.lateralAcceleration = message.getLateralAcceleration();
        f.yawRateDps = message.getYawRateDps();
        f.sampleCaptureMs = u32(message.getSampleCaptureMs());
        f.sampleReceiptMonoS = u32(message.getSampleReceiptMonoS());
        f.sampleReceiptMonoNs = u32(message.getSampleReceiptMonoNs());

        f.mode = u32(message.getMode());
        f.cause = u32(message.getCause());
        f.modeSource = message.getModeSource();
        f.causeSinceMonoS = u32(message.getCauseSinceMonoS());
        f.causeSinceMonoNs = u32(message.getCauseSinceMonoNs());
        f.lastPlanFrameIndex = u32(message.getLastPlanFrameIndex());
        f.lastPlanCaptureMs = u32(message.getLastPlanCaptureMs());
        f.stepCaptureMs = u32(message.getStepCaptureMs());
        f.lastPlanProductionMonoS = u32(message.getLastPlanProductionMonoS());
        f.lastPlanProductionMonoNs = u32(message.getLastPlanProductionMonoNs());
        f.droppedSamples = u32(message.getDroppedSamples());
        f.checkpointExpectedSha256 = message.getCheckpointExpectedSha256();
        f.checkpointActualSha256 = message.getCheckpointActualSha256();
        f.refusalReason = message.getRefusalReason();

        String problem = "";
        if (f.schemaMajor != SCHEMA_MAJOR) {
            problem = "schema_major_" + f.schemaMajor;
        } else if (f.kind < 1 || f.kind > 3) {
            problem = "kind_" + f.kind;
        } else if (f.producer.isEmpty()) {
            problem = "producer_empty";
        }
        return new Mapped(f, problem, kindIsAllDefault(f));
    }

    private static float[] floats(List<Float> values) {
        final float[] out = new float[values.size()];
        for (int index = 0; index < out.length; index++) {
            out[index] = values.get(index);
        }
        return out;
    }

    /**
     * True when every field of the message's kind is still at its default, for the kinds whose real
     * messages cannot be: a plan has samples and a reference, a vehicle state has a receipt stamp.
     * A HEALTH message can. Before drivingAgent offers its mode, statePublisher's heartbeat is
     * kStarting with no cause, no step, no plan and no source, which is the defaults: it is a real
     * message and is not counted.
     */
    static boolean kindIsAllDefault(StateRecord.Fields f) {
        switch ((int) f.kind) {
            case 1:
                return f.planFrameIndex == 0 && f.planCaptureMs == 0 && f.planSampleCount == 0
                        && f.planAcceleration.length == 0 && f.planX.length == 0
                        && f.planReference.isEmpty();
            case 2:
                return f.speedKmh == 0f && f.sampleCaptureMs == 0 && f.sampleReceiptMonoS == 0;
            default:
                return false;
        }
    }
}
