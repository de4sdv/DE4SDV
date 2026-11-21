// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The calls the recording stand-ins saw, in order, for the activity harness
// (tests/jvm/harness/). Not a platform class; never on the guest.
package de4sdv.teststubs;

import java.util.ArrayList;
import java.util.List;

public final class Calls {
    private static final List<String> CALLS = new ArrayList<>();

    private Calls() {}

    public static synchronized void add(String call) {
        CALLS.add(call);
    }

    public static synchronized List<String> snapshot() {
        return new ArrayList<>(CALLS);
    }

    public static synchronized void clear() {
        CALLS.clear();
    }
}
