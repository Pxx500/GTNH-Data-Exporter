package dev.gtnh.data;

import static dev.gtnh.data.Jsons.object;

import codechicken.nei.ItemList;
import codechicken.nei.NEIClientConfig;
import codechicken.nei.PositionedStack;
import codechicken.nei.recipe.GuiCraftingRecipe;
import codechicken.nei.recipe.ICraftingHandler;
import codechicken.nei.recipe.Recipe;
import codechicken.nei.recipe.StackInfo;
import codechicken.nei.recipe.TemplateRecipeHandler;
import codechicken.nei.util.NBTJson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import gregtech.api.recipe.RecipeMap;
import gregtech.nei.GTNEIDefaultHandler;
import java.io.BufferedWriter;
import java.io.Closeable;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.GZIPOutputStream;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTTagCompound;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/** Client-side NEI presentation evidence, independent of canonical resource serialization. */
final class NeiReferenceCapture implements Closeable {
    private static final Logger LOG = LogManager.getLogger("GTNHDataExporter");
    private static final String[] STREAMS = {"handlers", "signatures", "handler-views"};
    private final Path directory;
    private final Map<String, BufferedWriter> streams = new LinkedHashMap<>();
    private final Map<String, Long> counts = new LinkedHashMap<>();
    private long failedHandlers;
    private long emptyHandlers;
    private long failedSignatures;
    private long failedViews;
    private long failedStacks;
    private JsonObject presentationContext;
    private boolean closed;

    private NeiReferenceCapture(Path directory) throws IOException {
        this.directory = directory;
        Files.createDirectory(directory);
        try {
            for (String name : STREAMS) {
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

    static boolean isReady() { return NEIClientConfig.isLoaded() && ItemList.loadFinished; }

    /** Must run on the client thread after native NEI readiness gates. */
    static void capture(Path directory, JsonObject manifest) throws IOException {
        if (!isReady()) throw new IllegalStateException("NEI reference capture requested before NEI/item readiness");
        try (NeiReferenceCapture reference = new NeiReferenceCapture(directory)) {
            reference.presentationContext = NeiPresentationContext.capture(directory, manifest);
            List<ICraftingHandler> handlers = new ArrayList<>(GuiCraftingRecipe.craftinghandlers);
            int parallelCount = handlers.size();
            handlers.addAll(new ArrayList<>(GuiCraftingRecipe.serialCraftingHandlers));
            for (int index = 0; index < handlers.size(); index++) {
                reference.handler(handlers.get(index), "h" + index,
                    index < parallelCount ? "craftinghandlers" : "serialCraftingHandlers");
            }
            reference.publish(manifest);
        }
    }

    private void handler(ICraftingHandler original, String key, String registration) throws IOException {
        LOG.info("NEI reference enumerates {} from {} ({})", key, registration, original.getClass().getName());
        JsonObject record = object("handler_key", key, "native_class", original.getClass().getName(),
            "handler_id", null, "handler_name", null, "gt_recipe_map_id", null,
            "registration", registration, "enumeration_status", "failed", "recipe_count", null, "failure", null);
        ICraftingHandler handler;
        int size;
        try {
            record.addProperty("handler_id", original.getHandlerId());
            record.addProperty("handler_name", original.getRecipeName());
            handler = original instanceof TemplateRecipeHandler
                ? ((TemplateRecipeHandler) original).getAllRecipeHandler() : original.getRecipeHandler("all");
            if (handler == null) throw new IllegalStateException("Native all-recipes query returned null");
            record.addProperty("queried_native_class", handler.getClass().getName());
            if (handler.getClass() == GTNEIDefaultHandler.class) {
                record.addProperty("gt_recipe_map_id", "gregtech:" + ((GTNEIDefaultHandler) handler).getRecipeMap().unlocalizedName);
            }
            record.add("getter_declaring_classes", object(
                "ingredients", handler.getClass().getMethod("getIngredientStacks", int.class).getDeclaringClass().getName(),
                "result", handler.getClass().getMethod("getResultStack", int.class).getDeclaringClass().getName(),
                "other_stacks", handler.getClass().getMethod("getOtherStacks", int.class).getDeclaringClass().getName()));
            size = handler.numRecipes();
            if (size < 0) throw new IllegalStateException("Native handler returned negative recipe count");
            record.addProperty("recipe_count", size);
            record.addProperty("enumeration_status", size == 0 ? "empty" : "ok");
            if (size == 0) emptyHandlers++;
        } catch (Exception | LinkageError failure) {
            failedHandlers++;
            record.add("failure", failure("handler_enumeration", failure));
            append("handlers", record);
            return;
        }
        append("handlers", record);
        for (int index = 0; index < size; index++) {
            signature(handler, key, index);
            view(handler, key, index);
        }
    }

    private void signature(ICraftingHandler handler, String key, int index) throws IOException {
        JsonObject record = object("handler_key", key, "recipe_index", index,
            "projection", "native_recipe_id_api", "signature", null, "failure", null);
        try { record.add("signature", Recipe.of(handler, index).getRecipeId().toJsonObject()); }
        catch (RuntimeException | LinkageError error) {
            failedSignatures++;
            record.add("failure", failure("native_recipe_id_api", error));
        }
        append("signatures", record);
    }

    private void view(ICraftingHandler handler, String key, int index) throws IOException {
        JsonObject record = object("handler_key", key, "recipe_index", index,
            "ingredients", null, "result", null, "other_stacks", null, "displayed_fields", null, "failure", null);
        JsonArray failures = new JsonArray();
        boolean mapped = handler.getClass() == GTNEIDefaultHandler.class;
        try { record.add("ingredients", positionedList(handler.getIngredientStacks(index), mapped)); }
        catch (RuntimeException | LinkageError error) { failures.add(failure("ingredients", error)); }
        try { record.add("result", positioned(handler.getResultStack(index), mapped)); }
        catch (RuntimeException | LinkageError error) { failures.add(failure("result", error)); }
        try { record.add("other_stacks", positionedList(handler.getOtherStacks(index), mapped)); }
        catch (RuntimeException | LinkageError error) { failures.add(failure("other_stacks", error)); }
        try {
            JsonObject displayed = object("recipe_height", handler.getRecipeHeight(index),
                "recipe_tab_name", handler.getRecipeTabName(), "overlay_identifier", handler.getOverlayIdentifier());
            if (mapped) {
                RecipeMap<?> map = ((GTNEIDefaultHandler) handler).getRecipeMap();
                displayed.addProperty("frontend_class", map.getFrontend().getClass().getName());
                displayed.addProperty("render_real_stack_sizes", map.getFrontend().getNEIProperties().renderRealStackSizes);
                displayed.addProperty("unificate_output", map.getFrontend().getNEIProperties().unificateOutput);
            }
            record.add("displayed_fields", displayed);
        } catch (RuntimeException | LinkageError error) { failures.add(failure("displayed_fields", error)); }
        if (failures.size() != 0) {
            failedViews++;
            record.add("failure", failures.get(0));
        }
        record.add("failures", failures);
        append("handler-views", record);
    }

    private JsonArray positionedList(List<PositionedStack> stacks, boolean mapped) {
        if (stacks == null) throw new IllegalStateException("Native positioned-stack list is null");
        JsonArray result = new JsonArray();
        for (PositionedStack stack : stacks) result.add(positioned(stack, mapped));
        return result;
    }

    private JsonElement positioned(PositionedStack stack, boolean mapped) {
        if (stack == null) return JsonNull.INSTANCE;
        JsonObject result = object("x", stack.relx, "y", stack.rely, "native_class", stack.getClass().getName(),
            "chance", stack.getChance(), "chance_semantics", "native_presentation_default_may_be_full",
            "real_stack_size", null, "alternatives", null);
        if (mapped && stack instanceof GTNEIDefaultHandler.FixedPositionedStack) {
            result.addProperty("real_stack_size", ((GTNEIDefaultHandler.FixedPositionedStack) stack).realStackSize);
        }
        if (stack.items == null) throw new IllegalStateException("Native positioned-stack alternatives are null");
        JsonArray alternatives = new JsonArray();
        for (ItemStack item : stack.items) {
            JsonObject alternative = object("native_stack", null, "failure", null);
            if (item != null) {
                try {
                    NBTTagCompound nativeNbt = StackInfo.itemStackToNBT(item);
                    if (nativeNbt == null) throw new IllegalStateException("NEI StackInfo serializer returned null");
                    alternative.add("native_stack", NBTJson.toJsonObject(nativeNbt));
                } catch (RuntimeException | LinkageError error) {
                    failedStacks++;
                    alternative.add("failure", failure("native_stack", error));
                }
            }
            alternatives.add(alternative);
        }
        result.add("alternatives", alternatives);
        return result;
    }

    private JsonObject failure(String phase, Throwable error) {
        LOG.warn("NEI reference {} failed: {}", phase, error.toString());
        return object("phase", phase, "class", error.getClass().getName(), "message", error.getMessage());
    }

    private void append(String stream, JsonObject record) throws IOException {
        BufferedWriter target = streams.get(stream);
        target.write(SnapshotWriter.JSON.toJson(record));
        target.newLine();
        counts.put(stream, counts.get(stream) + 1L);
    }

    private void publish(JsonObject manifest) throws IOException {
        close();
        JsonObject files = new JsonObject();
        for (String name : STREAMS) {
            String filename = name + ".jsonl.gz";
            files.add(filename, object("records", counts.get(name), "sha256", SnapshotWriter.sha256(directory.resolve(filename))));
        }
        files.add("presentation-context.json", presentationContext);
        JsonObject summary = object("schema_version", 1, "canonical_snapshot_id", manifest.get("snapshot_id"),
            "canonical_pack", manifest.get("pack"), "created_at", Instant.now().toString(),
            "counts", object("handlers", counts.get("handlers"), "signatures", counts.get("signatures"),
                "handler_views", counts.get("handler-views")),
            "complete", failedHandlers + failedSignatures + failedViews + failedStacks == 0,
            "scope", "registered crafting and serial crafting all-recipes queries, not all pack recipes",
            "signature_projection", "native_recipe_id_api", "view_projection", "raw_handler_view",
            "recipeid_blacklist_applied", false, "skipped_handlers", 0, "empty_handlers", emptyHandlers,
            "readiness", object("nei_loaded", true, "item_list_load_finished", true,
                "canonical_capture_after_nei_ready", true),
            "settings", object("config_digest_source", "canonical_pack.config_script_digests",
                "native_handler_filters", "uninterpreted", "recipeid_blacklist_applied", false),
            "failed_handlers", failedHandlers, "failed_signatures", failedSignatures, "failed_views", failedViews,
            "failed_stacks", failedStacks, "chance_semantics", "native_presentation_default_may_be_full",
            "nbt_semantics", "verbatim NEI NBTJson projection, not typed canonical NBT", "files", files);
        JsonElement nei = JsonNull.INSTANCE;
        for (JsonElement mod : manifest.getAsJsonObject("pack").getAsJsonArray("mods")) {
            if ("NotEnoughItems".equalsIgnoreCase(mod.getAsJsonObject().get("id").getAsString())) nei = mod;
        }
        summary.add("native_nei", nei);
        Path temporary = directory.resolve("summary.json.tmp");
        Files.write(temporary, SnapshotWriter.JSON.toJson(summary).getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE_NEW);
        Files.move(temporary, directory.resolve("summary.json"), StandardCopyOption.ATOMIC_MOVE);
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
