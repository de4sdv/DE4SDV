// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The gateway subscriber of the IVI observer: three subscriptions, one per
// service unit that the SOME/IP broker of the SDV Core VM publishes, merged into
// the one stream the app's state and record take.
//
// The broker registers one service unit per SOME/IP event
// (interop/de4sdv_driving_operational_state.vsidl: sdv_service_unit_parameterization
// keys 0, 1, 2 for the events 0x8001 plan, 0x8002 vehicle state, 0x8003 health),
// all three of the one message type: the publication is SINGLE_PUB, one publisher
// per channel. Each unit carries one kind, so the per-kind sequences of the merged
// stream are per-unit sequences; nothing relies on an order across kinds.
//
// It subscribes BY NAME to each unit, the way the two existing subscribers of a
// broker publication on this tree do it:
//   * the proven native relay of the AEBS frame bench subscribed to
//     instance1:com.android.sdv.someip.SomeIpBroker, unit de4sdv-score-aebs-signal-frame
//     (samples/ivi_frame_relay, options.hpp);
//   * the platform's SdvCarMonitorTestApp subscribes to the broker's FooMessage
//     unit with addListenerForServiceUnitChangeByName + subscribeToPublicationByName,
//     and holds two such discoveries and subscriptions on one client.
// A by-name subscription addresses a unit by (VM, publisher package, publisher
// bundle, service unit name): the broker's own bundle com.android.sdv.someip /
// SomeIpBroker and the unit names of the mapping. The message name is not part of
// the address; it is this app's parser and the ACLs' `message`.
// The client's Subscriber.create() is NOT used: it discovers by unit type and
// matches the publisher's topic name, which a broker unit without a topic
// parameter does not set; and it logs and drops subscribe and parse failures.
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
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
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
    // The typed message of all three units (ICD section 3, MAP-DRIVING-OPERATIONAL-STATE).
    static final String MESSAGE_NAME = "de4sdv.driving.v1.DrivingOperationalState";
    // The publisher: the SOME/IP broker bundle of the SDV Core VM. An empty VM name
    // matches the units on any VM; each subscribe call then uses the VM name its
    // discovery event reports.
    static final String PUBLISHER_VM = "";
    static final String PUBLISHER_PACKAGE = "com.android.sdv.someip";
    static final String PUBLISHER_BUNDLE = "SomeIpBroker";
    // The three service units (the mapping's sdv_service_unit_parameterization values,
    // keys 0, 1, 2) and the kind each one carries.
    static final String UNIT_PLAN = "de4sdv-driving-operational-state-plan";
    static final String UNIT_VEHICLE_STATE = "de4sdv-driving-operational-state-vehicle-state";
    static final String UNIT_HEALTH = "de4sdv-driving-operational-state-health";
    static final List<String> PUBLISHER_UNITS =
            Collections.unmodifiableList(Arrays.asList(UNIT_PLAN, UNIT_VEHICLE_STATE, UNIT_HEALTH));

    static final String LINK_WAITING = "WAITING";
    static final String LINK_SUBSCRIBED = "SUBSCRIBED";
    static final String LINK_UNAVAILABLE = "UNAVAILABLE";

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

        /** Link state of the three units together: WAITING, SUBSCRIBED, UNAVAILABLE. */
        void onLink(String state, String detail);

        /** A lifecycle/config fact for the record (key, value). */
        void onConfig(String key, String value);
    }

    /** One service unit: its discovery, its subscription and its link (executor thread only). */
    private static final class Unit {
        final String name;
        final int expectedKind;
        AutoCloseable discovery;
        Subscription subscription;
        ServiceUnitDefinition publisher;
        String link = LINK_WAITING;
        String detail = "";

        Unit(String name) {
            this.name = name;
            this.expectedKind = expectedKind(name);
        }
    }

    private final ScheduledExecutorService executor = Executors.newSingleThreadScheduledExecutor();
    private final Sink sink;
    private final List<Unit> units = new ArrayList<>();

    // Owned by the executor thread.
    private SdvGatewayClient client;
    private boolean clientInitCalled;
    private boolean polling;
    private volatile boolean running;

    TypedStateSubscriber(Sink sink) {
        this.sink = sink;
        for (String name : PUBLISHER_UNITS) {
            units.add(new Unit(name));
        }
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
        for (String unit : PUBLISHER_UNITS) {
            if (!UNIT_NAME.matcher(unit).matches()) {
                return "service unit must be [a-z0-9-] starting [a-z]: " + unit;
            }
        }
        return "";
    }

    /** The kind a unit carries (ICD section 3: 1 PLAN, 2 VEHICLE_STATE, 3 HEALTH); 0 if unknown. */
    static int expectedKind(String unit) {
        if (UNIT_PLAN.equals(unit)) {
            return 1;
        }
        if (UNIT_VEHICLE_STATE.equals(unit)) {
            return 2;
        }
        if (UNIT_HEALTH.equals(unit)) {
            return 3;
        }
        return 0;
    }

    /**
     * The one link state of the units: UNAVAILABLE when any unit failed, SUBSCRIBED only when
     * every unit is subscribed, WAITING otherwise. A partly subscribed set is not SUBSCRIBED:
     * the screen shows which unit is missing.
     */
    static String aggregateLink(List<String> states) {
        boolean all = !states.isEmpty();
        for (String state : states) {
            if (LINK_UNAVAILABLE.equals(state)) {
                return LINK_UNAVAILABLE;
            }
            if (!LINK_SUBSCRIBED.equals(state)) {
                all = false;
            }
        }
        return all ? LINK_SUBSCRIBED : LINK_WAITING;
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
            sink.onLink(LINK_UNAVAILABLE, naming);
            return;
        }
        final SdvGatewayClient candidate = new SdvGatewayClient();
        try {
            clientInitCalled = true;
            client = candidate;
            candidate.initComms(SUBJECT_PACKAGE, SUBJECT_BUNDLE);
            Log.i(TAG, "lifecycle initComms package=" + SUBJECT_PACKAGE + " bundle=" + SUBJECT_BUNDLE);
            sink.onConfig("initComms", SUBJECT_PACKAGE + "." + SUBJECT_BUNDLE);

            for (Unit unit : units) {
                unit.link = LINK_WAITING;
                unit.detail = "";
                final UnitNameDiscoveryArgs name = new UnitNameDiscoveryArgs(
                        PUBLISHER_VM, PUBLISHER_PACKAGE, PUBLISHER_BUNDLE, unit.name);
                unit.discovery = candidate.addListenerForServiceUnitChangeByName(name,
                        (type, definition) -> post(() -> onUnitChanged(unit, type, definition)));
                Log.i(TAG, "discovery by name vm='" + PUBLISHER_VM + "' package=" + PUBLISHER_PACKAGE
                        + " bundle=" + PUBLISHER_BUNDLE + " unit=" + unit.name);
            }
            reportLink();
            if (!polling) {
                polling = true;
                executor.scheduleWithFixedDelay(this::drainAll, kPollPeriodMs, kPollPeriodMs, TimeUnit.MILLISECONDS);
            }
        } catch (Throwable error) {
            final String reason = "initComms/discovery: " + describe(error);
            Log.e(TAG, reason + "; retrying in " + kRetryDelayMs + " ms", error);
            closeAll();
            sink.onLink(LINK_UNAVAILABLE, reason);
            later(this::connect);
        }
    }

    private void onUnitChanged(Unit unit, ServiceUnitChangeEventType type, ServiceUnitDefinition definition) {
        if (!running || client == null) {
            return;
        }
        final String identity = identity(definition);
        Log.i(TAG, "service unit " + type + " " + identity);
        sink.onConfig("publisher_" + (type == ServiceUnitChangeEventType.Registered ? "registered" : "unregistered"),
                identity);
        if (type == ServiceUnitChangeEventType.Registered) {
            unit.publisher = definition;
            subscribe(unit);
        } else {
            unit.publisher = null;
            closeSubscription(unit);
            setLink(unit, LINK_WAITING, "publisher unregistered: " + identity);
        }
    }

    private void subscribe(Unit unit) {
        if (!running || client == null || unit.publisher == null) {
            return;
        }
        closeSubscription(unit);
        final String vm = unit.publisher.serviceUnitIdentifier == null
                || unit.publisher.serviceUnitIdentifier.fqin == null
                ? PUBLISHER_VM : unit.publisher.serviceUnitIdentifier.fqin.sdvVmName;
        try {
            unit.subscription = client.subscribeToPublicationByName(vm, PUBLISHER_PACKAGE, PUBLISHER_BUNDLE,
                    unit.name,
                    (sub, notification) -> post(() -> onNotification(unit, sub, notification)),
                    /* fetchLastMessageOnSubscribe= */ true);
            final String slot = unit.subscription.metadata == null ? "?"
                    : unit.subscription.metadata.messageSizeBytes + " B x " + unit.subscription.metadata.messageCount;
            Log.i(TAG, "subscribed unit=" + unit.name + " message=" + MESSAGE_NAME + " vm=" + vm
                    + " publisher=" + PUBLISHER_PACKAGE + "." + PUBLISHER_BUNDLE + " slot=" + slot);
            sink.onConfig("subscribed", vm + ":" + PUBLISHER_PACKAGE + "." + PUBLISHER_BUNDLE + "/" + unit.name
                    + " slot " + slot);
            setLink(unit, LINK_SUBSCRIBED, vm);
            drain(unit);
        } catch (Throwable error) {
            final String reason = "subscribe " + vm + ":" + unit.name + ": " + describe(error);
            Log.e(TAG, reason + "; retrying in " + kRetryDelayMs + " ms", error);
            unit.subscription = null;
            setLink(unit, LINK_UNAVAILABLE, reason);
            later(() -> subscribe(unit));
        }
    }

    private void onNotification(Unit unit, Subscription sub, SubscriptionNotificationType type) {
        if (sub != unit.subscription) {
            return;
        }
        if (type == SubscriptionNotificationType.PublicationDestroyed) {
            // Unread messages can still be in the queue (G/SubscriptionNotificationType.java):
            // read them, then let go of the subscription.
            Log.w(TAG, "publication destroyed: " + unit.name);
            drain(unit);
            closeSubscription(unit);
            setLink(unit, LINK_WAITING, "publication destroyed; waiting for the publisher to register again");
            return;
        }
        drain(unit);
    }

    private void drainAll() {
        for (Unit unit : units) {
            drain(unit);
        }
    }

    private void drain(Unit unit) {
        final Subscription current = unit.subscription;
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
                    sink.onDataLoss("DATA_LOSS " + unit.name + ": " + error.getMessage(), tMonoNs, tRealNs);
                    continue;
                }
                final String reason = "read " + unit.name + ": " + describe(error);
                Log.w(TAG, reason, error);
                sink.onError(reason, tMonoNs, tRealNs);
                closeSubscription(unit);
                setLink(unit, LINK_UNAVAILABLE, reason);
                later(() -> subscribe(unit));
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
                    sink.onError(String.format(Locale.US, "parse: %s (%d bytes, unit %s)", describe(error),
                            slot.length, unit.name), tMonoNs, tRealNs);
                    continue;
                }
                if (message.getKind() != unit.expectedKind) {
                    // The receipt is kept (its values are the published ones); a crossed unit key
                    // in the mapping is reported, not hidden by the merge.
                    sink.onError(String.format(Locale.US, "unit %s carried kind %d, expected %d", unit.name,
                            message.getKind(), unit.expectedKind), tMonoNs, tRealNs);
                }
                sink.onState(MessageMapper.map(message), tMonoNs, tRealNs);
            }
            if (slots.size() < kReadBatch) {
                return;
            }
        }
    }

    private void setLink(Unit unit, String state, String detail) {
        unit.link = state;
        unit.detail = detail == null ? "" : detail;
        reportLink();
    }

    /** The units' links as one state and one line: which units are subscribed, and why not the others. */
    private void reportLink() {
        final List<String> states = new ArrayList<>();
        int subscribed = 0;
        String vm = "";
        for (Unit unit : units) {
            states.add(unit.link);
            if (LINK_SUBSCRIBED.equals(unit.link)) {
                subscribed++;
                vm = unit.detail;
            }
        }
        final String state = aggregateLink(states);
        final StringBuilder detail = new StringBuilder(160);
        detail.append(subscribed).append(" of ").append(units.size()).append(" units subscribed");
        if (LINK_SUBSCRIBED.equals(state)) {
            detail.append(" on ").append(vm.isEmpty() ? "?" : vm);
        }
        for (Unit unit : units) {
            if (!LINK_SUBSCRIBED.equals(unit.link)) {
                detail.append("; ").append(unit.name).append(' ').append(unit.link);
                if (!unit.detail.isEmpty()) {
                    detail.append(": ").append(unit.detail);
                }
            }
        }
        sink.onLink(state, detail.toString());
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

    private void closeSubscription(Unit unit) {
        final Subscription current = unit.subscription;
        unit.subscription = null;
        if (current == null) {
            return;
        }
        try {
            current.close();
        } catch (Throwable error) {
            Log.w(TAG, "subscription close " + unit.name + ": " + describe(error));
        }
    }

    /** Subscriptions, then discoveries, then the client (the client's close() javadoc order). */
    private void closeAll() {
        for (Unit unit : units) {
            closeSubscription(unit);
            unit.publisher = null;
            unit.link = LINK_WAITING;
            unit.detail = "";
        }
        for (Unit unit : units) {
            if (unit.discovery != null) {
                try {
                    unit.discovery.close();
                } catch (Throwable error) {
                    Log.w(TAG, "discovery close " + unit.name + ": " + describe(error));
                }
                unit.discovery = null;
            }
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
