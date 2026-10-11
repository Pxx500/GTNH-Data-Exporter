package dev.gtnh.data;

import com.google.common.hash.Hashing;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import java.io.BufferedWriter;
import java.io.Closeable;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.zip.GZIPOutputStream;

/** Publishes the manifest only after every compressed record stream is closed. */
public final class SnapshotWriter implements Closeable {
    public static final Gson JSON = new GsonBuilder().serializeNulls().disableHtmlEscaping().create();
    private static final String[] COLLECTIONS = {
        "resources", "groups", "processes", "sources", "environments", "coverage"
    };
    private final Path directory;
    private final Map<String, BufferedWriter> streams = new LinkedHashMap<>();
    private final Map<String, Long> counts = new LinkedHashMap<>();
    private boolean closed;

    public SnapshotWriter(Path directory) throws IOException {
        this.directory = directory;
        Files.createDirectory(directory);
        try {
            for (String name : COLLECTIONS) {
                streams.put(name, new BufferedWriter(new OutputStreamWriter(new GZIPOutputStream(
                    Files.newOutputStream(directory.resolve(name + ".jsonl.gz"), StandardOpenOption.CREATE_NEW)),
                    StandardCharsets.UTF_8)));
                counts.put(name, 0L);
            }
        } catch (IOException failure) {
            try { close(); } catch (IOException cleanup) { failure.addSuppressed(cleanup); }
            throw failure;
        }
    }

    public void append(String collection, JsonObject record) throws IOException {
        if (closed) throw new IllegalStateException("Snapshot streams are closed");
        BufferedWriter stream = streams.get(collection);
        if (stream == null) throw new IllegalArgumentException("Unknown collection: " + collection);
        stream.write(JSON.toJson(record));
        stream.newLine();
        counts.put(collection, counts.get(collection) + 1L);
    }

    public long count(String collection) { return counts.get(collection); }

    public void publish(JsonObject manifest) throws IOException {
        close();
        JsonObject files = new JsonObject();
        for (String name : COLLECTIONS) {
            String filename = name + ".jsonl.gz";
            files.add(filename, Jsons.object("sha256", sha256(directory.resolve(filename)), "records", counts.get(name)));
        }
        manifest.add("files", files);
        Path temporary = directory.resolve("manifest.json.tmp");
        Files.write(temporary, JSON.toJson(manifest).getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE_NEW);
        Files.move(temporary, directory.resolve("manifest.json"), StandardCopyOption.ATOMIC_MOVE);
    }

    public static String sha256(Path path) throws IOException {
        return com.google.common.io.Files.asByteSource(path.toFile()).hash(Hashing.sha256()).toString();
    }

    @Override
    public void close() throws IOException {
        if (closed) return;
        closed = true;
        IOException failure = null;
        for (BufferedWriter stream : streams.values()) {
            try { stream.close(); }
            catch (IOException error) {
                if (failure == null) failure = error;
                else failure.addSuppressed(error);
            }
        }
        if (failure != null) throw failure;
    }
}
