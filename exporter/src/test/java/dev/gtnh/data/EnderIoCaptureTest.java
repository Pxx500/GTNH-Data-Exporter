package dev.gtnh.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import com.google.gson.JsonObject;
import org.junit.Test;

public class EnderIoCaptureTest {
    @Test
    public void sourceProfilesKeepActualVersionAndRejectUnverifiedRuntimes() {
        for (String version : new String[] {"2.10.49", "2.10.51"}) {
            JsonObject source = EnderIoCapture.sourceDeclaration(version);
            assertTrue(source.get("native_version_supported").getAsBoolean());
            assertEquals(version, source.get("native_version").getAsString());
            assertEquals("verified_2.10.49_2.10.51_narrow_class_equivalence",
                source.get("native_semantics_basis").getAsString());
        }
        for (String version : new String[] {null, "2.10.50", "2.10.52"}) {
            JsonObject source = EnderIoCapture.sourceDeclaration(version);
            assertFalse(source.get("native_version_supported").getAsBoolean());
            assertEquals("unsupported_native_version", source.get("native_semantics_basis").getAsString());
        }
    }

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
