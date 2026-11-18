// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Compile-only stand-in (tests/test_app_jvm.py): the signatures the app calls, with the platform's
// types and checked exceptions; no behavior. Never on the guest: the AOSP tree compiles the app
// against the real classes.
package google.sdv.gateway.client;
public class SdvGatewayClient implements AutoCloseable {
    public interface ServiceUnitChangeListener { void onChange(ServiceUnitChangeEventType type, ServiceUnitDefinition definition); }
    public interface SubscriptionListener { void onNotification(Subscription subscription, SubscriptionNotificationType type); }
    public void initComms(String packageName, String bundleName) {}
    public AutoCloseable addListenerForServiceUnitChangeByName(UnitNameDiscoveryArgs args, ServiceUnitChangeListener listener) { return null; }
    public Subscription subscribeToPublicationByName(String vm, String packageName, String bundleName, String unitName,
            SubscriptionListener listener, boolean fetchLastMessageOnSubscribe) { return null; }
    @Override public void close() {}
}
