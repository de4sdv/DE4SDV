// Copyright (C) 2026 DE4SDV contributors
// SPDX-License-Identifier: Apache-2.0
//
// The screen's regions, Android-free. One region per kind of information
// (HMI design rules): the plan panel left; mode, speed, plan facts and clocks
// stacked right; identity, counters and the provenance line along the bottom;
// the freshness chip in the header.
//
// Laid out for the IVI centre display of the earlier recordings, 1080 x 600
// px, and scaled uniformly into the part of the view the system bars leave
// free (s = min(w/1080, h/600) of that part; place()). Text widths are checked against a conservative monospace advance
// of 0.61 em (DejaVu/Droid Sans Mono advance 1229/2048 = 0.600 em), so a line
// that passes ScreenLayoutTest also fits on the device; the view additionally
// shrinks a line at draw time if Paint.measureText says it does not fit.
package org.de4sdv.drivingstate;

final class ScreenLayout {

    static final float REF_W = 1080f;
    static final float REF_H = 600f;
    static final float MONO_ADVANCE_EM = 0.61f;
    static final float LINE_SPACING = 1.25f;
    /** Inner padding: horizontal, and vertical above the first and below the last line. */
    static final float PAD = 10f;
    static final float PAD_Y = 6f;
    /** The header is one title row plus one status row; it uses a tighter padding. */
    static final float HEADER_PAD = 3f;

    // Text sizes in reference px. Nothing below 15 px: in a video that puts the
    // 1080 x 600 capture beside a 1280 x 720 simulator view and downscales the
    // pair to 1920 px wide (factor 0.745 at equal heights), 15 px becomes 11 px.
    static final float TITLE = 22f;
    static final float CHIP = 22f;
    static final float MODE = 40f;
    static final float CAUSE = 21f;
    static final float SPEED = 30f;
    static final float CLOCK = 21f;
    static final float BODY = 19f;
    static final float SMALL = 16f;
    static final float NOTE = 15f;
    static final float MIN_TEXT = 15f;

    static final class Box {
        final float left;
        final float top;
        final float width;
        final float height;

        Box(float left, float top, float width, float height) {
            this.left = left;
            this.top = top;
            this.width = width;
            this.height = height;
        }

        float right() {
            return left + width;
        }

        float bottom() {
            return top + height;
        }
    }

    // Reference boxes (1080 x 600).
    static final Box HEADER = new Box(12f, 0f, 1056f, 54f);
    static final Box PLAN = new Box(12f, 56f, 540f, 448f);
    static final Box PLAN_TITLE = new Box(12f, 56f, 540f, 26f);
    static final Box PLAN_PLOT = new Box(12f, 82f, 540f, 396f);
    static final Box PLAN_CAPTION = new Box(12f, 478f, 540f, 26f);
    static final Box MODE_BOX = new Box(564f, 56f, 504f, 110f);
    static final Box SPEED_BOX = new Box(564f, 170f, 504f, 112f);
    static final Box FACTS_BOX = new Box(564f, 286f, 504f, 107f);
    static final Box CLOCKS_BOX = new Box(564f, 397f, 504f, 107f);
    static final Box FOOTER = new Box(12f, 510f, 1056f, 86f);

    static final Box[] ALL = {HEADER, PLAN, MODE_BOX, SPEED_BOX, FACTS_BOX, CLOCKS_BOX, FOOTER};

    private ScreenLayout() {}

    /** Uniform scale of the reference layout into a view of w x h px. */
    static float scaleFor(float w, float h) {
        return Math.min(w / REF_W, h / REF_H);
    }

    /** Scale and origin of the reference layout inside a view, view px. */
    static final class Placement {
        final float scale;
        final float left;
        final float top;

        Placement(float scale, float left, float top) {
            this.scale = scale;
            this.left = left;
            this.top = top;
        }
    }

    /**
     * Places the reference layout in the part of a w x h view that the system bars leave free.
     * The window is laid out edge to edge (enforced from Android 15), so the bars cover the
     * view's edges by the given insets; hidden bars give zero insets and the layout fills the
     * view as before. Uniform scale, centred in the free area. A free area without width or
     * height gives scale 0: nothing can be drawn.
     */
    static Placement place(float w, float h, float insetLeft, float insetTop, float insetRight, float insetBottom) {
        final float freeW = w - insetLeft - insetRight;
        final float freeH = h - insetTop - insetBottom;
        if (freeW <= 0f || freeH <= 0f) {
            return new Placement(0f, 0f, 0f);
        }
        final float s = scaleFor(freeW, freeH);
        return new Placement(s, insetLeft + (freeW - s * REF_W) / 2f, insetTop + (freeH - s * REF_H) / 2f);
    }

    /** Width of a monospace line at a reference text size, reference px. */
    static float textWidth(String text, float size) {
        return text.codePointCount(0, text.length()) * MONO_ADVANCE_EM * size;
    }

    /** True when the line fits the box's inner width. */
    static boolean fitsWidth(Box box, String text, float size) {
        return textWidth(text, size) <= box.width - 2f * PAD;
    }

    /** Height a stack of lines needs, reference px (padding included). */
    static float stackHeight(float[] sizes) {
        return stackHeight(sizes, PAD_Y);
    }

    static float stackHeight(float[] sizes, float pad) {
        float h = 2f * pad;
        for (float s : sizes) {
            h += s * LINE_SPACING;
        }
        return h;
    }

    /** True when two boxes do not overlap. */
    static boolean disjoint(Box a, Box b) {
        return a.right() <= b.left || b.right() <= a.left || a.bottom() <= b.top || b.bottom() <= a.top;
    }
}
