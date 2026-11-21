// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// A stand-in for JUnit 4's @Test so the app's tests run on a host with a JDK and no JUnit jar
// (tests/test_app_jvm.py). In the AOSP tree the java_test links the real JUnit.
package org.junit;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface Test {}
