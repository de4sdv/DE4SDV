// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The gateway subscriber of the IVI observer: one subscription to the typed topic
// the SOME/IP broker of the SDV Core VM publishes.
//
// It names the *typed* message, `de4sdv.driving.v1.DrivingOperationalState`, in
// the descriptor; the platform's subscriber does the protobuf parse and hands
// this process a DrivingOperationalState per slot. There is no carrier, no slot
// framing and no decode step: the broker's REFLECTION translation produced the
// message on the other side of the hypervisor, and the app reads its fields.
//
// The subject identity (org.de4sdv.drivingstate / DrivingStateObserver) is the
// pair the two ACL files grant (interop/acl/). The bundle name must start with an
// upper-case letter (PF-004 finding, INC-AEBS-010).
//
// The observer publishes nothing, offers nothing and calls nothing: the model's
// observer sends nothing to the driving system (REQ-DRIVING-018, -019).
package org.de4sdv.drivingstate;

import android.util.Log;

import com.google.protobuf.Parser;

import de4sdv.driving.v1.DrivingOperationalState;

import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

import google.sdv.gateway.client.SdvGatewayClient;
import google.sdv.gateway.client.Subscriber;
import google.sdv.gateway.client.SubscriberDescriptor;
import google.sdv.gateway.client.SubscriberOptions;

final class TypedStateSubscriber {

    private static final String TAG = StateRecord.COMPONENT;

    static final String SUBJECT_PACKAGE = "org.de4sdv.drivingstate";
    static final String SUBJECT_BUNDLE = "DrivingStateObserver";
    static final String TOPIC_NAME = "de4sdv-driving-operational-state";
    static final String MESSAGE_NAME = "de4sdv.driving.v1.DrivingOperationalState";

    private static final long kRetryDelaySeconds = 5L;
    private static final long kPollPeriodMs = 100L;
    private static final int kReadBatch = 16;

    interface Sink {
        void onState(MessageMapper.Mapped mapped, long tMonoNs, long tRealNs);

        void onError(String reason, long tMonoNs, long tRealNs);

        void onSubscriptionActive();

        void onUnavailable(String reason);
    }

    private final ScheduledExecutorService executor =
            Executors.newSingleThreadScheduledExecutor();
    private final Sink sink;
    private volatile SdvGatewayClient client;
    private volatile Subscriber<DrivingOperationalState> subscriber;
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
        executor.execute(() -> {
            try {
                if (subscriber != null) {
                    subscriber.dispose();
                }
            } catch (Throwable error) {
                Log.w(TAG, "subscriber dispose failed", error);
            } finally {
                subscriber = null;
                client = null;
            }
        });
    }

    private void connect() {
        if (!running) {
            return;
        }
        try {
            final SdvGatewayClient candidate = new SdvGatewayClient();
            candidate.initComms(SUBJECT_PACKAGE, SUBJECT_BUNDLE);
            client = candidate;
            Log.i(TAG, "lifecycle initComms package=" + SUBJECT_PACKAGE
                    + " bundle=" + SUBJECT_BUNDLE);

            final Parser<DrivingOperationalState> parser = DrivingOperationalState.parser();
            final SubscriberDescriptor<DrivingOperationalState> descriptor =
                    new SubscriberDescriptor.Builder<DrivingOperationalState>()
                            .setTopicName(TOPIC_NAME)
                            .setMessageName(MESSAGE_NAME)
                            .setParser(parser)
                            .build();

            final Subscriber<DrivingOperationalState> newSubscriber =
                    Subscriber.create(candidate, descriptor, new SubscriberOptions.Builder().build());
            subscriber = newSubscriber;
            newSubscriber.registerOnMessagesAvailableListener(executor, this::drain);

            Log.i(TAG, "subscribed topic=" + TOPIC_NAME + " message=" + MESSAGE_NAME);
            sink.onSubscriptionActive();
            executor.scheduleWithFixedDelay(this::drain, 0L, kPollPeriodMs, TimeUnit.MILLISECONDS);
        } catch (Throwable error) {
            Log.e(TAG, "gateway subscription failed, retrying in " + kRetryDelaySeconds + " s", error);
            closeQuietly();
            sink.onUnavailable(error.getClass().getSimpleName() + ": " + error.getMessage());
            if (running) {
                executor.schedule(this::connect, kRetryDelaySeconds, TimeUnit.SECONDS);
            }
        }
    }

    private void drain() {
        final Subscriber<DrivingOperationalState> current = subscriber;
        if (!running || current == null) {
            return;
        }
        try {
            final List<DrivingOperationalState> messages = current.readNextMessages(kReadBatch);
            for (DrivingOperationalState message : messages) {
                // The receipt stamps are taken before the copy: the record's
                // clocks are the observer's, not the app's later drawing.
                final long tMonoNs = System.nanoTime();
                final long tRealNs = System.currentTimeMillis() * 1_000_000L;
                sink.onState(MessageMapper.map(message), tMonoNs, tRealNs);
            }
        } catch (Throwable error) {
            final long tMonoNs = System.nanoTime();
            final long tRealNs = System.currentTimeMillis() * 1_000_000L;
            Log.w(TAG, "read failed", error);
            sink.onError("read: " + error.getClass().getSimpleName() + ": " + error.getMessage(),
                    tMonoNs, tRealNs);
            closeQuietly();
            if (running) {
                executor.schedule(this::connect, kRetryDelaySeconds, TimeUnit.SECONDS);
            }
        }
    }

    private void closeQuietly() {
        try {
            if (subscriber != null) {
                subscriber.dispose();
            }
        } catch (Throwable error) {
            Log.w(TAG, "dispose failed", error);
        } finally {
            subscriber = null;
            client = null;
        }
    }
}
