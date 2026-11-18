// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Compile-only stand-in (tests/test_app_jvm.py): the signatures the app calls, with the platform's
// types and checked exceptions; no behavior. Never on the guest: the AOSP tree compiles the app
// against the real classes.
package android.app;
public class Activity extends android.content.Context {
    protected void onCreate(android.os.Bundle savedInstanceState) {}
    protected void onDestroy() {}
    public android.view.Window getWindow() { return null; }
    public void setContentView(android.view.View view) {}
    @Override public java.io.File getFilesDir() { return null; }
}
