// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Compile-only stand-in (tests/test_app_jvm.py): the signatures the app calls, with the platform's
// types and checked exceptions; no behavior. Never on the guest: the AOSP tree compiles the app
// against the real classes.
package com.google.protobuf;
public interface Parser<MessageType> {
    MessageType parseDelimitedFrom(java.io.InputStream input) throws InvalidProtocolBufferException;
}
