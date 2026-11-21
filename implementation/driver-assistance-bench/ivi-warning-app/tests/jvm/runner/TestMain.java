// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// Runs every @Test method of the classes named on the command line and prints one line per
// test, then "RESULT run=<n> failed=<m>". Exit status 1 on any failure or on zero tests.
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;

public final class TestMain {
    public static void main(String[] args) throws Exception {
        int run = 0;
        int failed = 0;
        for (String name : args) {
            final Class<?> type = Class.forName(name);
            final Method[] methods = type.getDeclaredMethods();
            java.util.Arrays.sort(methods, (a, b) -> a.getName().compareTo(b.getName()));
            for (Method method : methods) {
                if (!method.isAnnotationPresent(org.junit.Test.class) || Modifier.isStatic(method.getModifiers())) {
                    continue;
                }
                run++;
                try {
                    method.invoke(type.getDeclaredConstructor().newInstance());
                    System.out.println("PASS " + name + "." + method.getName());
                } catch (InvocationTargetException error) {
                    failed++;
                    System.out.println("FAIL " + name + "." + method.getName() + ": " + error.getCause());
                }
            }
        }
        System.out.println("RESULT run=" + run + " failed=" + failed);
        System.exit(failed == 0 && run > 0 ? 0 : 1);
    }
}
