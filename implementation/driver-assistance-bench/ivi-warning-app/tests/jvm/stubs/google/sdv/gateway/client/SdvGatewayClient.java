// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Stand-in (tests/test_app_jvm.py): the signatures the app calls, with the platform's types and
// checked exceptions. Its only behavior is what the activity harness checks: the calls it records in
// de4sdv.teststubs.Calls. Never on the guest: the AOSP tree compiles the app against the real classes.
// Discovery answers at once with a registered unit, so the subscriber goes on to subscribe.
package google.sdv.gateway.client;
public class SdvGatewayClient implements AutoCloseable {
    public interface ServiceUnitChangeListener { void onChange(ServiceUnitChangeEventType type, ServiceUnitDefinition definition); }
    public interface SubscriptionListener { void onNotification(Subscription subscription, SubscriptionNotificationType type); }
    public void initComms(String packageName, String bundleName) {}
    public AutoCloseable addListenerForServiceUnitChangeByName(UnitNameDiscoveryArgs args, ServiceUnitChangeListener listener) {
        listener.onChange(ServiceUnitChangeEventType.Registered, new ServiceUnitDefinition());
        return () -> {};
    }
    public Subscription subscribeToPublicationByName(String vm, String packageName, String bundleName, String unitName,
            SubscriptionListener listener, boolean fetchLastMessageOnSubscribe) {
        de4sdv.teststubs.Calls.add("gateway:subscribe unit=" + unitName + " fetchLastMessageOnSubscribe=" + fetchLastMessageOnSubscribe);
        return new Subscription();
    }
    @Override public void close() {}
}
