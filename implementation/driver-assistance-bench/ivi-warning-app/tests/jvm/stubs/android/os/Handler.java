// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Stand-in (tests/test_app_jvm.py): the signatures the app calls, with the platform's types and
// checked exceptions. Its only behavior is what the activity harness checks: the calls it records in
// de4sdv.teststubs.Calls. Never on the guest: the AOSP tree compiles the app against the real classes.
package android.os;
public class Handler {
    private final Looper looper;
    public Handler(Looper looper) { this.looper = looper; }
    private String queue() { return looper == Looper.getMainLooper() ? "main" : "other"; }
    public final boolean post(Runnable r) { de4sdv.teststubs.Calls.add(queue() + ":post"); return true; }
    public final boolean postDelayed(Runnable r, long delayMillis) { de4sdv.teststubs.Calls.add(queue() + ":postDelayed"); return true; }
    public final boolean postAtFrontOfQueue(Runnable r) { de4sdv.teststubs.Calls.add(queue() + ":front"); return true; }
    public final void removeCallbacksAndMessages(Object token) {}
}
