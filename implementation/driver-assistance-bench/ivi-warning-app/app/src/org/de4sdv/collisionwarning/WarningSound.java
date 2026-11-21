// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The warning sound: a looped beep (WarningTone) in a static AudioTrack, created when the app
// starts so that a request only calls play(). The model asks the presentation to start a warning
// sound when a request starts and to log its start (CollisionWarningPresentationApplication); the
// start of the sound on the guest is unmeasured in the model, and the split of the 0.2 s is
// revisited when it is measured.
//
// What is logged per request, each once (PresentationTimeline):
//   sound_play_called  the IVI monotonic time just before AudioTrack.play();
//   sound_head_moved   the first poll (every POLL_MS) that sees the playback head past frame 0;
//   sound_timestamp    the first AudioTrack.getTimestamp() past frame 0 whose time is not before this
//                      request's play() (a stamp of the previous request is ignored): presented_mono_ns is the
//                      IVI monotonic time at which frame frame_position was presented, and
//                      start_estimate_mono_ns that time minus frame_position at SAMPLE_RATE.
// Whether getTimestamp() answers for a static track on the Cuttlefish IVI, and how close any of
// these is to the sound leaving the guest, is what the phase 10 probe of the guests finds out: these are the app's own
// records, not a capture of the sound.
//
// Usage USAGE_ALARM with transient focus that lets others duck: the bench's choice; the
// AAOS-specific USAGE_SAFETY needs a system permission and is not used.
package org.de4sdv.collisionwarning;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioTimestamp;
import android.media.AudioTrack;
import android.os.Handler;
import android.os.HandlerThread;

final class WarningSound {

    static final long POLL_MS = 2L;
    static final long CONFIRM_TIMEOUT_MS = 1000L;

    interface Listener {
        /** A moment of the sound; monoNs on the IVI VM's monotonic clock. */
        void onSoundMark(PresentationTimeline.Mark mark, long request, long monoNs, Object... details);

        /** Something about the sound for the record (prepared, focus, failure, unconfirmed, stopped). */
        void onSoundNote(String event, Object... details);
    }

    private final Context context;
    private final Listener listener;
    private final PresentationTimeline timeline;
    private final HandlerThread thread = new HandlerThread("de4sdv-warning-sound");
    private Handler handler;
    private AudioTrack track;
    private AudioManager audio;
    private AudioAttributes attributes;
    private AudioFocusRequest focus;
    private int frames;
    private long playing;  // the request being played, 0 when silent

    WarningSound(Context context, PresentationTimeline timeline, Listener listener) {
        this.context = context;
        this.timeline = timeline;
        this.listener = listener;
    }

    synchronized void prepare() {
        thread.start();
        handler = new Handler(thread.getLooper());
        final short[] samples = WarningTone.pattern();
        frames = samples.length;
        attributes = new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ALARM)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build();
        try {
            track = new AudioTrack.Builder()
                    .setAudioAttributes(attributes)
                    .setAudioFormat(new AudioFormat.Builder()
                            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                            .setSampleRate(WarningTone.SAMPLE_RATE)
                            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                            .build())
                    .setTransferMode(AudioTrack.MODE_STATIC)
                    .setBufferSizeInBytes(samples.length * 2)
                    .build();
            final int written = track.write(samples, 0, samples.length);
            final int loop = track.setLoopPoints(0, frames, -1);
            audio = context.getSystemService(AudioManager.class);
            focus = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                    .setAudioAttributes(attributes)
                    .build();
            listener.onSoundNote("sound_prepared", "state", track.getState(), "written", written, "loop_points", loop,
                    "sample_rate", WarningTone.SAMPLE_RATE, "tone_hz", WarningTone.TONE_HZ,
                    "on_ms", WarningTone.ON_MS, "off_ms", WarningTone.OFF_MS, "usage", "USAGE_ALARM");
        } catch (Throwable error) {
            track = null;
            listener.onSoundNote("sound_failed", "reason", "prepare: " + error);
        }
    }

    /** Start the sound of a request; called on the subscriber's thread right after the receipt. */
    synchronized void start(long request) {
        if (track == null) {
            listener.onSoundNote("sound_failed", "request", request, "reason", "no AudioTrack");
            return;
        }
        if (playing != 0) {
            return;
        }
        playing = request;
        final long tPlay = System.nanoTime();
        try {
            track.play();
            if (timeline.mark(PresentationTimeline.Mark.SOUND_PLAY, request)) {
                listener.onSoundMark(PresentationTimeline.Mark.SOUND_PLAY, request, tPlay);
            }
            // Focus after play(): asking first would put a binder call in front of the sound.
            final int granted = audio == null ? -1 : audio.requestAudioFocus(focus);
            listener.onSoundNote("sound_focus", "request", request, "result", granted);
        } catch (Throwable error) {
            listener.onSoundNote("sound_failed", "request", request, "reason", "play: " + error);
            return;
        }
        final long deadline = System.nanoTime() + CONFIRM_TIMEOUT_MS * 1_000_000L;
        handler.post(new Runnable() {
            private final AudioTimestamp stamp = new AudioTimestamp();
            private boolean head;
            private boolean timestamp;

            @Override
            public void run() {
                synchronized (WarningSound.this) {
                    if (playing != request) {
                        return;
                    }
                    final long now = System.nanoTime();
                    if (!head && track.getPlaybackHeadPosition() > 0) {
                        head = true;
                        if (timeline.mark(PresentationTimeline.Mark.SOUND_HEAD, request)) {
                            listener.onSoundMark(PresentationTimeline.Mark.SOUND_HEAD, request, now,
                                    "head_position", track.getPlaybackHeadPosition());
                        }
                    }
                    // After pause() and reloadStaticData() the platform can still answer with the
                    // previous request's stamp: only a stamp at or after this request's play() counts.
                    if (!timestamp && track.getTimestamp(stamp) && stamp.framePosition > 0 && stamp.nanoTime >= tPlay) {
                        timestamp = true;
                        final long startEstimate = stamp.nanoTime
                                - stamp.framePosition * 1_000_000_000L / WarningTone.SAMPLE_RATE;
                        if (timeline.mark(PresentationTimeline.Mark.SOUND_TIMESTAMP, request)) {
                            listener.onSoundMark(PresentationTimeline.Mark.SOUND_TIMESTAMP, request, now,
                                    "frame_position", stamp.framePosition, "presented_mono_ns", stamp.nanoTime,
                                    "start_estimate_mono_ns", startEstimate);
                        }
                    }
                    if (head && timestamp) {
                        return;
                    }
                    if (now > deadline) {
                        listener.onSoundNote("sound_unconfirmed", "request", request, "head_moved", head,
                                "timestamp", timestamp, "after_ms", CONFIRM_TIMEOUT_MS);
                        return;
                    }
                }
                handler.postDelayed(this, POLL_MS);
            }
        });
    }

    /** Stop the sound of a request and rewind it for the next one. */
    synchronized void stop(long request) {
        if (track == null || playing != request) {
            return;
        }
        playing = 0;
        try {
            track.pause();
            track.reloadStaticData();
            track.setLoopPoints(0, frames, -1);
            if (audio != null) {
                audio.abandonAudioFocusRequest(focus);
            }
            listener.onSoundNote("sound_stopped", "request", request);
        } catch (Throwable error) {
            listener.onSoundNote("sound_failed", "request", request, "reason", "stop: " + error);
        }
    }

    synchronized void release() {
        playing = 0;
        if (track != null) {
            try {
                track.release();
            } catch (Throwable ignored) {
                // closing anyway
            }
            track = null;
        }
        thread.quitSafely();
    }
}
