// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Compile-only stand-in (tests/test_app_jvm.py): the signatures the app calls, with the platform's
// types and checked exceptions; no behavior. Never on the guest: the AOSP tree compiles the app
// against the real classes.
package android.graphics;
public class Paint {
    public static final int ANTI_ALIAS_FLAG = 1;
    public enum Align { LEFT, CENTER, RIGHT }
    public Paint(int flags) {}
    public void setColor(int color) {}
    public void setTextAlign(Align align) {}
    public void setFakeBoldText(boolean fakeBoldText) {}
    public void setTextSize(float textSize) {}
}
