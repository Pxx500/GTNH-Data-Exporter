package dev.gtnh.data;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertThrows;
import static org.junit.Assert.assertTrue;

import codechicken.nei.recipe.ICraftingHandler;
import codechicken.nei.recipe.IUsageHandler;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.io.InputStreamReader;
import java.io.BufferedReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.zip.GZIPInputStream;
import java.util.jar.JarOutputStream;
import java.util.jar.JarEntry;
import java.util.jar.Manifest;
import java.net.URL;
import java.net.URLClassLoader;
import java.net.JarURLConnection;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

public final class NeiReferenceCaptureTest {
    @Rule
    public final TemporaryFolder temporary = new TemporaryFolder();

    @Test
    public void inventoryPersistsBothRostersAndAliasesWithoutCallingHandlerMethods() throws Exception {
        Object first = new OpaqueCraftHandler();
        Object second = new OpaqueCraftHandler();
        Object usageOnly = new OpaqueUsageHandler();
        List<List<?>> rosters = Arrays.asList(new ArrayList<>(Arrays.asList(first, second)),
            new ArrayList<>(Arrays.asList(first)), new ArrayList<>(Arrays.asList(first, usageOnly)),
            new ArrayList<>(Arrays.asList((Object) null)));
        Path output = temporary.getRoot().toPath().resolve("inventory");
        JsonObject manifest = inventoryManifest();
            NeiReferenceCapture.captureInventory(output, manifest, () -> rosters);
            List<JsonObject> rows = new ArrayList<>();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(
                new GZIPInputStream(Files.newInputStream(output.resolve("handlers.jsonl.gz"))), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) rows.add(SnapshotWriter.JSON.fromJson(line, JsonObject.class));
            }
            assertEquals(6, rows.size());
            assertEquals("craftinghandlers", rows.get(0).get("registration").getAsString());
            assertEquals("serialCraftingHandlers", rows.get(2).get("registration").getAsString());
            assertEquals(0, rows.get(2).get("registration_index").getAsInt());
            assertEquals(2, rows.get(2).get("global_index").getAsInt());
            assertEquals(rows.get(0).get("object_key"), rows.get(2).get("object_key"));
            assertEquals("h0", rows.get(2).get("same_instance_as").getAsString());
            assertFalse(rows.get(0).get("object_key").equals(rows.get(1).get("object_key")));
            assertTrue(rows.get(1).get("same_instance_as").isJsonNull());
            JsonObject source = rows.get(0).getAsJsonArray("hierarchy").get(0).getAsJsonObject().getAsJsonObject("source");
            assertEquals("unique_class_resource", source.get("basis").getAsString());
            assertEquals("directory", source.get("status").getAsString());
            assertEquals("usagehandlers", rows.get(3).get("registration").getAsString());
            assertEquals("h0", rows.get(3).get("same_instance_as").getAsString());
            assertTrue(rows.get(4).getAsJsonArray("interfaces").toString().contains(IUsageHandler.class.getName()));
            assertEquals("serialUsageHandlers", rows.get(5).get("registration").getAsString());
            assertTrue(rows.get(5).get("native_class").isJsonNull());
            assertEquals(1, rows.get(5).getAsJsonArray("failures").size());
            JsonObject summary = SnapshotWriter.JSON.fromJson(new String(Files.readAllBytes(output.resolve("summary.json")),
                StandardCharsets.UTF_8), JsonObject.class);
            assertEquals("handler_inventory", summary.get("profile").getAsString());
            assertEquals(manifest.get("snapshot_id"), summary.get("canonical_snapshot_id"));
            assertEquals(manifest.get("files"), summary.get("canonical_files"));
            assertTrue(summary.getAsJsonObject("rosters").get("stable").getAsBoolean());
            assertFalse(summary.get("complete").getAsBoolean());
            assertEquals(0, summary.getAsJsonObject("counts").get("handler_views").getAsInt());
            assertEquals(SnapshotWriter.sha256(output.resolve("handlers.jsonl.gz")), summary.getAsJsonObject("files")
                .getAsJsonObject("handlers.jsonl.gz").get("sha256").getAsString());
    }

    private JsonObject inventoryManifest() {
        JsonObject files = new JsonObject();
        for (String stream : Arrays.asList("resources", "groups", "processes", "sources", "environments", "coverage"))
            files.add(stream + ".jsonl.gz", Jsons.object("records", 0, "sha256", "unverified_test_digest"));
        return Jsons.object("snapshot_id", "test-inventory", "pack", Jsons.object("mods", new JsonArray(),
            "config_script_digests", new JsonArray()), "files", files);
    }

    @Test
    public void classResourceOriginsRequireOneDistinctOriginAndExposeMissingResources() throws Exception {
        String resource = "sample/Entry.class";
        Path first = temporary.newFolder("origin-one").toPath();
        Path second = temporary.newFolder("origin-two").toPath();
        for (Path root : Arrays.asList(first, second)) {
            Files.createDirectories(root.resolve("sample"));
            Files.write(root.resolve(resource), new byte[] {0});
        }
        try (URLClassLoader loader = new URLClassLoader(new URL[] {first.toUri().toURL()}, null)) {
            JsonObject unique = NeiReferenceCapture.classResourceOrigin(loader, resource);
            assertEquals("directory", unique.get("status").getAsString());
            assertEquals(first.toRealPath().toUri().toString(), unique.getAsJsonArray("origins").get(0).getAsString());
            JsonObject missing = NeiReferenceCapture.classResourceOrigin(loader, "sample/Missing.class");
            assertEquals("unavailable", missing.get("status").getAsString());
            assertEquals("class_resource_missing", missing.get("reason").getAsString());
        }
        try (URLClassLoader loader = new URLClassLoader(new URL[] {first.toUri().toURL(), second.toUri().toURL()}, null)) {
            JsonObject ambiguous = NeiReferenceCapture.classResourceOrigin(loader, resource);
            assertEquals("unavailable", ambiguous.get("status").getAsString());
            assertEquals("ambiguous_class_origins", ambiguous.get("reason").getAsString());
            assertEquals(2, ambiguous.getAsJsonArray("origins").size());
            assertTrue(ambiguous.get("sha256").isJsonNull());
        }
    }

    @Test
    public void jarClassResourceOriginUsesTheActualArchiveWithoutDefiningTheClass() throws Exception {
        Path jar = temporary.getRoot().toPath().resolve("origin.jar");
        try (JarOutputStream output = new JarOutputStream(Files.newOutputStream(jar))) {
            output.putNextEntry(new JarEntry("sample/Entry.class"));
            output.write(0);
            output.closeEntry();
        }
        try (URLClassLoader loader = new URLClassLoader(new URL[] {jar.toUri().toURL()}, null)) {
            JsonObject source = NeiReferenceCapture.classResourceOrigin(loader, "sample/Entry.class");
            assertEquals("jar", source.get("status").getAsString());
            assertEquals("unique_class_resource", source.get("basis").getAsString());
            assertEquals("origin.jar", source.get("file").getAsString());
            assertEquals(jar.toRealPath().toUri().toString(), source.getAsJsonArray("origins").get(0).getAsString());
        }
    }

    @Test
    public void multiReleaseOriginRetainsTheFullJarSelectedByTheActualLoader() throws Exception {
        Path jar = temporary.getRoot().toPath().resolve("multi-release.jar");
        versionedJar(jar, true);
        try (URLClassLoader loader = new URLClassLoader(new URL[] {jar.toUri().toURL()}, null)) {
            JarURLConnection selected = (JarURLConnection) loader.getResource("sample/Entry.class").openConnection();
            assertEquals("META-INF/versions/17/sample/Entry.class", selected.getEntryName());
            JsonObject source = NeiReferenceCapture.classResourceOrigin(loader, "sample/Entry.class");
            assertEquals("jar", source.get("status").getAsString());
            assertEquals("multi-release.jar", source.get("file").getAsString());
            assertEquals(jar.toRealPath().toUri().toString(), source.getAsJsonArray("origins").get(0).getAsString());
        }
    }

    @Test
    public void versionedEntriesRequireExactBinaryPathStandardVersionAndManifestAuthority() throws Exception {
        Path marked = temporary.getRoot().toPath().resolve("marked.jar");
        Path unmarked = temporary.getRoot().toPath().resolve("unmarked.jar");
        versionedJar(marked, true);
        versionedJar(unmarked, false);
        assertTrue(NeiReferenceCapture.matchesJarClassResource(jarEntry(marked, "sample/Entry.class"), "sample/Entry.class"));
        assertTrue(NeiReferenceCapture.matchesJarClassResource(jarEntry(marked,
            "META-INF/versions/17/sample/Entry.class"), "sample/Entry.class"));
        for (String invalid : Arrays.asList("META-INF/versions/17/other/Entry.class",
            "prefix/META-INF/versions/17/sample/Entry.class", "META-INF/versions/8/sample/Entry.class",
            "META-INF/versions/09/sample/Entry.class")) {
            assertFalse(NeiReferenceCapture.matchesJarClassResource(jarEntry(marked, invalid), "sample/Entry.class"));
        }
        assertFalse(NeiReferenceCapture.matchesJarClassResource(jarEntry(unmarked,
            "META-INF/versions/17/sample/Entry.class"), "sample/Entry.class"));
    }

    private JarURLConnection jarEntry(Path jar, String entry) throws Exception {
        return (JarURLConnection) new URL("jar:" + jar.toUri().toURL() + "!/" + entry).openConnection();
    }

    private void versionedJar(Path jar, boolean multiRelease) throws Exception {
        Manifest manifest = new Manifest();
        manifest.getMainAttributes().putValue("Manifest-Version", "1.0");
        if (multiRelease) manifest.getMainAttributes().putValue("Multi-Release", "true");
        try (JarOutputStream output = new JarOutputStream(Files.newOutputStream(jar), manifest)) {
            for (String entry : Arrays.asList("sample/Entry.class", "META-INF/versions/17/sample/Entry.class",
                "META-INF/versions/17/other/Entry.class", "prefix/META-INF/versions/17/sample/Entry.class",
                "META-INF/versions/8/sample/Entry.class", "META-INF/versions/09/sample/Entry.class")) {
                output.putNextEntry(new JarEntry(entry));
                output.write(0);
                output.closeEntry();
            }
        }
    }

    @Test
    public void inventoryReportsRosterMutationAndReplacementWithoutReenumeratingHandlers() throws Exception {
        for (boolean replace : new boolean[] {false, true}) {
            Object handler = new OpaqueCraftHandler();
            List<List<?>> rosters = new ArrayList<>(Arrays.asList(new ArrayList<>(Arrays.asList(handler)),
                new ArrayList<>(), new ArrayList<>(), new ArrayList<>()));
            int[] reads = {0};
            Path output = temporary.getRoot().toPath().resolve(replace ? "replaced" : "mutated");
            NeiReferenceCapture.captureInventory(output, inventoryManifest(), () -> {
                if (++reads[0] == 2) {
                    if (replace) rosters.set(0, new ArrayList<>(Arrays.asList(handler)));
                    else rosters.get(0).clear();
                }
                return rosters;
            });
            JsonObject summary = SnapshotWriter.JSON.fromJson(new String(Files.readAllBytes(output.resolve("summary.json")),
                StandardCharsets.UTF_8), JsonObject.class);
            assertEquals(1, summary.getAsJsonObject("counts").get("handlers").getAsInt());
            assertEquals(replace, summary.getAsJsonObject("rosters").get("stable").getAsBoolean());
            assertEquals(!replace, summary.getAsJsonObject("rosters").get("references_unchanged").getAsBoolean());
            assertFalse(summary.get("complete").getAsBoolean());
            assertEquals(2, reads[0]);
        }
    }

    private static final class OpaqueCraftHandler extends OpaqueUsageHandler implements ICraftingHandler {
        @Override public ICraftingHandler getRecipeHandler(String id, Object... results) { throw new AssertionError(); }
    }

    private static class OpaqueUsageHandler implements IUsageHandler {
        @Override public String getHandlerId() { throw new AssertionError(); }
        @Override public String getRecipeName() { throw new AssertionError(); }
        @Override public int numRecipes() { throw new AssertionError(); }
        @Override public void drawBackground(int recipe) { throw new AssertionError(); }
        @Override public void drawForeground(int recipe) { throw new AssertionError(); }
        @Override public List<codechicken.nei.PositionedStack> getIngredientStacks(int recipe) { throw new AssertionError(); }
        @Override public List<codechicken.nei.PositionedStack> getOtherStacks(int recipe) { throw new AssertionError(); }
        @Override public codechicken.nei.PositionedStack getResultStack(int recipe) { throw new AssertionError(); }
        @Override public void onUpdate() { throw new AssertionError(); }
        @Override public boolean hasOverlay(net.minecraft.client.gui.inventory.GuiContainer gui,
            net.minecraft.inventory.Container container, int recipe) { throw new AssertionError(); }
        @Override public codechicken.nei.api.IRecipeOverlayRenderer getOverlayRenderer(
            net.minecraft.client.gui.inventory.GuiContainer gui, int recipe) { throw new AssertionError(); }
        @Override public codechicken.nei.api.IOverlayHandler getOverlayHandler(
            net.minecraft.client.gui.inventory.GuiContainer gui, int recipe) { throw new AssertionError(); }
        @Override public List<String> handleTooltip(codechicken.nei.recipe.GuiRecipe<?> gui,
            List<String> tooltip, int recipe) { throw new AssertionError(); }
        @Override public List<String> handleItemTooltip(codechicken.nei.recipe.GuiRecipe<?> gui,
            net.minecraft.item.ItemStack stack, List<String> tooltip, int recipe) { throw new AssertionError(); }
        @Override public boolean keyTyped(codechicken.nei.recipe.GuiRecipe<?> gui,
            char character, int code, int recipe) { throw new AssertionError(); }
        @Override public boolean mouseClicked(codechicken.nei.recipe.GuiRecipe<?> gui,
            int button, int recipe) { throw new AssertionError(); }
        @Override public IUsageHandler getUsageHandler(String id, Object... ingredients) { throw new AssertionError(); }
        @Override public int hashCode() { throw new AssertionError("handler hashCode called"); }
        @Override public boolean equals(Object other) { throw new AssertionError("handler equals called"); }
        @Override public String toString() { throw new AssertionError("handler toString called"); }
    }

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
