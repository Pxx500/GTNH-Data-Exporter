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
        assertNull(EnderIoCapture.outputChance(Float.NaN));
        assertNull(EnderIoCapture.outputChance(Float.POSITIVE_INFINITY));
    }

    private void assertChance(float threshold, long numerator, long denominator) {
        JsonObject actual = EnderIoCapture.outputChance(threshold);
        assertEquals(numerator, actual.get("numerator").getAsLong());
        assertEquals(denominator, actual.get("denominator").getAsLong());
    }
}
