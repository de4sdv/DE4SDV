// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The gateway subscriber of the IVI observer: one subscription to the typed
// topic that the SOME/IP broker of the SDV Core VM publishes.
//
// It subscribes BY NAME to the broker's service unit, the way the two existing
// subscribers of a broker publication on this tree do it:
//   * the proven native relay of the AEBS frame bench subscribed to
//     instance1:com.android.sdv.someip.SomeIpBroker, unit de4sdv-score-aebs-signal-frame
//     (samples/ivi_frame_relay, options.hpp);
//   * the platform's SdvCarMonitorTestApp subscribes to the broker's FooMessage
//     unit with addListenerForServiceUnitChangeByName + subscribeToPublicationByName.
// The client's Subscriber.create() is NOT used: it discovers by unit type, which
// it derives from the message name (package de4sdv.driving.v1), and the mapping
// registers the unit type in package com.android.sdv.someip
// (interop/de4sdv_driving_operational_state.vsidl). Discovery by name does not
// depend on that, and every failure of the subscribe call reaches this class
// (Subscriber.create logs it under tag "Subscriber" and drops it).
//
// The message arrives typed: the broker translated the SOME/IP struct in
// REFLECTION mode on the SDV Core VM; nothing here decodes the SOME/IP bytes.
// The payload of a slot is the serialized DrivingOperationalState with a varint
// length prefix, zero-padded to the slot size: the client's own Subscriber
// parses exactly that with parseDelimitedFrom, and so does this class.
//
// Threading: everything runs on one executor. Gateway callbacks arrive on
// native threads attached by the JNI and are hopped onto the executor at once.
// The JNI holds one client per process: after any failure past initComms the
// client is closed before the next attempt, or every retry would fail with
// FAILED_PRECONDITION "Native SDV Gateway client instance already created".
//
// The subject identity (org.de4sdv.drivingstate / DrivingStateObserver) is the
// pair the two ACL files grant (interop/acl/). The observer publishes nothing,
// offers nothing and calls nothing on the driving side (REQ-DRIVING-018, -019).
package org.de4sdv.drivingstate;

import android.util.Log;

import com.google.protobuf.Parser;

import de4sdv.driving.v1.De4SdvDrivingOperationalState.DrivingOperationalState;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.regex.Pattern;

import google.sdv.gateway.client.SdvGatewayClient;
import google.sdv.gateway.client.SdvGatewayRuntimeException;
import google.sdv.gateway.client.SdvGatewayStatusCode;
import google.sdv.gateway.client.ServiceUnitChangeEventType;
import google.sdv.gateway.client.ServiceUnitDefinition;
import google.sdv.gateway.client.Subscription;
import google.sdv.gateway.client.SubscriptionNotificationType;
import google.sdv.gateway.client.UnitNameDiscoveryArgs;

final class TypedStateSubscriber {

    // The app's one logcat tag (the subscriber used to log under "observer", so the lines
    // RUNBOOK step 11 expects never appeared under `logcat -s DE4SDV_DRIVING_STATE`).
    private static final String TAG = "DE4SDV_DRIVING_STATE";

    // The subject this app claims (initComms) -- granted by interop/acl/.
    static final String SUBJECT_PACKAGE = "org.de4sdv.drivingstate";
    static final String SUBJECT_BUNDLE = "DrivingStateObserver";
    // The topic and its typed message (ICD section 3, MAP-DRIVING-OPERATIONAL-STATE).
    static final String TOPIC_NAME = "de4sdv-driving-operational-state";
    static final String MESSAGE_NAME = "de4sdv.driving.v1.DrivingOperationalState";
    // The publisher: the SOME/IP broker bundle of the SDV Core VM. The unit name
    // is key 0 of the mapping's sdv_service_unit_parameterization (= the topic).
    // An empty VM name matches the unit on any VM; the subscribe call then uses
    // the VM name the discovery event reports.
    static final String PUBLISHER_VM = "";
    static final String PUBLISHER_PACKAGE = "com.android.sdv.someip";
    static final String PUBLISHER_BUNDLE = "SomeIpBroker";
    static final String PUBLISHER_UNIT = TOPIC_NAME;

    static final Parser<DrivingOperationalState> PARSER = DrivingOperationalState.parser();

    private static final long kRetryDelayMs = 5000L;
    private static final long kPollPeriodMs = 100L;
    private static final int kReadBatch = 16;
    private static final int kMaxBatchesPerDrain = 8;

    // PF-004: bundle names start [A-Z]; service-unit names are [a-z0-9-], starting [a-z].
    private static final Pattern BUNDLE_NAME = Pattern.compile("[A-Z][A-Za-z0-9]*");
    private static final Pattern UNIT_NAME = Pattern.compile("[a-z][a-z0-9-]*");

    interface Sink {
        /** One parsed receipt; stamps are the IVI's, taken before the mapping. */
        void onState(MessageMapper.Mapped mapped, long tMonoNs, long tRealNs);

        /** A failure that does not end the subscription (parse failure, read error). */
        void onError(String reason, long tMonoNs, long tRealNs);

        /** The gateway reported DATA_LOSS: messages were skipped in the queue. */
        void onDataLoss(String reason, long tMonoNs, long tRealNs);

        /** Link state for the screen and the record: WAITING, SUBSCRIBED, UNAVAILABLE. */
        void onLink(String state, String detail);

        /** A lifecycle/config fact for the record (key, value). */
        void onConfig(String key, String value);
    }

    private final ScheduledExecutorService executor = Executors.newSingleThreadScheduledExecutor();
    private final Sink sink;

    // Owned by the executor thread.
    private SdvGatewayClient client;
    private boolean clientInitCalled;
    private AutoCloseable discovery;
    private Subscription subscription;
    private ServiceUnitDefinition publisher;
    private boolean polling;
    private volatile boolean running;

    TypedStateSubscriber(Sink sink) {
        this.sink = sink;
    }

    void start() {
        if (running) {
            return;
        }
        running = true;
        executor.execute(this::connect);
    }

    void stop() {
        running = false;
        executor.execute(this::closeAll);
        executor.shutdown();
    }

    /**
     * The gateway's own message for a gateway failure -- SdvGatewayRuntimeException.getMessage()
     * already ends in "(statusCode N: NAME)" -- and "<class>: <message>" for anything else.
     */
    static String describe(Throwable error) {
        if (error instanceof SdvGatewayRuntimeException) {
            return error.getMessage();
        }
        return error.getClass().getSimpleName() + ": " + error.getMessage();
    }

    /** Empty when the configured names follow the gateway's naming rules, else the reason. */
    static String namingProblem() {
        if (!BUNDLE_NAME.matcher(SUBJECT_BUNDLE).matches()) {
            return "subject bundle must start [A-Z]: " + SUBJECT_BUNDLE;
        }
        if (!BUNDLE_NAME.matcher(PUBLISHER_BUNDLE).matches()) {
            return "publisher bundle must start [A-Z]: " + PUBLISHER_BUNDLE;
        }
        if (!UNIT_NAME.matcher(PUBLISHER_UNIT).matches()) {
            return "service unit must be [a-z0-9-] starting [a-z]: " + PUBLISHER_UNIT;
        }
        return "";
    }

    /** One Data Tunnel slot to the typed message (varint-delimited, zero-padded). */
    static DrivingOperationalState parseSlot(byte[] slot) throws IOException {
        final DrivingOperationalState message = PARSER.parseDelimitedFrom(new ByteArrayInputStream(slot));
        if (message == null) {
            throw new IOException("empty slot");
        }
        return message;
    }

    // ------------------------------------------------------------------ executor thread

    private void connect() {
        if (!running) {
            return;
        }
        final String naming = namingProblem();
        if (!naming.isEmpty()) {
            sink.onLink("UNAVAILABLE", naming);
            return;
        }
        final SdvGatewayClient candidate = new SdvGatewayClient();
        try {
            clientInitCalled = true;
            client = candidate;
            candidate.initComms(SUBJECT_PACKAGE, SUBJECT_BUNDLE);
            Log.i(TAG, "lifecycle initComms package=" + SUBJECT_PACKAGE + " bundle=" + SUBJECT_BUNDLE);
            sink.onConfig("initComms", SUBJECT_PACKAGE + "." + SUBJECT_BUNDLE);

            final UnitNameDiscoveryArgs name = new UnitNameDiscoveryArgs(
                    PUBLISHER_VM, PUBLISHER_PACKAGE, PUBLISHER_BUNDLE, PUBLISHER_UNIT);
            discovery = candidate.addListenerForServiceUnitChangeByName(name,
                    (type, definition) -> post(() -> onUnitChanged(type, definition)));
            Log.i(TAG, "discovery by name vm='" + PUBLISHER_VM + "' package=" + PUBLISHER_PACKAGE
                    + " bundle=" + PUBLISHER_BUNDLE + " unit=" + PUBLISHER_UNIT);
            sink.onLink("WAITING", "for " + PUBLISHER_PACKAGE + "." + PUBLISHER_BUNDLE + " unit " + PUBLISHER_UNIT);
            if (!polling) {
                polling = true;
                executor.scheduleWithFixedDelay(this::drain, kPollPeriodMs, kPollPeriodMs, TimeUnit.MILLISECONDS);
            }
        } catch (Throwable error) {
            final String reason = "initComms/discovery: " + describe(error);
            Log.e(TAG, reason + "; retrying in " + kRetryDelayMs + " ms", error);
            closeAll();
            sink.onLink("UNAVAILABLE", reason);
            later(this::connect);
        }
    }

    private void onUnitChanged(ServiceUnitChangeEventType type, ServiceUnitDefinition definition) {
        if (!running || client == null) {
            return;
        }
        final String identity = identity(definition);
        Log.i(TAG, "service unit " + type + " " + identity);
        sink.onConfig("publisher_" + (type == ServiceUnitChangeEventType.Registered ? "registered" : "unregistered"),
                identity);
        if (type == ServiceUnitChangeEventType.Registered) {
            publisher = definition;
            subscribe();
        } else {
            publisher = null;
            closeSubscription();
            sink.onLink("WAITING", "publisher unregistered: " + identity);
        }
    }

    private void subscribe() {
        if (!running || client == null || publisher == null) {
            return;
        }
        closeSubscription();
        final String vm = publisher.serviceUnitIdentifier == null || publisher.serviceUnitIdentifier.fqin == null
                ? PUBLISHER_VM : publisher.serviceUnitIdentifier.fqin.sdvVmName;
        try {
            subscription = client.subscribeToPublicationByName(vm, PUBLISHER_PACKAGE, PUBLISHER_BUNDLE,
                    PUBLISHER_UNIT,
                    (sub, notification) -> post(() -> onNotification(sub, notification)),
                    /* fetchLastMessageOnSubscribe= */ true);
            final String slot = subscription.metadata == null ? "?" : subscription.metadata.messageSizeBytes
                    + " B x " + subscription.metadata.messageCount;
            Log.i(TAG, "subscribed topic=" + TOPIC_NAME + " message=" + MESSAGE_NAME + " vm=" + vm
                    + " publisher=" + PUBLISHER_PACKAGE + "." + PUBLISHER_BUNDLE + " slot=" + slot);
            sink.onConfig("subscribed", vm + ":" + PUBLISHER_PACKAGE + "." + PUBLISHER_BUNDLE + "/" + PUBLISHER_UNIT
                    + " slot " + slot);
            sink.onLink("SUBSCRIBED", vm + ":" + PUBLISHER_UNIT);
            drain();
        } catch (Throwable error) {
            final String reason = "subscribe " + vm + ":" + PUBLISHER_UNIT + ": " + describe(error);
            Log.e(TAG, reason + "; retrying in " + kRetryDelayMs + " ms", error);
            subscription = null;
            sink.onLink("UNAVAILABLE", reason);
            later(this::subscribe);
        }
    }

    private void onNotification(Subscription sub, SubscriptionNotificationType type) {
        if (sub != subscription) {
            return;
        }
        if (type == SubscriptionNotificationType.PublicationDestroyed) {
            // Unread messages can still be in the queue (G/SubscriptionNotificationType.java):
            // read them, then let go of the subscription.
            Log.w(TAG, "publication destroyed");
            drain();
            closeSubscription();
            sink.onLink("WAITING", "publication destroyed; waiting for the publisher to register again");
            return;
        }
        drain();
    }

    private void drain() {
        final Subscription current = subscription;
        if (!running || current == null) {
            return;
        }
        for (int batch = 0; batch < kMaxBatchesPerDrain; batch++) {
            final List<byte[]> slots;
            try {
                slots = current.readMessageList(kReadBatch);
            } catch (SdvGatewayRuntimeException error) {
                final long tMonoNs = System.nanoTime();
                final long tRealNs = System.currentTimeMillis() * 1_000_000L;
                if (error.getSdvGatewayStatusCode() == SdvGatewayStatusCode.DATA_LOSS) {
                    // Messages were skipped in the queue; the subscription itself is fine.
                    sink.onDataLoss("DATA_LOSS: " + error.getMessage(), tMonoNs, tRealNs);
                    continue;
                }
                final String reason = "read: " + describe(error);
                Log.w(TAG, reason, error);
                sink.onError(reason, tMonoNs, tRealNs);
                closeSubscription();
                sink.onLink("UNAVAILABLE", reason);
                later(this::subscribe);
                return;
            }
            if (slots == null || slots.isEmpty()) {
                return;
            }
            for (byte[] slot : slots) {
                // The receipt stamps are taken before the parse: they are the observer's
                // clocks at the read, not the app's later drawing.
                final long tMonoNs = System.nanoTime();
                final long tRealNs = System.currentTimeMillis() * 1_000_000L;
                final DrivingOperationalState message;
                try {
                    message = parseSlot(slot);
                } catch (IOException error) {
                    sink.onError(String.format(Locale.US, "parse: %s (%d bytes)", describe(error), slot.length),
                            tMonoNs, tRealNs);
                    continue;
                }
                sink.onState(MessageMapper.map(message), tMonoNs, tRealNs);
            }
            if (slots.size() < kReadBatch) {
                return;
            }
        }
    }

    /** Hop a gateway callback (a JNI-attached native thread) onto the executor. */
    private void post(Runnable task) {
        try {
            executor.execute(task);
        } catch (RejectedExecutionException stopped) {
            // stop() already ran; the callback has nothing left to do.
        }
    }

    /** Retry a step after kRetryDelayMs, unless the subscriber is stopping. */
    private void later(Runnable task) {
        if (!running) {
            return;
        }
        try {
            executor.schedule(task, kRetryDelayMs, TimeUnit.MILLISECONDS);
        } catch (RejectedExecutionException stopped) {
            // stop() already ran.
        }
    }

    private static String identity(ServiceUnitDefinition d) {
        final StringBuilder text = new StringBuilder(160);
        if (d.serviceUnitIdentifier != null && d.serviceUnitIdentifier.fqin != null) {
            text.append(d.serviceUnitIdentifier.fqin.sdvVmName).append(':')
                    .append(d.serviceUnitIdentifier.fqin.sdvPackageName).append('.')
                    .append(d.serviceUnitIdentifier.fqin.serviceBundleName).append('/')
                    .append(d.serviceUnitIdentifier.fqin.serviceInstanceName)
                    .append(" unit ").append(d.serviceUnitIdentifier.serviceUnitName);
        }
        if (d.unitType != null) {
            text.append(" type ").append(d.unitType.sdvPackageName).append('/')
                    .append(d.unitType.serviceBundleName).append('/').append(d.unitType.typeName);
        }
        if (d.publisherUnitMetadata != null) {
            text.append(" topic ").append(d.publisherUnitMetadata.topicName)
                    .append(" slot ").append(d.publisherUnitMetadata.messageSizeBytes)
                    .append(" B x ").append(d.publisherUnitMetadata.messageCount);
        }
        return text.toString();
    }

    private void closeSubscription() {
        final Subscription current = subscription;
        subscription = null;
        if (current == null) {
            return;
        }
        try {
            current.close();
        } catch (Throwable error) {
            Log.w(TAG, "subscription close: " + describe(error));
        }
    }

    /** Subscription, then discovery, then the client (the client's close() javadoc order). */
    private void closeAll() {
        closeSubscription();
        publisher = null;
        if (discovery != null) {
            try {
                discovery.close();
            } catch (Throwable error) {
                Log.w(TAG, "discovery close: " + describe(error));
            }
            discovery = null;
        }
        if (client != null && clientInitCalled) {
            try {
                // Also after a failed initComms: the JNI may already hold the client.
                client.close();
            } catch (Throwable error) {
                Log.w(TAG, "client close: " + describe(error));
            }
        }
        client = null;
        clientInitCalled = false;
    }
}
