// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The writer of files/warning.jsonl: one thread that owns the file, fed through a queue. The
// callers (the subscriber's thread, the UI thread inside onDraw, the sound thread) only format a
// line and hand it over, so no file write or flush sits in front of a frame commit or a play()
// (review R13 of fc74de16). The times on each line are taken by the caller before the hand-over.
//
// The file is opened in append mode: an activity that is created again (a configuration change the
// manifest does not absorb, a restart) adds its lines after the earlier ones instead of truncating
// them (review R11). Each start writes a lifecycle line with its pid, so the runs can be told apart.
//
// No Android import: a plain JVM test pins the behavior.
package org.de4sdv.collisionwarning;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

final class RecordWriter implements AutoCloseable {

    interface Failure {
        /** A write, flush or close failed; called on the writer thread. */
        void onFailure(String what, IOException error);
    }

    static final long CLOSE_WAIT_MS = 2000L;

    private static final String STOP = new String("stop");  // identity sentinel

    private final BlockingQueue<String> queue = new LinkedBlockingQueue<>();
    private final Writer out;
    private final Failure failure;
    private final Thread thread;
    private volatile boolean closed;

    RecordWriter(File file, Failure failure) throws IOException {
        this.out = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(file, true), StandardCharsets.UTF_8));
        this.failure = failure;
        this.thread = new Thread(this::loop, "de4sdv-warning-record");
        this.thread.setDaemon(true);
        this.thread.start();
    }

    /** Queue one line (without its newline); never blocks the caller on the file. */
    void write(String line) {
        if (!closed) {
            queue.offer(line);
        }
    }

    /** Write what is queued, then close the file; waits at most CLOSE_WAIT_MS. */
    @Override
    public void close() {
        if (closed) {
            return;
        }
        closed = true;
        queue.offer(STOP);
        try {
            thread.join(CLOSE_WAIT_MS);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
        }
    }

    private void loop() {
        try {
            while (true) {
                final String line = queue.poll(1, TimeUnit.SECONDS);
                if (line == null) {
                    continue;
                }
                if (line == STOP) {
                    break;
                }
                try {
                    out.write(line);
                    out.write('\n');
                    if (queue.isEmpty()) {
                        out.flush();
                    }
                } catch (IOException error) {
                    failure.onFailure("write", error);
                }
            }
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
        } finally {
            try {
                out.close();
            } catch (IOException error) {
                failure.onFailure("close", error);
            }
        }
    }
}
