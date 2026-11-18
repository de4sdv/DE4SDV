// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Compile-only stand-in (tests/test_app_jvm.py): the signatures the app calls, with the platform's
// types and checked exceptions; no behavior. Never on the guest: the AOSP tree compiles the app
// against the real classes.
package android.media;
public final class AudioFormat {
    public static final int ENCODING_PCM_16BIT = 2;
    public static final int CHANNEL_OUT_MONO = 4;
    public static class Builder {
        public Builder setEncoding(int encoding) { return this; }
        public Builder setSampleRate(int sampleRate) { return this; }
        public Builder setChannelMask(int channelMask) { return this; }
        public AudioFormat build() { return null; }
    }
}
