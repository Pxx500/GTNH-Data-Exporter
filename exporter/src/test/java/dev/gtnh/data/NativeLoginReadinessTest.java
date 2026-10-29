package dev.gtnh.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;

import org.junit.Test;

public class NativeLoginReadinessTest {
    @Test
    public void verifiedProtocolVersionsRetainTheirActualIdentity() {
        assertEquals("2.9.89", NativeLoginReadiness.requireSupportedVersion("2.9.89"));
        assertEquals("2.9.98", NativeLoginReadiness.requireSupportedVersion("2.9.98"));
    }

    @Test
    public void absentAndUnverifiedOwnersCannotBypassTheNativeProtocolGate() {
        for (String version : new String[] {null, "", "2.9.88", "2.9.90", "2.9.99"}) {
            assertThrows(IllegalStateException.class, () -> NativeLoginReadiness.requireSupportedVersion(version));
        }
    }
}
