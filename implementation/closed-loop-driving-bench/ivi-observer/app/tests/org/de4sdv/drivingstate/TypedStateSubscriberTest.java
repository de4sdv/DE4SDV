// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The subscriber's device-free parts: the names it claims and subscribes to
// follow the gateway's naming rules, every gateway failure is shown with its
// status code and message, and a Data Tunnel slot (varint-delimited message,
// zero-padded to the slot size) parses to the typed message. The gateway
// calls themselves need the guest.
package org.de4sdv.drivingstate;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import de4sdv.driving.v1.De4SdvDrivingOperationalState.DrivingOperationalState;

import google.sdv.gateway.client.SdvGatewayRuntimeException;
import google.sdv.gateway.client.SdvGatewayStatusCode;

import org.junit.Test;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.Arrays;

public class TypedStateSubscriberTest {

    @Test
    public void namesFollowTheGatewayRules() {
        assertEquals("", TypedStateSubscriber.namingProblem());
        assertEquals("org.de4sdv.drivingstate", TypedStateSubscriber.SUBJECT_PACKAGE);
        assertEquals("DrivingStateObserver", TypedStateSubscriber.SUBJECT_BUNDLE);
        assertEquals("com.android.sdv.someip", TypedStateSubscriber.PUBLISHER_PACKAGE);
        assertEquals("SomeIpBroker", TypedStateSubscriber.PUBLISHER_BUNDLE);
        // The three service units of the mapping (keys 0, 1, 2), in event order.
        assertEquals(Arrays.asList("de4sdv-driving-operational-state-plan",
                "de4sdv-driving-operational-state-vehicle-state",
                "de4sdv-driving-operational-state-health"), TypedStateSubscriber.PUBLISHER_UNITS);
        assertEquals("de4sdv.driving.v1.DrivingOperationalState", TypedStateSubscriber.MESSAGE_NAME);
    }

    @Test
    public void eachUnitCarriesOneKind() {
        assertEquals(1, TypedStateSubscriber.expectedKind(TypedStateSubscriber.UNIT_PLAN));
        assertEquals(2, TypedStateSubscriber.expectedKind(TypedStateSubscriber.UNIT_VEHICLE_STATE));
        assertEquals(3, TypedStateSubscriber.expectedKind(TypedStateSubscriber.UNIT_HEALTH));
        assertEquals(0, TypedStateSubscriber.expectedKind("de4sdv-driving-operational-state"));
    }

    @Test
    public void theLinkIsSubscribedOnlyWhenEveryUnitIs() {
        final String s = TypedStateSubscriber.LINK_SUBSCRIBED;
        final String w = TypedStateSubscriber.LINK_WAITING;
        final String u = TypedStateSubscriber.LINK_UNAVAILABLE;
        assertEquals(s, TypedStateSubscriber.aggregateLink(Arrays.asList(s, s, s)));
        assertEquals(w, TypedStateSubscriber.aggregateLink(Arrays.asList(s, w, s)));
        assertEquals(w, TypedStateSubscriber.aggregateLink(Arrays.asList(w, w, w)));
        assertEquals(u, TypedStateSubscriber.aggregateLink(Arrays.asList(s, s, u)));
        assertEquals(u, TypedStateSubscriber.aggregateLink(Arrays.asList(w, u, s)));
        assertEquals(w, TypedStateSubscriber.aggregateLink(Arrays.<String>asList()));
    }

    @Test
    public void gatewayFailuresCarryTheirStatusAndMessage() {
        // The client's exception text already carries the code (G/SdvGatewayRuntimeException.java
        // getMessage()); describe() must not lose or duplicate it.
        assertEquals("no ACL for org.de4sdv.drivingstate.DrivingStateObserver (statusCode 7: PERMISSION_DENIED)",
                TypedStateSubscriber.describe(new SdvGatewayRuntimeException(SdvGatewayStatusCode.PERMISSION_DENIED,
                        "no ACL for org.de4sdv.drivingstate.DrivingStateObserver")));
        assertEquals("IOException: Truncated message",
                TypedStateSubscriber.describe(new IOException("Truncated message")));
    }

    private static DrivingOperationalState sample() {
        final DrivingOperationalState.Builder b = DrivingOperationalState.newBuilder()
                .setSchemaMajor(2).setKind(1).setSequence(812).setProducer("statePublisher")
                .setPublishRealS(1762742400).setPublishRealNs(420_000_000)
                .setPlanFrameIndex(1234).setPlanCaptureMs(123400)
                .setPlanReference("0123456789abcdef/1234").setRunRecord("0123456789abcdef")
                .setPlanProducer("drivingAgent/inferPlan").setPlanSampleCount(64).setPlanHorizonS(6.4f);
        for (int i = 0; i < 64; i++) {
            b.addPlanAcceleration(0.5f).addPlanCurvature(-0.047f).addPlanX(0.8f * (i + 1)).addPlanY(-0.01f * i);
        }
        b.setPlanFrameIndex(-1);   // uint32 4294967295 arrives as a negative Java int
        return b.build();
    }

    @Test
    public void aDelimitedZeroPaddedSlotParsesToTheTypedMessage() throws IOException {
        final DrivingOperationalState sent = sample();
        final ByteArrayOutputStream out = new ByteArrayOutputStream();
        sent.writeDelimitedTo(out);
        final byte[] slot = Arrays.copyOf(out.toByteArray(), 4096);   // the publisher's slot is zero-padded
        final DrivingOperationalState got = TypedStateSubscriber.parseSlot(slot);
        assertEquals(sent, got);
        final MessageMapper.Mapped mapped = MessageMapper.map(got);
        assertTrue(mapped.contractProblem, mapped.ok());
        assertEquals(4294967295L, mapped.fields.planFrameIndex);
        assertEquals(64, mapped.fields.planX.length);
        assertEquals(51.2f, mapped.fields.planX[63], 1e-4f);
        assertEquals("drivingAgent/inferPlan", mapped.fields.planProducer);
    }

    @Test
    public void anAllZeroSlotIsAnEmptyMessageAndTheMapperSaysSo() throws IOException {
        final DrivingOperationalState got = TypedStateSubscriber.parseSlot(new byte[256]);
        final MessageMapper.Mapped mapped = MessageMapper.map(got);
        assertEquals("schema_major_0", mapped.contractProblem);
    }

    @Test(expected = IOException.class)
    public void aTruncatedSlotIsAParseFailureNotAMessage() throws IOException {
        final ByteArrayOutputStream out = new ByteArrayOutputStream();
        sample().writeDelimitedTo(out);
        TypedStateSubscriber.parseSlot(Arrays.copyOf(out.toByteArray(), 40));
    }

    @Test(expected = IOException.class)
    public void anEmptySlotIsAParseFailure() throws IOException {
        TypedStateSubscriber.parseSlot(new byte[0]);
    }
}
