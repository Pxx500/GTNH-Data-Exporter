package dev.gtnh.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

import com.google.gson.JsonObject;
import org.junit.Test;

public class ForestryCaptureTest {
    @Test
    public void separateFloatRollsUseStrictThresholdsIncludingZeroAndTinyPositiveChance() {
        assertChance(0f, 0, 16777216);
        assertChance(-0.0f, 0, 16777216);
        assertChance(Float.MIN_VALUE, 1, 16777216);
        assertChance(0.5f, 8388608, 16777216);
        assertChance(Math.nextDown(1f), 16777215, 16777216);
        assertChance(1f, 1, 1);
        assertChance(2f, 1, 1);
        assertChance(-0.5f, 0, 1);
        assertNull(NativeCapture.floatRollChance(Float.NaN, false));
        assertNull(NativeCapture.floatRollChance(Float.POSITIVE_INFINITY, false));
        assertNull(NativeCapture.floatRollChance(Float.NEGATIVE_INFINITY, false));
    }

    private void assertChance(float threshold, long numerator, long denominator) {
        JsonObject actual = NativeCapture.floatRollChance(threshold, false);
        assertEquals(numerator, actual.get("numerator").getAsLong());
        assertEquals(denominator, actual.get("denominator").getAsLong());
    }
}
