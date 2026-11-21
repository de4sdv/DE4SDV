// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Stand-in (tests/test_app_jvm.py): the signatures the app calls, with the platform's types and
// checked exceptions. Its only behavior is what the activity harness checks: the calls it records in
// de4sdv.teststubs.Calls. Never on the guest: the AOSP tree compiles the app against the real classes.
package android.os;
public class HandlerThread extends Thread {
    private final Looper looper = new Looper();
    public HandlerThread(String name) { super(name); }
    public Looper getLooper() { return looper; }
    public boolean quitSafely() { return true; }
}
