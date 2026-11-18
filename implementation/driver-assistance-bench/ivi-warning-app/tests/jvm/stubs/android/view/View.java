// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Stand-in (tests/test_app_jvm.py): the signatures the app calls, with the platform's types and
// checked exceptions. Its only behavior is what the activity harness checks: the calls it records in
// de4sdv.teststubs.Calls. Never on the guest: the AOSP tree compiles the app against the real classes.
package android.view;
public class View {
    private final ViewTreeObserver observer = new ViewTreeObserver();
    public View(android.content.Context context) {}
    public void invalidate() {}
    protected void onDraw(android.graphics.Canvas canvas) {}
    public final int getWidth() { return 0; }
    public final int getHeight() { return 0; }
    public ViewTreeObserver getViewTreeObserver() { return observer; }
}
