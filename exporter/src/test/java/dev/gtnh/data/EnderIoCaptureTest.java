package dev.gtnh.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import com.google.gson.JsonObject;
import org.junit.Test;

public class EnderIoCaptureTest {
    @Test
    public void sourceDeclarationsKeepAnyActualVersionWithoutVersionBasedApproval() {
        for (String version : new String[] {"2.10.49", "2.10.51", "future-development-version"}) {
            JsonObject source = EnderIoCapture.sourceDeclaration(version);
            assertFalse(source.has("native_version_supported"));
            assertEquals(version, source.get("native_version").getAsString());
            assertEquals("native_class_uid_contract",
                source.get("native_semantics_basis").getAsString());
        }
        assertTrue(EnderIoCapture.sourceDeclaration(null).get("native_version").isJsonNull());
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
