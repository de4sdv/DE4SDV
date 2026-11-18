// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Compile-only stand-in (tests/test_app_jvm.py): the signatures the app calls, with the platform's
// types and checked exceptions; no behavior. Never on the guest: the AOSP tree compiles the app
// against the real classes.
package android.os;
public class HandlerThread extends Thread {
    public HandlerThread(String name) {}
    public Looper getLooper() { return null; }
    public boolean quitSafely() { return true; }
}
