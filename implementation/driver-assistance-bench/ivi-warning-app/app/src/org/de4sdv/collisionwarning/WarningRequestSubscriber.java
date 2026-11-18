// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The gateway subscriber of the warning presentation: the port warningRequestIn of
// CollisionWarningPresentationApplication, at the end of the connection
// warningRequestThroughSDVGateway (driver_assistance_physical_software_realization.sysml,
// MAP-DRIVING-DA-WARNING-REQUEST, hop 8 of ../../ivi-warning/README.md).
//
// One by-name subscription to the one service unit that the SOME/IP broker of the SDV Core VM
// publishes for the warning request, as the INC-DRIVING-001 observer subscribes to its three
// (closed-loop-driving-bench/ivi-observer/app/.../TypedStateSubscriber.java, the pattern copied
// here): discovery by (VM, publisher package, publisher bundle, unit name), then
// subscribeToPublicationByName. The ids are those of ../../interfaces/service_ids.json:
//   unit      de4sdv-driving-warning-request            (icd.data_tunnel.service_unit)
//   message   de4sdv.driving.v1.CollisionWarningRequest (icd.data_tunnel.message)
//   publisher com.android.sdv.someip / SomeIpBroker     (lane_choices.sdv_core_broker)
//   subject   org.de4sdv.collisionwarning / CollisionWarningPresentation (lane_choices.ivi_subscriber)
//
// The message arrives typed: the broker translated the SOME/IP struct in REFLECTION mode on the
// SDV Core VM; nothing here decodes SOME/IP bytes. A Data Tunnel slot is the serialized message
// with a varint length prefix, zero-padded to the slot size (parseDelimitedFrom, as the client's
// own Subscriber and the observer parse it).
//
// The receipt stamps are taken at the read, before the parse: that read is "the receipt by the
// warning presentation" where the model's 0.1 s path share ends and its 0.1 s presentation share
// begins. The poll period bounds how late a read can follow a message that arrives without a
// notification.
//
// Threading: one executor. Gateway callbacks arrive on JNI-attached native threads and are hopped
// onto the executor at once. The JNI holds one client per process: after any failure past
// initComms the client is closed before the next attempt. The presentation publishes nothing,
// offers nothing and calls nothing on the driving side (it sends nothing to the candidate).
package org.de4sdv.collisionwarning;

import android.util.Log;

import com.google.protobuf.Parser;

import de4sdv.driving.v1.De4SdvDrivingCollisionWarningRequest.CollisionWarningRequest;

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

final class WarningRequestSubscriber {

    private static final String TAG = WarningRecord.TAG;

    static final String SUBJECT_PACKAGE = "org.de4sdv.collisionwarning";
    static final String SUBJECT_BUNDLE = "CollisionWarningPresentation";
    static final String MESSAGE_NAME = "de4sdv.driving.v1.CollisionWarningRequest";
    // An empty VM name matches the unit on any VM; the subscribe call uses the VM its discovery reports.
    static final String PUBLISHER_VM = "";
    static final String PUBLISHER_PACKAGE = "com.android.sdv.someip";
    static final String PUBLISHER_BUNDLE = "SomeIpBroker";
    static final String UNIT = "de4sdv-driving-warning-request";

    static final String LINK_WAITING = "WAITING";
    static final String LINK_SUBSCRIBED = "SUBSCRIBED";
    static final String LINK_UNAVAILABLE = "UNAVAILABLE";

    static final Parser<CollisionWarningRequest> PARSER = CollisionWarningRequest.parser();

    static final long RETRY_DELAY_MS = 5000L;
    static final long POLL_PERIOD_MS = 10L;
    private static final int READ_BATCH = 16;
    private static final int MAX_BATCHES_PER_DRAIN = 8;

    // PF-004 conventions: bundle names start [A-Z]; service-unit names are [a-z0-9-], starting [a-z].
    private static final Pattern BUNDLE_NAME = Pattern.compile("[A-Z][A-Za-z0-9]*");
    private static final Pattern UNIT_NAME = Pattern.compile("[a-z][a-z0-9-]*");

    interface Sink {
        /** One parsed message; the stamps are the IVI VM's, taken at the read. */
        void onMessage(long requested, long issueTimeSimMs, long tMonoNs, long tRealNs);

        /** A failure that does not end the subscription (a slot that does not parse, a read error). */
        void onError(String reason, long tMonoNs, long tRealNs);

        /** The gateway reported DATA_LOSS: messages were skipped in the queue. */
        void onDataLoss(String reason, long tMonoNs, long tRealNs);

        /** WAITING, SUBSCRIBED or UNAVAILABLE, with a detail. */
        void onLink(String state, String detail);

        /** A lifecycle or configuration fact for the record. */
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

    WarningRequestSubscriber(Sink sink) {
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

    /** Run a task on the subscriber's thread (the reducer lives there). */
    void post(Runnable task) {
        try {
            executor.execute(task);
        } catch (RejectedExecutionException stopped) {
            // stop() already ran.
        }
    }

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
        if (!UNIT_NAME.matcher(UNIT).matches()) {
            return "service unit must be [a-z0-9-] starting [a-z]: " + UNIT;
        }
        return "";
    }

    /** One Data Tunnel slot to the typed message (varint-delimited, zero-padded). */
    static CollisionWarningRequest parseSlot(byte[] slot) throws IOException {
        final CollisionWarningRequest message = PARSER.parseDelimitedFrom(new ByteArrayInputStream(slot));
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
            sink.onConfig("initComms", SUBJECT_PACKAGE + "." + SUBJECT_BUNDLE);
            final UnitNameDiscoveryArgs name = new UnitNameDiscoveryArgs(
                    PUBLISHER_VM, PUBLISHER_PACKAGE, PUBLISHER_BUNDLE, UNIT);
            discovery = candidate.addListenerForServiceUnitChangeByName(name,
                    (type, definition) -> post(() -> onUnitChanged(type, definition)));
            sink.onConfig("discovery", "vm='" + PUBLISHER_VM + "' publisher=" + PUBLISHER_PACKAGE + "."
                    + PUBLISHER_BUNDLE + " unit=" + UNIT);
            sink.onLink(LINK_WAITING, "discovery started; waiting for the broker's unit " + UNIT);
            if (!polling) {
                polling = true;
                executor.scheduleWithFixedDelay(this::drain, POLL_PERIOD_MS, POLL_PERIOD_MS, TimeUnit.MILLISECONDS);
            }
        } catch (Throwable error) {
            final String reason = "initComms/discovery: " + describe(error);
            Log.e(TAG, reason + "; retrying in " + RETRY_DELAY_MS + " ms", error);
            closeAll();
            sink.onLink(LINK_UNAVAILABLE, reason);
            later(this::connect);
        }
    }

    private void onUnitChanged(ServiceUnitChangeEventType type, ServiceUnitDefinition definition) {
        if (!running || client == null) {
            return;
        }
        final String identity = identity(definition);
        sink.onConfig(type == ServiceUnitChangeEventType.Registered ? "publisher_registered" : "publisher_unregistered",
                identity);
        if (type == ServiceUnitChangeEventType.Registered) {
            publisher = definition;
            subscribe();
        } else {
            publisher = null;
            closeSubscription();
            sink.onLink(LINK_WAITING, "publisher unregistered: " + identity);
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
            // fetchLastMessageOnSubscribe: the last message again on every (re)subscription; the
            // reducer refuses it as stale when its issue time is not newer.
            subscription = client.subscribeToPublicationByName(vm, PUBLISHER_PACKAGE, PUBLISHER_BUNDLE, UNIT,
                    (sub, notification) -> post(() -> onNotification(sub, notification)),
                    /* fetchLastMessageOnSubscribe= */ true);
            final String slot = subscription.metadata == null ? "?"
                    : subscription.metadata.messageSizeBytes + " B x " + subscription.metadata.messageCount;
            sink.onConfig("subscribed", vm + ":" + PUBLISHER_PACKAGE + "." + PUBLISHER_BUNDLE + "/" + UNIT
                    + " message " + MESSAGE_NAME + " slot " + slot);
            sink.onLink(LINK_SUBSCRIBED, vm);
            drain();
        } catch (Throwable error) {
            final String reason = "subscribe " + vm + ":" + UNIT + ": " + describe(error);
            Log.e(TAG, reason + "; retrying in " + RETRY_DELAY_MS + " ms", error);
            subscription = null;
            sink.onLink(LINK_UNAVAILABLE, reason);
            later(this::subscribe);
        }
    }

    private void onNotification(Subscription sub, SubscriptionNotificationType type) {
        if (sub != subscription) {
            return;
        }
        if (type == SubscriptionNotificationType.PublicationDestroyed) {
            // Unread messages can still be in the queue: read them, then let go.
            drain();
            closeSubscription();
            sink.onLink(LINK_WAITING, "publication destroyed; waiting for the publisher to register again");
            return;
        }
        drain();
    }

    private void drain() {
        final Subscription current = subscription;
        if (!running || current == null) {
            return;
        }
        for (int batch = 0; batch < MAX_BATCHES_PER_DRAIN; batch++) {
            final List<byte[]> slots;
            try {
                slots = current.readMessageList(READ_BATCH);
            } catch (SdvGatewayRuntimeException error) {
                final long tMonoNs = System.nanoTime();
                final long tRealNs = System.currentTimeMillis() * 1_000_000L;
                if (error.getSdvGatewayStatusCode() == SdvGatewayStatusCode.DATA_LOSS) {
                    sink.onDataLoss("DATA_LOSS " + UNIT + ": " + error.getMessage(), tMonoNs, tRealNs);
                    continue;
                }
                final String reason = "read " + UNIT + ": " + describe(error);
                sink.onError(reason, tMonoNs, tRealNs);
                closeSubscription();
                sink.onLink(LINK_UNAVAILABLE, reason);
                later(this::subscribe);
                return;
            }
            if (slots == null || slots.isEmpty()) {
                return;
            }
            for (byte[] slot : slots) {
                final long tMonoNs = System.nanoTime();
                final long tRealNs = System.currentTimeMillis() * 1_000_000L;
                final CollisionWarningRequest message;
                try {
                    message = parseSlot(slot);
                } catch (IOException error) {
                    sink.onError(String.format(Locale.US, "parse: %s (%d bytes)", describe(error), slot.length),
                            tMonoNs, tRealNs);
                    continue;
                }
                // protobuf's uint32 is a signed Java int.
                sink.onMessage(Integer.toUnsignedLong(message.getRequested()),
                        Integer.toUnsignedLong(message.getIssueTimeSimMs()), tMonoNs, tRealNs);
            }
            if (slots.size() < READ_BATCH) {
                return;
            }
        }
    }

    private void later(Runnable task) {
        if (!running) {
            return;
        }
        try {
            executor.schedule(task, RETRY_DELAY_MS, TimeUnit.MILLISECONDS);
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

    /** The subscription, then the discovery, then the client. */
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
                client.close();
            } catch (Throwable error) {
                Log.w(TAG, "client close: " + describe(error));
            }
        }
        client = null;
        clientInitCalled = false;
    }
}
