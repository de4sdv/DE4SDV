// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The record writer: lines in the order given, appended after an earlier run's lines, written when
// close() returns, and nothing after close.
package org.de4sdv.collisionwarning;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.List;

import org.junit.Test;

public class RecordWriterTest {

    private static File tempFile() throws IOException {
        final File file = File.createTempFile("warning", ".jsonl");
        file.deleteOnExit();
        return file;
    }

    private static List<String> lines(File file) throws IOException {
        return Files.readAllLines(file.toPath(), StandardCharsets.UTF_8);
    }

    @Test
    public void linesArriveInOrderWhenCloseReturns() throws IOException {
        final File file = tempFile();
        final RecordWriter writer = new RecordWriter(file, (what, error) -> { throw new AssertionError(what, error); });
        for (int i = 0; i < 200; i++) {
            writer.write("{\"n\":" + i + "}");
        }
        writer.close();
        final List<String> got = lines(file);
        assertEquals(200, got.size());
        assertEquals("{\"n\":0}", got.get(0));
        assertEquals("{\"n\":199}", got.get(199));
    }

    @Test
    public void aSecondWriterAppendsAfterTheFirstRunsLines() throws IOException {
        final File file = tempFile();
        final RecordWriter first = new RecordWriter(file, (what, error) -> { throw new AssertionError(what, error); });
        first.write("first run");
        first.close();
        final RecordWriter second = new RecordWriter(file, (what, error) -> { throw new AssertionError(what, error); });
        second.write("second run");
        second.close();
        assertEquals(Arrays.asList("first run", "second run"), lines(file));
    }

    @Test
    public void nothingIsWrittenAfterClose() throws IOException {
        final File file = tempFile();
        final RecordWriter writer = new RecordWriter(file, (what, error) -> { throw new AssertionError(what, error); });
        writer.write("kept");
        writer.close();
        writer.write("dropped");
        writer.close();
        assertEquals(Arrays.asList("kept"), lines(file));
        assertTrue(file.length() > 0);
    }
}
