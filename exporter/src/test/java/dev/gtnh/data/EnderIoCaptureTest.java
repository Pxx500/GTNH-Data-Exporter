package dev.gtnh.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import com.google.gson.JsonObject;
import org.junit.Test;

public class EnderIoCaptureTest {
    @Test
    public void nativeFloatThresholdIncludesEqualityAndSharedRollBoundaries() {
        assertChance(0f, 1, 16777216);
        assertChance(0.5f, 8388609, 16777216);
        assertChance(1f, 1, 1);
        assertChance(-0.5f, 0, 1);
        assertNull(NativeCapture.floatRollChance(Float.NaN, true));
        assertNull(NativeCapture.floatRollChance(Float.POSITIVE_INFINITY, true));
    }

    private void assertChance(float threshold, long numerator, long denominator) {
        JsonObject actual = NativeCapture.floatRollChance(threshold, true);
        assertEquals(numerator, actual.get("numerator").getAsLong());
        assertEquals(denominator, actual.get("denominator").getAsLong());
    }
}
