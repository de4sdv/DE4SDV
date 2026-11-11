// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Frames, decodes and records one sample of the driving operational state.
//
// The bytes a typed subscriber receives for the broker's bytes publication are
// located by SlotFramer, then parsed by the generated protobuf class of the
// ICD message (contract/observed/de4sdv_driving_operational_state.proto). No
// field is read out of the wire format by hand: the generated parser is the only
// reader of the payload, and the record is built from the parsed message.
//
// The record is the ICD section 6 line, one per receipt:
//   {"t_mono_ns":..,"t_real_ns":..,"host":"guest","component":"observer",
//    "event":"in.operational_state","seq":N,"data":{..}}
// t_mono_ns is CLOCK_MONOTONIC (System.nanoTime) and t_real_ns is CLOCK_REALTIME
// at millisecond granularity (System.currentTimeMillis * 1e6: the Java API of
// this image gives no nanosecond realtime reading; the runbook states it).
// No latency is computed here: the record carries both stamps and the
// evaluators compute (ICD section 6, "Timing").
package org.de4sdv.drivingstate;

import com.google.protobuf.InvalidProtocolBufferException;

import de4sdv.driving.v1.DrivingOperationalState;

import java.util.Arrays;
import java.util.List;
import java.util.Locale;

final class OperationalStateDecoder {

    /** The one logcat tag of the observer: lifecycle, subscription and receipts. */
    static final String LOGCAT_TAG = "DE4SDV_DRIVING_STATE";

    static final String HOST = "guest";
    static final String COMPONENT = "observer";
    static final String EVENT = "in.operational_state";

    private static final int kSchemaMajor = 1;

    private OperationalStateDecoder() {}

    static final class Decoded {
        final DrivingOperationalState state;
        final SlotFramer.Layout layout;
        final int payloadBytes;
        final String contractProblem;

        Decoded(DrivingOperationalState state, SlotFramer.Layout layout, int payloadBytes,
                String contractProblem) {
            this.state = state;
            this.layout = layout;
            this.payloadBytes = payloadBytes;
            this.contractProblem = contractProblem;
        }

        boolean contractOk() {
            return contractProblem.isEmpty();
        }
    }

    static final class DecodeException extends Exception {
        final String reason;
        final String hex;

        DecodeException(String reason, String hex) {
            super(reason);
            this.reason = reason;
            this.hex = hex;
        }
    }

    static Decoded decode(byte[] delivered) throws DecodeException {
        final SlotFramer.Framed framed = SlotFramer.frame(delivered);
        switch (framed.layout) {
            case EMPTY:
                throw new DecodeException("empty_payload", "");
            case INVALID:
                throw new DecodeException(framed.reason, SlotFramer.hexPrefix(delivered, 16));
            case CARRIER:
            case DIRECT:
                break;
        }

        final byte[] payload = Arrays.copyOfRange(delivered, framed.offset,
                framed.offset + framed.length);
        final DrivingOperationalState state;
        try {
            state = DrivingOperationalState.parseFrom(payload);
        } catch (InvalidProtocolBufferException error) {
            throw new DecodeException("protobuf_" + error.getClass().getSimpleName()
                    + ":" + framed.layout, SlotFramer.hexPrefix(payload, 16));
        }

        String problem = "";
        if (state.getSchemaMajor() != kSchemaMajor) {
            problem = "schema_major_" + state.getSchemaMajor();
        } else if (state.getKindValue() < 1 || state.getKindValue() > 3) {
            problem = "kind_" + state.getKindValue();
        }
        return new Decoded(state, framed.layout, payload.length, problem);
    }

    static String kindName(int kindValue) {
        switch (kindValue) {
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

    /**
     * The ICD section 6 record, with the full payload: the plan's four arrays
     * are written in full here. The logcat line of the same receipt is
     * logcatLine(), because logcat truncates a line at about 4 KiB.
     */
    static String jsonRecord(long tMonoNs, long tRealNs, long receiptSeq, Decoded decoded) {
        final DrivingOperationalState state = decoded.state;
        final StringBuilder json = new StringBuilder(4096);
        json.append('{');
        json.append("\"t_mono_ns\":").append(tMonoNs);
        json.append(",\"t_real_ns\":").append(tRealNs);
        json.append(",\"host\":\"").append(HOST).append('"');
        json.append(",\"component\":\"").append(COMPONENT).append('"');
        json.append(",\"event\":\"").append(EVENT).append('"');
        json.append(",\"seq\":").append(receiptSeq);
        json.append(",\"data\":{");
        json.append("\"schema_major\":").append(state.getSchemaMajor());
        json.append(",\"schema_minor\":").append(state.getSchemaMinor());
        json.append(",\"kind\":\"").append(kindName(state.getKindValue())).append('"');
        json.append(",\"sequence\":").append(state.getSequence());
        json.append(",\"producer\":\"").append(quote(state.getProducer())).append('"');
        json.append(",\"publish_time_real\":").append(number(state.getPublishTimeReal()));
        json.append(",\"publish_time_mono\":").append(number(state.getPublishTimeMono()));
        json.append(",\"contract_ok\":").append(decoded.contractOk());
        if (!decoded.contractOk()) {
            json.append(",\"contract_problem\":\"").append(quote(decoded.contractProblem)).append('"');
        }
        json.append(",\"payload_bytes\":").append(decoded.payloadBytes);
        json.append(",\"layout\":\"").append(decoded.layout.name()).append('"');

        switch (state.getKindValue()) {
            case 1:
                json.append(",\"plan_frame_index\":").append(state.getPlanFrameIndex());
                json.append(",\"plan_capture_time\":").append(number(state.getPlanCaptureTime()));
                json.append(",\"plan_production_time\":").append(number(state.getPlanProductionTime()));
                json.append(",\"plan_reference\":\"").append(quote(state.getPlanReference())).append('"');
                json.append(",\"run_record\":\"").append(quote(state.getRunRecord())).append('"');
                appendFloats(json, "plan_acceleration", state.getPlanAccelerationList());
                appendFloats(json, "plan_curvature", state.getPlanCurvatureList());
                appendFloats(json, "plan_x", state.getPlanXList());
                appendFloats(json, "plan_y", state.getPlanYList());
                break;
            case 2:
                json.append(",\"speed_kmh\":").append(number(state.getSpeedKmh()));
                json.append(",\"longitudinal_acceleration\":")
                        .append(number(state.getLongitudinalAcceleration()));
                json.append(",\"lateral_acceleration\":").append(number(state.getLateralAcceleration()));
                json.append(",\"yaw_rate_dps\":").append(number(state.getYawRateDps()));
                json.append(",\"sample_capture_time\":").append(number(state.getSampleCaptureTime()));
                json.append(",\"sample_receipt_time_mono\":")
                        .append(number(state.getSampleReceiptTimeMono()));
                break;
            case 3:
                json.append(",\"mode\":").append(state.getMode());
                json.append(",\"cause\":").append(state.getCause());
                json.append(",\"mode_source\":\"").append(quote(state.getModeSource())).append('"');
                json.append(",\"cause_since_mono\":").append(number(state.getCauseSinceMono()));
                json.append(",\"last_plan_frame_index\":").append(state.getLastPlanFrameIndex());
                json.append(",\"dropped_samples\":").append(state.getDroppedSamples());
                break;
            default:
                break;
        }
        json.append("}}");
        return json.toString();
    }

    /** The same receipt, short enough for one logcat line. */
    static String logcatLine(long receiptSeq, Decoded decoded) {
        final DrivingOperationalState state = decoded.state;
        final StringBuilder line = new StringBuilder(320);
        line.append("seq=").append(receiptSeq);
        line.append(" kind=").append(kindName(state.getKindValue()));
        line.append(" sequence=").append(state.getSequence());
        line.append(" schema=").append(state.getSchemaMajor()).append('.').append(state.getSchemaMinor());
        line.append(" publish_time_real=").append(number(state.getPublishTimeReal()));
        switch (state.getKindValue()) {
            case 1:
                line.append(" frame=").append(state.getPlanFrameIndex());
                line.append(" capture_time=").append(number(state.getPlanCaptureTime()));
                line.append(" points=").append(state.getPlanXCount());
                line.append(" run_record=").append(state.getRunRecord());
                break;
            case 2:
                line.append(" speed_kmh=").append(number(state.getSpeedKmh()));
                line.append(" capture_time=").append(number(state.getSampleCaptureTime()));
                break;
            case 3:
                line.append(" mode=").append(state.getMode());
                line.append(" cause=").append(state.getCause());
                line.append(" cause_since_mono=").append(number(state.getCauseSinceMono()));
                break;
            default:
                break;
        }
        line.append(" payload_bytes=").append(decoded.payloadBytes);
        line.append(" layout=").append(decoded.layout.name());
        if (!decoded.contractOk()) {
            line.append(" contract=").append(decoded.contractProblem);
        }
        return line.toString();
    }

    private static void appendFloats(StringBuilder json, String name, List<Float> values) {
        json.append(",\"").append(name).append("\":[");
        for (int index = 0; index < values.size(); index++) {
            if (index > 0) {
                json.append(',');
            }
            json.append(number(values.get(index)));
        }
        json.append(']');
    }

    private static String number(double value) {
        if (Double.isNaN(value) || Double.isInfinite(value)) {
            // JSON has no NaN or Infinity; the ICD's floats are finite, so a
            // non-finite value is a contract violation worth seeing, not hiding.
            return "\"" + value + "\"";
        }
        return String.format(Locale.US, "%.17g", value);
    }

    private static String number(float value) {
        if (Float.isNaN(value) || Float.isInfinite(value)) {
            return "\"" + value + "\"";
        }
        return String.format(Locale.US, "%.9g", value);
    }

    private static String quote(String value) {
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
