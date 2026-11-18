// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Compile-only stand-in (tests/test_app_jvm.py): the signatures the app calls, with the platform's
// types and checked exceptions; no behavior. Never on the guest: the AOSP tree compiles the app
// against the real classes.
package android.media;
public final class AudioAttributes {
    public static final int USAGE_ALARM = 4;
    public static final int CONTENT_TYPE_SONIFICATION = 4;
    public static class Builder {
        public Builder setUsage(int usage) { return this; }
        public Builder setContentType(int contentType) { return this; }
        public AudioAttributes build() { return null; }
    }
}
