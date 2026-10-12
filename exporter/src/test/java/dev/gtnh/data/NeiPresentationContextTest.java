package dev.gtnh.data;

import static org.junit.Assert.*;

import com.google.gson.JsonObject;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.Test;

public final class NeiPresentationContextTest {
    @Test
    public void refusesChangedCanonicalStreamsBeforeNativeQueries() throws Exception {
        Path snapshot = Files.createTempDirectory("nei-context-integrity").resolve("snapshot");
        JsonObject manifest = Jsons.object("snapshot_id", "context-test", "pack", Jsons.object());
        try (SnapshotWriter writer = new SnapshotWriter(snapshot)) {
            writer.publish(manifest);
        }
        Files.write(snapshot.resolve("resources.jsonl.gz"), "changed".getBytes(StandardCharsets.UTF_8));
        Path reference = Files.createDirectory(snapshot.resolve("nei-reference"));
        try {
            NeiPresentationContext.capture(reference, manifest);
            fail("Changed canonical files must not seed presentation context");
        } catch (IOException expected) {
            assertTrue(expected.getMessage().contains("resources.jsonl.gz checksum"));
        }
        assertFalse(Files.exists(reference.resolve("presentation-context.json")));
    }

    @Test
    public void refusesIncorrectCanonicalRecordCountsBeforeNativeQueries() throws Exception {
        Path snapshot = Files.createTempDirectory("nei-context-count").resolve("snapshot");
        JsonObject manifest = Jsons.object("snapshot_id", "context-test", "pack", Jsons.object());
        try (SnapshotWriter writer = new SnapshotWriter(snapshot)) {
            writer.publish(manifest);
        }
        manifest.getAsJsonObject("files").getAsJsonObject("processes.jsonl.gz").addProperty("records", 1);
        Path reference = Files.createDirectory(snapshot.resolve("nei-reference"));
        try {
            NeiPresentationContext.capture(reference, manifest);
            fail("Incorrect record declarations must not seed presentation context");
        } catch (IOException expected) {
            assertTrue(expected.getMessage().contains("processes.jsonl.gz record count"));
        }
        assertFalse(Files.exists(reference.resolve("presentation-context.json")));
    }
}
