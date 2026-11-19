// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Stand-in (tests/test_app_jvm.py): the signatures the app calls, with the platform's types and
// checked exceptions. Its only behavior is what the activity harness checks: the calls it records in
// de4sdv.teststubs.Calls. Never on the guest: the AOSP tree compiles the app against the real classes.
package android.app;
public class Activity extends android.content.Context {
    private final android.view.Window window = new android.view.Window() {};
    protected void onCreate(android.os.Bundle savedInstanceState) {}
    protected void onDestroy() {}
    public android.view.Window getWindow() { return window; }
    public void setContentView(android.view.View view) {}
    // The harness names the directory with -Dde4sdv.test.files; null otherwise, as before.
    @Override public java.io.File getFilesDir() {
        final String dir = System.getProperty("de4sdv.test.files");
        return dir == null ? null : new java.io.File(dir);
    }
}
