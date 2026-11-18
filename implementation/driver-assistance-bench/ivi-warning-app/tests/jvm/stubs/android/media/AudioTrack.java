// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Stand-in (tests/test_app_jvm.py): the signatures the app calls, with the platform's types and
// checked exceptions. Its only behavior is what the activity harness checks: the calls it records in
// de4sdv.teststubs.Calls. Never on the guest: the AOSP tree compiles the app against the real classes.
package android.media;
public class AudioTrack {
    public static final int MODE_STATIC = 0;
    public static class Builder {
        public Builder setAudioAttributes(AudioAttributes attributes) { return this; }
        public Builder setAudioFormat(AudioFormat format) { return this; }
        public Builder setTransferMode(int mode) { return this; }
        public Builder setBufferSizeInBytes(int bufferSizeInBytes) { return this; }
        public AudioTrack build() throws UnsupportedOperationException { return new AudioTrack(); }
    }
    public int write(short[] audioData, int offsetInShorts, int sizeInShorts) { return 0; }
    public int setLoopPoints(int startInFrames, int endInFrames, int loopCount) { return 0; }
    public int getState() { return 0; }
    public void play() throws IllegalStateException { de4sdv.teststubs.Calls.add("sound:play"); }
    public void pause() throws IllegalStateException {}
    public int reloadStaticData() { return 0; }
    public int getPlaybackHeadPosition() { return 0; }
    public boolean getTimestamp(AudioTimestamp timestamp) { return false; }
    public void release() {}
}
