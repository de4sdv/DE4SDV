// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Compile-only stand-in (tests/test_app_jvm.py): the signatures the app calls, with the platform's
// types and checked exceptions; no behavior. Never on the guest: the AOSP tree compiles the app
// against the real classes.
package de4sdv.driving.v1;
// The outer class protoc's java_lite generator names for de4sdv_driving_collision_warning_request.proto
// (no java_outer_classname option: the file name in camel case, a capital after the digit, as the
// INC-DRIVING-001 observer's De4SdvDrivingOperationalState).
public final class De4SdvDrivingCollisionWarningRequest {
    public static final class CollisionWarningRequest {
        public static com.google.protobuf.Parser<CollisionWarningRequest> parser() { return null; }
        public int getRequested() { return 0; }
        public int getIssueTimeSimMs() { return 0; }
    }
}
