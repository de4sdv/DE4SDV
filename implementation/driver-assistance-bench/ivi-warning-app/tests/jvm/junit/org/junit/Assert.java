// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// A stand-in for the subset of JUnit 4's Assert the app's tests use, with JUnit's semantics
// (equality by equals(), integral values compared as long). The AOSP tree's java_test links
// the real JUnit.
package org.junit;

import java.util.Objects;

public final class Assert {
    private Assert() {}

    public static void fail(String message) {
        throw new AssertionError(message);
    }

    public static void assertTrue(boolean condition) {
        assertTrue(null, condition);
    }

    public static void assertTrue(String message, boolean condition) {
        if (!condition) {
            fail(message == null ? "expected true" : message);
        }
    }

    public static void assertFalse(boolean condition) {
        assertFalse(null, condition);
    }

    public static void assertFalse(String message, boolean condition) {
        assertTrue(message == null ? "expected false" : message, !condition);
    }

    public static void assertEquals(long expected, long actual) {
        assertEquals(null, expected, actual);
    }

    public static void assertEquals(String message, long expected, long actual) {
        if (expected != actual) {
            fail((message == null ? "" : message + ": ") + "expected:<" + expected + "> but was:<" + actual + ">");
        }
    }

    public static void assertEquals(Object expected, Object actual) {
        assertEquals(null, expected, actual);
    }

    public static void assertEquals(String message, Object expected, Object actual) {
        if (!Objects.equals(expected, actual)) {
            fail((message == null ? "" : message + ": ") + "expected:<" + expected + "> but was:<" + actual + ">");
        }
    }
}
