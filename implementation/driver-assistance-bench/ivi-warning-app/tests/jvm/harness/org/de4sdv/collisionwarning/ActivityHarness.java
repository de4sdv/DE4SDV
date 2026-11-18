// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The activity harness of tests/test_app_jvm.py: MainActivity against the recording stand-ins, no
// Android. It prints what the pytest asserts:
//   SUBSCRIBE <the gateway subscribe call, with its fetchLastMessageOnSubscribe flag>
//   START <the main-queue posts and the sound calls of a first true, in order>
//   CLEAR <the same for the false that follows>
// and leaves the record file in the directory named by -Dde4sdv.test.files.
package org.de4sdv.collisionwarning;

import de4sdv.teststubs.Calls;

import java.util.ArrayList;
import java.util.List;

public final class ActivityHarness {

    private ActivityHarness() {}

    private static List<String> presentation() {
        final List<String> out = new ArrayList<>();
        for (String call : Calls.snapshot()) {
            if (call.startsWith("main:") || call.startsWith("sound:")) {
                out.add(call);
            }
        }
        return out;
    }

    private static String subscribeCall() {
        for (String call : Calls.snapshot()) {
            if (call.startsWith("gateway:subscribe")) {
                return call;
            }
        }
        return null;
    }

    public static void main(String[] args) throws Exception {
        final MainActivity activity = new MainActivity();
        activity.onCreate(null);
        final long deadline = System.nanoTime() + 10_000_000_000L;
        String subscribe = subscribeCall();
        while (subscribe == null && System.nanoTime() < deadline) {
            Thread.sleep(20);
            subscribe = subscribeCall();
        }
        System.out.println("SUBSCRIBE " + subscribe);

        Calls.clear();
        activity.onMessage(1L, 1000L, System.nanoTime(), System.currentTimeMillis() * 1_000_000L);
        System.out.println("START " + presentation());

        Calls.clear();
        activity.onMessage(0L, 1100L, System.nanoTime(), System.currentTimeMillis() * 1_000_000L);
        System.out.println("CLEAR " + presentation());

        activity.onDestroy();
        System.out.println("DONE");
        System.exit(0);
    }
}
