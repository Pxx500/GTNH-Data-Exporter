package dev.gtnh.data;

import static org.junit.Assert.*;

import com.google.gson.JsonObject;
import com.google.gson.JsonArray;
import codechicken.nei.util.NBTJson;
import codechicken.nei.api.IStackStringifyHandler;
import codechicken.nei.recipe.stackinfo.DefaultStackStringifyHandler;
import java.util.Arrays;
import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraft.nbt.NBTTagDouble;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.Test;

public final class NeiPresentationContextTest {
    @Test
    public void usesThePinnedNativeJavaDoubleProjection() {
        assertEquals("1.0E7D", NBTJson.toJsonObject(new NBTTagDouble(10000000)).getAsString());
    }

    @Test
    public void classifiesOnlySourceProvenOrdinaryItemCounts() {
        String defaultClass = "codechicken.nei.recipe.stackinfo.DefaultStackStringifyHandler";
        JsonObject typed = Jsons.object("registry_name", "test:input", "metadata", 3, "nbt", null);
        NBTTagCompound nativeStack = new NBTTagCompound();
        nativeStack.setString("strId", "test:input");
        nativeStack.setInteger("Damage", 3);
        nativeStack.setInteger("Count", 1);
        assertEquals("item_stack_size", NeiPresentationContext.itemCountSemantics(typed, nativeStack, defaultClass));
        assertEquals("unknown", NeiPresentationContext.itemCountSemantics(typed, nativeStack, "com.gtnewhorizons.aspectrecipeindex.nei.TCAspectStringifyHandler"));
        assertEquals("unknown", NeiPresentationContext.itemCountSemantics(typed, nativeStack, "codechicken.enderstorage.internal.StorageStackStringifyHandler"));
        nativeStack.setInteger("Count", 77);
        assertEquals("unknown", NeiPresentationContext.itemCountSemantics(typed, nativeStack, defaultClass));
        nativeStack = new NBTTagCompound();
        nativeStack.setString("neiFluidName", "water");
        nativeStack.setLong("Count", 1000);
        assertEquals("native_conversion", NeiPresentationContext.itemCountSemantics(typed, nativeStack, "custom.FluidSerializer"));
    }

    private IStackStringifyHandler handler(List<String> calls, String name, NBTTagCompound result) {
        return new DefaultStackStringifyHandler() {
            @Override
            public NBTTagCompound convertItemStackToNBT(ItemStack stack, boolean saveStackSize) {
                assertNull(stack);
                assertTrue(saveStackSize);
                calls.add(name);
                return result;
            }
        };
    }

    @Test
    public void dispatchPreservesReverseOrderAndStopsAtTheFirstNonnullPayload() {
        List<String> calls = new ArrayList<>();
        NBTTagCompound payload = new NBTTagCompound();
        IStackStringifyHandler winner = handler(calls, "winner", payload);
        List<IStackStringifyHandler> five = Arrays.asList(handler(calls, "unreached", payload), winner,
            handler(calls, "fluid", null), handler(calls, "aspects", null), handler(calls, "storage", null));
        Map.Entry<IStackStringifyHandler, NBTTagCompound> selected = NeiPresentationContext.dispatchItem(null, true, five);
        assertSame(winner, selected.getKey());
        assertSame(payload, selected.getValue());
        assertEquals(Arrays.asList("storage", "aspects", "fluid", "winner"), calls);
        calls.clear();
        assertNull(NeiPresentationContext.dispatchItem(null, true, Arrays.asList(handler(calls, "first", null), handler(calls, "second", null))));
        assertEquals(Arrays.asList("second", "first"), calls);
    }

    @Test
    public void dispatchPropagatesHandlerExceptionsWithoutCallingEarlierHandlers() {
        List<String> calls = new ArrayList<>();
        RuntimeException failure = new IllegalStateException("native failure");
        IStackStringifyHandler failing = new DefaultStackStringifyHandler() {
            @Override
            public NBTTagCompound convertItemStackToNBT(ItemStack stack, boolean saveStackSize) { throw failure; }
        };
        RuntimeException actual = assertThrows(RuntimeException.class, () -> NeiPresentationContext.dispatchItem(null, true,
            Arrays.asList(handler(calls, "unreached", new NBTTagCompound()), failing)));
        assertSame(failure, actual);
        assertTrue(calls.isEmpty());
    }

    @Test
    public void validatesSupplementaryBotaniaInputAndOutputDeclarationsBeforeNativeQueries() throws Exception {
        for (boolean input : new boolean[]{true, false}) {
            Path snapshot = Files.createTempDirectory("nei-botania-declarations").resolve("snapshot");
            JsonObject manifest = Jsons.object("snapshot_id", "botania-context-test", "pack", Jsons.object());
            JsonArray inputs = new JsonArray();
            JsonArray outputs = new JsonArray();
            if (input) inputs.add(Jsons.object("choices", Jsons.array(Jsons.object("resource_id", "missing-input"))));
            else outputs.add(Jsons.object("resource_id", "missing-output"));
            try (SnapshotWriter writer = new SnapshotWriter(snapshot)) {
                writer.append("processes", Jsons.object("id", "botania", "family", "botania:mana_infusion", "inputs", inputs, "outputs", outputs));
                writer.publish(manifest);
            }
            Path reference = Files.createDirectory(snapshot.resolve("nei-reference"));
            IOException failure = assertThrows(IOException.class, () -> NeiPresentationContext.capture(reference, manifest));
            assertTrue(failure.getCause().getMessage().contains(input ? "missing-input" : "missing-output"));
            assertFalse(Files.exists(reference.resolve("presentation-context.json")));
        }
    }

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
