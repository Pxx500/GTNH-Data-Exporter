package dev.gtnh.data;

import static org.junit.Assert.*;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.zip.GZIPInputStream;
import org.junit.Test;

public final class SnapshotWriterTest {
    @Test
    public void exposesClosedFileDeclarationsBeforeManifestPublication() throws Exception {
        Path directory = Files.createTempDirectory("gtnh-closed-declarations").resolve("snapshot");
        JsonObject declarations;
        try (SnapshotWriter writer = new SnapshotWriter(directory)) {
            assertThrows(IllegalStateException.class, writer::fileDeclarations);
            writer.append("resources", Jsons.object("id", "r1"));
            writer.append("processes", Jsons.object("id", "p1"));
            writer.close();
            declarations = writer.fileDeclarations();
            assertFalse(Files.exists(directory.resolve("manifest.json")));
            assertFalse(Files.exists(directory.resolve("manifest.json.tmp")));
            assertEquals(6, declarations.entrySet().size());
            assertEquals(1L, declarations.getAsJsonObject("resources.jsonl.gz").get("records").getAsLong());
            assertEquals(1L, declarations.getAsJsonObject("processes.jsonl.gz").get("records").getAsLong());
            assertEquals(0L, declarations.getAsJsonObject("sources.jsonl.gz").get("records").getAsLong());
            for (java.util.Map.Entry<String, com.google.gson.JsonElement> entry : declarations.entrySet()) {
                assertEquals(SnapshotWriter.sha256(directory.resolve(entry.getKey())),
                    entry.getValue().getAsJsonObject().get("sha256").getAsString());
            }
            writer.publish(Jsons.object("schema_version", 1, "snapshot_id", "test"));
        }
        JsonObject manifest = new JsonParser().parse(new String(Files.readAllBytes(directory.resolve("manifest.json")),
            StandardCharsets.UTF_8)).getAsJsonObject();
        assertEquals(declarations, manifest.getAsJsonObject("files"));
    }

    @Test
    public void publishesClosedStreamsWithChecksumsAndLosslessRecords() throws Exception {
        Path directory = Files.createTempDirectory("gtnh-snapshot-test").resolve("snapshot");
        try (SnapshotWriter writer = new SnapshotWriter(directory)) {
            writer.append("resources", Jsons.object("id", "r1", "display_name", "Żółć \"ore\"", "nbt", null));
            assertFalse(Files.exists(directory.resolve("manifest.json")));
            writer.publish(Jsons.object("schema_version", 1, "snapshot_id", "test"));
        }
        JsonObject manifest = new JsonParser().parse(new String(Files.readAllBytes(directory.resolve("manifest.json")),
            StandardCharsets.UTF_8)).getAsJsonObject();
        JsonObject files = manifest.getAsJsonObject("files");
        assertEquals(6, files.entrySet().size());
        assertEquals(1L, files.getAsJsonObject("resources.jsonl.gz").get("records").getAsLong());
        for (java.util.Map.Entry<String, com.google.gson.JsonElement> entry : files.entrySet()) {
            assertEquals(SnapshotWriter.sha256(directory.resolve(entry.getKey())), entry.getValue().getAsJsonObject().get("sha256").getAsString());
        }
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(new GZIPInputStream(
            Files.newInputStream(directory.resolve("resources.jsonl.gz"))), StandardCharsets.UTF_8))) {
            JsonObject resource = new JsonParser().parse(reader.readLine()).getAsJsonObject();
            assertEquals("Żółć \"ore\"", resource.get("display_name").getAsString());
            assertTrue(resource.get("nbt").isJsonNull());
            assertNull(reader.readLine());
        }
    }

    @Test
    public void refusesToOverwriteAnExistingSnapshot() throws Exception {
        Path directory = Files.createTempDirectory("gtnh-existing-snapshot");
        Files.write(directory.resolve("manifest.json"), "existing".getBytes(StandardCharsets.UTF_8));
        try {
            new SnapshotWriter(directory);
            fail("Existing directory must be preserved");
        } catch (java.nio.file.FileAlreadyExistsException expected) {
            assertEquals("existing", new String(Files.readAllBytes(directory.resolve("manifest.json")), StandardCharsets.UTF_8));
        }
    }
}
