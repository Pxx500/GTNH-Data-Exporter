package dev.gtnh.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertThrows;

import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

public final class NeiReferenceCaptureTest {
    @Rule
    public final TemporaryFolder temporary = new TemporaryFolder();

    @Test
    public void unsupportedScopeIsRejectedBeforeNativeReadinessOrArtifactCreation() {
        String property = "gtnh.data.neiReferenceScope";
        String previous = System.getProperty(property);
        Path output = temporary.getRoot().toPath().resolve("reference");
        try {
            System.setProperty(property, "unsupported");
            IllegalArgumentException error = assertThrows(IllegalArgumentException.class,
                () -> NeiReferenceCapture.capture(output, new com.google.gson.JsonObject()));
            assertEquals("Unsupported NEI reference scope: unsupported", error.getMessage());
            assertFalse(Files.exists(output));
        } finally {
            if (previous == null) System.clearProperty(property);
            else System.setProperty(property, previous);
        }
    }
}
