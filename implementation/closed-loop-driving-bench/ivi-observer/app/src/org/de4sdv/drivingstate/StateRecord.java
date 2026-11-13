// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// One JSONL record of the observation path (ICD v2 section 6), built from the
// typed message the SDV Gateway delivers.
//
// Two properties matter here and both are tested (app/tests/.../StateRecordTest):
//
//  1. `data` is the message, field for field, with the ICD's own names and in the
//     ICD's order. There is no per-kind reshaping, no sum, no difference and no
//     derived number: the typed message already has the ICD's shape, so the
//     record is its faithful transcription. Evaluators compare it to
//     statePublisher.jsonl without a translation table.
//  2. `data.clocks` maps every time field to its clock (ICD section 6, C9):
//     `_ms` fields are simulation time, `_mono_*` are the S-CORE host's
//     monotonic clock, `publish_real_*` is real time. `t_real_ns` in the
//     envelope is the IVI's own receipt stamp, at millisecond granularity
//     (System.currentTimeMillis * 1e6): the image's Java API has no nanosecond
//     realtime read, and the runbook says so. No latency is computed here.
//
// This class has no Android and no protobuf import, so it compiles and runs as a
// plain JVM test on the build host as well as in the tree (MessageMapper is the
// only class that touches the generated message).
package org.de4sdv.drivingstate;

import java.util.Locale;

final class StateRecord {

    static final String HOST = "guest";
    static final String COMPONENT = "observer";
    static final String EVENT = "in.operational_state";

    /**
     * The 43 fields of the typed message, in ICD section 3 order. u32 is a long
     * (protobuf's uint32 arrives as a signed int; MessageMapper converts with
     * Integer.toUnsignedLong).
     */
    static final class Fields {
        long schemaMajor;
        long schemaMinor;
        long kind;
        long sequence;
        String producer = "";

        long publishRealS;
        long publishRealNs;
        long publishMonoS;
        long publishMonoNs;

        long planFrameIndex;
        long planCaptureMs;
        long planProductionMonoS;
        long planProductionMonoNs;
        String planReference = "";
        String runRecord = "";
        String planProducer = "";
        long planSampleCount;
        float planHorizonS;
        float[] planAcceleration = new float[0];
        float[] planCurvature = new float[0];
        float[] planX = new float[0];
        float[] planY = new float[0];

        float speedKmh;
        float longitudinalAcceleration;
        float lateralAcceleration;
        float yawRateDps;
        long sampleCaptureMs;
        long sampleReceiptMonoS;
        long sampleReceiptMonoNs;

        long mode;
        long cause;
        String modeSource = "";
        long causeSinceMonoS;
        long causeSinceMonoNs;
        long lastPlanFrameIndex;
        long lastPlanCaptureMs;
        long stepCaptureMs;
        long lastPlanProductionMonoS;
        long lastPlanProductionMonoNs;
        long droppedSamples;
        String checkpointExpectedSha256 = "";
        String checkpointActualSha256 = "";
        String refusalReason = "";
    }

    /** Every time field of the message, with its clock (ICD section 6, C9). */
    static final String CLOCKS_JSON =
            "{\"publish_real_s\":\"real\",\"publish_real_ns\":\"real\","
            + "\"publish_mono_s\":\"monotonic\",\"publish_mono_ns\":\"monotonic\","
            + "\"plan_capture_ms\":\"simulation\","
            + "\"plan_production_mono_s\":\"monotonic\",\"plan_production_mono_ns\":\"monotonic\","
            + "\"sample_capture_ms\":\"simulation\","
            + "\"sample_receipt_mono_s\":\"monotonic\",\"sample_receipt_mono_ns\":\"monotonic\","
            + "\"cause_since_mono_s\":\"monotonic\",\"cause_since_mono_ns\":\"monotonic\","
            + "\"last_plan_capture_ms\":\"simulation\",\"step_capture_ms\":\"simulation\","
            + "\"last_plan_production_mono_s\":\"monotonic\","
            + "\"last_plan_production_mono_ns\":\"monotonic\"}";

    private StateRecord() {}

    /** The `data` object: the 43 fields in ICD order, then `clocks`. */
    static String data(Fields f) {
        final StringBuilder json = new StringBuilder(4096);
        json.append('{');
        json.append("\"schema_major\":").append(f.schemaMajor);
        json.append(",\"schema_minor\":").append(f.schemaMinor);
        json.append(",\"kind\":").append(f.kind);
        json.append(",\"kind_name\":\"").append(kindName(f.kind)).append('"');
        json.append(",\"sequence\":").append(f.sequence);
        json.append(",\"producer\":\"").append(quote(f.producer)).append('"');
        json.append(",\"publish_real_s\":").append(f.publishRealS);
        json.append(",\"publish_real_ns\":").append(f.publishRealNs);
        json.append(",\"publish_mono_s\":").append(f.publishMonoS);
        json.append(",\"publish_mono_ns\":").append(f.publishMonoNs);
        json.append(",\"plan_frame_index\":").append(f.planFrameIndex);
        json.append(",\"plan_capture_ms\":").append(f.planCaptureMs);
        json.append(",\"plan_production_mono_s\":").append(f.planProductionMonoS);
        json.append(",\"plan_production_mono_ns\":").append(f.planProductionMonoNs);
        json.append(",\"plan_reference\":\"").append(quote(f.planReference)).append('"');
        json.append(",\"run_record\":\"").append(quote(f.runRecord)).append('"');
        json.append(",\"plan_producer\":\"").append(quote(f.planProducer)).append('"');
        json.append(",\"plan_sample_count\":").append(f.planSampleCount);
        json.append(",\"plan_horizon_s\":").append(number(f.planHorizonS));
        appendFloats(json, "plan_acceleration", f.planAcceleration);
        appendFloats(json, "plan_curvature", f.planCurvature);
        appendFloats(json, "plan_x", f.planX);
        appendFloats(json, "plan_y", f.planY);
        json.append(",\"speed_kmh\":").append(number(f.speedKmh));
        json.append(",\"longitudinal_acceleration\":").append(number(f.longitudinalAcceleration));
        json.append(",\"lateral_acceleration\":").append(number(f.lateralAcceleration));
        json.append(",\"yaw_rate_dps\":").append(number(f.yawRateDps));
        json.append(",\"sample_capture_ms\":").append(f.sampleCaptureMs);
        json.append(",\"sample_receipt_mono_s\":").append(f.sampleReceiptMonoS);
        json.append(",\"sample_receipt_mono_ns\":").append(f.sampleReceiptMonoNs);
        json.append(",\"mode\":").append(f.mode);
        json.append(",\"mode_name\":\"").append(modeName(f.mode)).append('"');
        json.append(",\"cause\":").append(f.cause);
        json.append(",\"cause_name\":\"").append(causeName(f.cause)).append('"');
        json.append(",\"mode_source\":\"").append(quote(f.modeSource)).append('"');
        json.append(",\"cause_since_mono_s\":").append(f.causeSinceMonoS);
        json.append(",\"cause_since_mono_ns\":").append(f.causeSinceMonoNs);
        json.append(",\"last_plan_frame_index\":").append(f.lastPlanFrameIndex);
        json.append(",\"last_plan_capture_ms\":").append(f.lastPlanCaptureMs);
        json.append(",\"step_capture_ms\":").append(f.stepCaptureMs);
        json.append(",\"last_plan_production_mono_s\":").append(f.lastPlanProductionMonoS);
        json.append(",\"last_plan_production_mono_ns\":").append(f.lastPlanProductionMonoNs);
        json.append(",\"dropped_samples\":").append(f.droppedSamples);
        json.append(",\"checkpoint_expected_sha256\":\"")
                .append(quote(f.checkpointExpectedSha256)).append('"');
        json.append(",\"checkpoint_actual_sha256\":\"")
                .append(quote(f.checkpointActualSha256)).append('"');
        json.append(",\"refusal_reason\":\"").append(quote(f.refusalReason)).append('"');
        json.append(",\"clocks\":").append(CLOCKS_JSON);
        json.append('}');
        return json.toString();
    }

    /** The whole ICD section 6 line for one receipt. */
    static String line(long tMonoNs, long tRealNs, long receiptSeq, Fields f) {
        return "{\"t_mono_ns\":" + tMonoNs
                + ",\"t_real_ns\":" + tRealNs
                + ",\"host\":\"" + HOST + "\""
                + ",\"component\":\"" + COMPONENT + "\""
                + ",\"event\":\"" + EVENT + "\""
                + ",\"seq\":" + receiptSeq
                + ",\"data\":" + data(f) + "}";
    }

    /** The envelope for a lifecycle or error line, with free-form data. */
    static String envelope(long tMonoNs, long tRealNs, String event, String dataFields) {
        return "{\"t_mono_ns\":" + tMonoNs
                + ",\"t_real_ns\":" + tRealNs
                + ",\"host\":\"" + HOST + "\""
                + ",\"component\":\"" + COMPONENT + "\""
                + ",\"event\":\"" + event + "\""
                + ",\"seq\":0"
                + ",\"data\":{" + dataFields + "}}";
    }

    static String kindName(long kind) {
        switch ((int) kind) {
            case 1:
                return "PLAN";
            case 2:
                return "VEHICLE_STATE";
            case 3:
                return "HEALTH";
            default:
                return "KIND_UNSPECIFIED";
        }
    }

    // Display labels only. The wire carries the number; the record carries both,
    // and the number is the field evaluators use.
    static String modeName(long mode) {
        switch ((int) mode) {
            case 0:
                return "kStarting";
            case 1:
                return "kDriving";
            case 2:
                return "kStopResponse";
            case 3:
                return "kStandstill";
            case 4:
                return "kRefused";
            default:
                return "unknown";
        }
    }

    static String causeName(long cause) {
        switch ((int) cause) {
            case 0:
                return "kNone";
            case 1:
                return "kCameraMissing";
            case 2:
                return "kCameraInvalid";
            case 3:
                return "kCameraStale";
            case 4:
                return "kMotionInvalid";
            case 5:
                return "kMotionStale";
            case 6:
                return "kRouteStale";
            case 7:
                return "kRouteEmpty";
            case 8:
                return "kPlanStale";
            case 9:
                return "kPlanInvalid";
            case 10:
                return "kCommandTimeout";
            case 11:
                return "kCheckpointRefused";
            case 12:
                return "kRunEnd";
            default:
                return "unknown";
        }
    }

    private static void appendFloats(StringBuilder json, String name, float[] values) {
        json.append(",\"").append(name).append("\":[");
        for (int index = 0; index < values.length; index++) {
            if (index > 0) {
                json.append(',');
            }
            json.append(number(values[index]));
        }
        json.append(']');
    }

    /** ICD section 6: a non-finite value is JSON null, never a quoted NaN. */
    private static String number(float value) {
        if (Float.isNaN(value) || Float.isInfinite(value)) {
            return "null";
        }
        return String.format(Locale.US, "%.9g", value);
    }

    static String quote(String value) {
        final StringBuilder text = new StringBuilder(value.length() + 8);
        for (int index = 0; index < value.length(); index++) {
            final char c = value.charAt(index);
            switch (c) {
                case '"':
                    text.append("\\\"");
                    break;
                case '\\':
                    text.append("\\\\");
                    break;
                case '\n':
                    text.append("\\n");
                    break;
                case '\r':
                    text.append("\\r");
                    break;
                case '\t':
                    text.append("\\t");
                    break;
                default:
                    if (c < 0x20) {
                        text.append(String.format(Locale.US, "\\u%04x", (int) c));
                    } else {
                        text.append(c);
                    }
            }
        }
        return text.toString();
    }
}
