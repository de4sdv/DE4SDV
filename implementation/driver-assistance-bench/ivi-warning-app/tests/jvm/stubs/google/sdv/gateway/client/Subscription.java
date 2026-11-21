// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Compile-only stand-in (tests/test_app_jvm.py): the signatures the app calls, with the platform's
// types and checked exceptions; no behavior. Never on the guest: the AOSP tree compiles the app
// against the real classes.
package google.sdv.gateway.client;
public class Subscription implements AutoCloseable {
    public static final class Metadata { public long messageSizeBytes; public long messageCount; }
    public Metadata metadata;
    public java.util.List<byte[]> readMessageList(int maxMessages) { return null; }
    @Override public void close() {}
}
