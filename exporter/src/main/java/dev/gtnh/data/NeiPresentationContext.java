package dev.gtnh.data;

import static dev.gtnh.data.Jsons.object;

import codechicken.nei.ItemList;
import codechicken.nei.NEIClientConfig;
import codechicken.nei.api.IStackStringifyHandler;
import codechicken.nei.recipe.StackInfo;
import codechicken.nei.util.NBTJson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.common.collect.ListMultimap;
import gregtech.api.util.GTOreDictUnificator;
import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.Arrays;
import java.util.ArrayList;
import java.util.AbstractMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Consumer;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.nbt.NBTBase;
import net.minecraft.nbt.NBTTagCompound;
import net.minecraftforge.oredict.OreDictionary;

/** Captures independent native presentation facts for persisted recipe declarations. */
final class NeiPresentationContext {
    private static final List<String> GT_FAMILIES = Arrays.asList(
        "gregtech:gt.recipe.alloysmelter", "gregtech:gt.recipe.metalbender",
        "gregtech:gt.recipe.macerator", "gregtech:gt.recipe.orewasher",
        "gregtech:gt.recipe.fluidsolidifier");
    private static final String FURNACE_FAMILY = "minecraft:smelting";
    private static final List<String> SUPPLEMENTARY_FAMILIES = Arrays.asList("botania:mana_infusion");
    private static final String DEFAULT_SERIALIZER = "codechicken.nei.recipe.stackinfo.DefaultStackStringifyHandler";
    private final Map<String, JsonObject> resources = new LinkedHashMap<>();
    private final Map<String, JsonObject> projectionItems = new LinkedHashMap<>();
    private final Set<String> projectionBuckets = new LinkedHashSet<>();
    private final Set<String> aliases = new LinkedHashSet<>();
    private final Set<String> poolOwners = new LinkedHashSet<>();
    private final JsonArray failures = new JsonArray();
    private long failedRows;

    private NeiPresentationContext() {}

    /** Requires closed canonical streams and their declarations, before any handler enumeration. */
    static JsonObject capture(Path directory, JsonObject manifest) throws IOException {
        NeiPresentationContext context = new NeiPresentationContext();
        Path canonical = directory.getParent();
        JsonObject declarations = new JsonObject();
        for (String stream : Arrays.asList("resources", "processes")) {
            String filename = stream + ".jsonl.gz";
            JsonObject files = manifest.getAsJsonObject("files");
            if (files == null || !files.has(filename))
                throw new IOException("Missing canonical declaration: " + filename);
            declarations.add(filename, files.get(filename));
        }
        context.readCanonical(canonical, declarations);
        JsonObject start = readiness();
        boolean ready = ready(start);
        ListMultimap<Item, ItemStack> pools = ItemList.itemMap;
        List<String> serializers = serializerClasses();
        Set<String> emptyPools = new LinkedHashSet<>();
        long aliasCount = 0;
        long poolCount = 0;
        try (BufferedWriter aliasWriter = writer(directory.resolve("gt-display-aliases.jsonl.gz"));
             BufferedWriter poolWriter = writer(directory.resolve("item-pools.jsonl.gz"))) {
            for (String id : context.aliases) {
                JsonObject row = object("resource_id", id, "status", "failed", "alternatives", new JsonArray(), "failure", null);
                try {
                    if (!ready) throw new IllegalStateException("NEI presentation context is not ready");
                    ItemStack anchor = reconstruct(context.resources.get(id));
                    List<ItemStack> alternatives = GTOreDictUnificator.getNonUnifiedStacks(anchor.copy());
                    if (alternatives == null) throw new IllegalStateException("Native GT display aliases are null");
                    JsonArray encoded = new JsonArray();
                    for (ItemStack alternative : alternatives) {
                        JsonObject stack = serialize(alternative);
                        encoded.add(stack);
                        context.addPoolOwner(stack);
                        context.addProjection(stack);
                    }
                    row.add("alternatives", encoded);
                    row.addProperty("status", encoded.size() == 0 ? "empty" : "ok");
                } catch (RuntimeException | LinkageError failure) {
                    context.failedRows++;
                    row.add("failure", failure("gt_display_aliases", failure));
                }
                append(aliasWriter, row);
                aliasCount++;
            }
            for (String owner : context.poolOwners) {
                JsonObject row = object("registry_name", owner, "status", "failed", "entries", new JsonArray(), "failure", null);
                try {
                    if (!ready) throw new IllegalStateException("NEI presentation context is not ready");
                    Item item = (Item) Item.itemRegistry.getObject(owner);
                    if (item == null) throw new IllegalArgumentException("Unknown item pool registry owner: " + owner);
                    JsonArray encoded = new JsonArray();
                    for (ItemStack stack : pools.get(item)) {
                        JsonObject typed = serialize(stack);
                        encoded.add(typed);
                        context.addProjection(typed);
                    }
                    if (encoded.size() == 0) emptyPools.add(owner);
                    row.add("entries", encoded);
                    row.addProperty("status", encoded.size() == 0 ? "empty" : "ok");
                } catch (RuntimeException | LinkageError failure) {
                    context.failedRows++;
                    row.add("failure", failure("item_pool", failure));
                }
                append(poolWriter, row);
                poolCount++;
            }
        }
        // Empty wildcard pools produce metadata zero with the declaration's original tag.
        for (JsonObject identity : new ArrayList<>(context.projectionItems.values())) {
            if (identity.get("metadata").getAsInt() == OreDictionary.WILDCARD_VALUE
                && emptyPools.contains(identity.get("registry_name").getAsString())) {
                JsonObject fallback = object("registry_name", identity.get("registry_name"), "metadata", 0, "nbt", identity.get("nbt"));
                context.addProjection(fallback);
            }
        }
        // Include other captured typed variants that could collide with scoped presentation identities.
        for (JsonObject resource : context.resources.values()) {
            if ("item".equals(resource.get("kind").getAsString()) && context.projectionBuckets.contains(bucket(resource)))
                context.addProjection(resource);
        }
        long projectionCount = 0;
        try (BufferedWriter projectionWriter = writer(directory.resolve("item-projections.jsonl.gz"))) {
            for (JsonObject identity : context.projectionItems.values()) {
                JsonObject row;
                try {
                    if (!ready) throw new IllegalStateException("NEI presentation context is not ready");
                    row = itemProjection(reconstruct(identity));
                    row.add("nbt", identity.get("nbt"));
                } catch (RuntimeException | LinkageError failure) {
                    row = object("registry_name", identity.get("registry_name"), "metadata", identity.get("metadata"),
                        "nbt", identity.get("nbt"), "status", "failed", "native_stack", null,
                        "serializer_class", null, "count_semantics", "unknown", "failure", failure("item_projection", failure));
                    context.failedRows++;
                }
                append(projectionWriter, row);
                projectionCount++;
            }
        }
        JsonObject end = readiness();
        end.addProperty("item_pool_unchanged", pools == ItemList.itemMap);
        end.addProperty("serializer_registry_unchanged", serializers.equals(serializerClasses()));
        boolean complete = ready && ready(end) && pools == ItemList.itemMap
            && end.get("serializer_registry_unchanged").getAsBoolean()
            && context.failedRows == 0 && context.failures.size() == 0;
        JsonObject files = object(
            "gt-display-aliases.jsonl.gz", object("records", aliasCount,
                "sha256", SnapshotWriter.sha256(directory.resolve("gt-display-aliases.jsonl.gz"))),
            "item-pools.jsonl.gz", object("records", poolCount,
                "sha256", SnapshotWriter.sha256(directory.resolve("item-pools.jsonl.gz"))),
            "item-projections.jsonl.gz", object("records", projectionCount,
                "sha256", SnapshotWriter.sha256(directory.resolve("item-projections.jsonl.gz"))));
        JsonObject summary = object("schema_version", 3, "canonical_snapshot_id", manifest.get("snapshot_id"),
            "canonical_pack", manifest.get("pack"), "canonical_files", declarations,
            "scope", object("gt_families", GT_FAMILIES, "furnace_family", FURNACE_FAMILY, "alias_template_amount", 1,
                "supplementary_families", SUPPLEMENTARY_FAMILIES),
            "readiness", object("start", start, "end", end), "complete", complete,
            "failed_rows", context.failedRows, "failures", context.failures, "files", files);
        summary.add("item_projection", object("api", "StackInfo.stackStringifyHandlers.reverse.convertItemStackToNBT(stack,true)->NBTJson.toJsonObject",
            "template_item_amount", 1, "classification", "selected_pinned_default_item_count", "serializer_classes", serializers));
        Path temporary = directory.resolve("presentation-context.json.tmp");
        Files.write(temporary, SnapshotWriter.JSON.toJson(summary).getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE_NEW);
        Files.move(temporary, directory.resolve("presentation-context.json"), StandardCopyOption.ATOMIC_MOVE);
        return object("sha256", SnapshotWriter.sha256(directory.resolve("presentation-context.json")));
    }

    private void readCanonical(Path directory, JsonObject declarations) throws IOException {
        read(directory, "resources", declarations, resource -> {
            String id = resource.get("id").getAsString();
            if (resources.put(id, resource) != null) throw new IllegalArgumentException("Duplicate resource: " + id);
        });
        read(directory, "processes", declarations, process -> {
            String family = process.get("family").getAsString();
            boolean gt = GT_FAMILIES.contains(family);
            if (!gt && !FURNACE_FAMILY.equals(family) && !SUPPLEMENTARY_FAMILIES.contains(family)) return;
            for (JsonElement element : process.getAsJsonArray("inputs")) {
                JsonObject slot = element.getAsJsonObject();
                for (JsonElement choice : slot.getAsJsonArray("choices"))
                    declaration(choice.getAsJsonObject(), process, slot, gt);
            }
            for (JsonElement output : process.getAsJsonArray("outputs"))
                declaration(output.getAsJsonObject(), process, null, gt);
        });
    }

    private void declaration(JsonObject stack, JsonObject process, JsonObject slot, boolean gt) {
        JsonElement resourceId = stack.get("resource_id");
        if (resourceId == null || resourceId.isJsonNull()) {
            failures.add(object("phase", "canonical_anchor", "process_id", process.get("id"),
                "native_slot", slot == null ? null : slot.get("native_slot"), "native_item", stack.get("native_item"),
                "message", "Canonical declaration has no registered resource identity"));
            return;
        }
        String id = resourceId.getAsString();
        JsonObject resource = resources.get(id);
        if (resource == null) throw new IllegalArgumentException("Unknown declared resource: " + id);
        if (!"item".equals(resource.get("kind").getAsString())) return;
        addProjection(resource);
        if (gt) aliases.add(id);
        addPoolOwner(resource);
    }

    private void addPoolOwner(JsonObject stack) {
        if (stack.get("metadata").getAsInt() == OreDictionary.WILDCARD_VALUE)
            poolOwners.add(stack.get("registry_name").getAsString());
    }

    private static String bucket(JsonObject stack) {
        return SnapshotWriter.JSON.toJson(object("registry_name", stack.get("registry_name"), "metadata", stack.get("metadata")));
    }

    private void addProjection(JsonObject stack) {
        JsonObject identity = object("registry_name", stack.get("registry_name"), "metadata", stack.get("metadata"), "nbt", stack.get("nbt"));
        projectionItems.putIfAbsent(SnapshotWriter.JSON.toJson(identity), identity);
        projectionBuckets.add(bucket(stack));
    }

    private static List<String> serializerClasses() {
        List<String> classes = new ArrayList<>();
        for (IStackStringifyHandler handler : StackInfo.stackStringifyHandlers) classes.add(handler.getClass().getName());
        return classes;
    }

    /** Same live reverse dispatch as the pinned StackInfo API, with the selected handler retained. */
    static Map.Entry<IStackStringifyHandler, NBTTagCompound> dispatchItem(ItemStack stack, boolean saveStackSize,
        List<IStackStringifyHandler> handlers) {
        for (int index = handlers.size() - 1; index >= 0; index--) {
            IStackStringifyHandler handler = handlers.get(index);
            NBTTagCompound serialized = handler.convertItemStackToNBT(stack, saveStackSize);
            if (serialized != null) return new AbstractMap.SimpleImmutableEntry<>(handler, serialized);
        }
        return null;
    }

    private static JsonObject itemProjection(ItemStack original) {
        JsonObject typed = serialize(original);
        ItemStack template = original.copy();
        template.stackSize = 1;
        Map.Entry<IStackStringifyHandler, NBTTagCompound> selected = dispatchItem(template, true, StackInfo.stackStringifyHandlers);
        if (selected == null) throw new IllegalStateException("Native item serializer returned null");
        NBTTagCompound serialized = selected.getValue();
        String serializer = selected.getKey().getClass().getName();
        String semantics = itemCountSemantics(typed, serialized, serializer);
        return object("registry_name", typed.get("registry_name"), "metadata", typed.get("metadata"), "nbt", typed.get("nbt"),
            "status", "ok", "native_stack", NBTJson.toJsonObject(serialized),
            "serializer_class", serializer,
            "count_semantics", semantics, "failure", null);
    }

    static String itemCountSemantics(JsonObject typed, NBTTagCompound serialized, String selectedSerializer) {
        boolean ordinary = DEFAULT_SERIALIZER.equals(selectedSerializer) && serialized.hasKey("strId", 8)
            && serialized.hasKey("Damage", 3) && serialized.hasKey("Count", 3)
            && serialized.getString("strId").equals(typed.get("registry_name").getAsString())
            && serialized.getInteger("Damage") == typed.get("metadata").getAsInt() && serialized.getInteger("Count") == 1
            && (!serialized.hasKey("tag") || serialized.hasKey("tag", 10));
        @SuppressWarnings("unchecked") Set<String> keys = serialized.func_150296_c();
        ordinary &= Arrays.asList("strId", "Damage", "Count", "tag").containsAll(keys);
        return ordinary ? "item_stack_size" : serialized.hasKey("neiFluidName") ? "native_conversion" : "unknown";
    }

    private static void read(Path directory, String stream, JsonObject declarations, Consumer<JsonObject> consumer)
        throws IOException {
        String filename = stream + ".jsonl.gz";
        JsonObject declaration = declarations.getAsJsonObject(filename);
        if (!declaration.has("sha256") || !declaration.has("records"))
            throw new IOException("Incomplete canonical declaration: " + filename);
        Path path = directory.resolve(filename);
        if (!SnapshotWriter.sha256(path).equals(declaration.get("sha256").getAsString()))
            throw new IOException(filename + " checksum does not match the canonical declaration");
        long count = 0;
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(
            new GZIPInputStream(Files.newInputStream(path)), StandardCharsets.UTF_8))) {
            String line;
            JsonParser parser = new JsonParser();
            while ((line = reader.readLine()) != null) {
                consumer.accept(parser.parse(line).getAsJsonObject());
                count++;
            }
        } catch (RuntimeException failure) {
            throw new IOException("Cannot read canonical " + filename, failure);
        }
        if (count != declaration.get("records").getAsLong())
            throw new IOException(filename + " record count does not match the canonical declaration");
    }

    private static ItemStack reconstruct(JsonObject resource) {
        String registryName = resource.get("registry_name").getAsString();
        Item item = (Item) Item.itemRegistry.getObject(registryName);
        if (item == null) throw new IllegalArgumentException("Unknown canonical item: " + registryName);
        ItemStack stack = new ItemStack(item, 1, resource.get("metadata").getAsInt());
        NBTBase nbt = TypedNbt.decode(resource.get("nbt"));
        if (nbt != null && !(nbt instanceof NBTTagCompound))
            throw new IllegalArgumentException("Canonical item NBT must be null or a typed compound");
        stack.setTagCompound((NBTTagCompound) nbt);
        return stack;
    }

    private static JsonObject serialize(ItemStack original) {
        if (original == null || original.getItem() == null)
            throw new IllegalArgumentException("Native presentation stack has no item");
        ItemStack stack = original.copy();
        String name = Item.itemRegistry.getNameForObject(stack.getItem());
        if (name == null) throw new IllegalArgumentException("Native presentation item is unregistered: " + stack.getItem().getClass().getName());
        return object("registry_name", name, "metadata", stack.getItemDamage(),
            "nbt", TypedNbt.encode(stack.getTagCompound()), "amount", stack.stackSize);
    }

    private static JsonObject readiness() {
        return object("nei_loaded", NEIClientConfig.isLoaded(), "item_list_load_finished", ItemList.loadFinished);
    }

    private static boolean ready(JsonObject readiness) {
        return readiness.get("nei_loaded").getAsBoolean() && readiness.get("item_list_load_finished").getAsBoolean();
    }

    private static JsonObject failure(String phase, Throwable failure) {
        return object("phase", phase, "class", failure.getClass().getName(), "message", failure.getMessage());
    }

    private static BufferedWriter writer(Path path) throws IOException {
        return new BufferedWriter(new OutputStreamWriter(new GZIPOutputStream(
            Files.newOutputStream(path, StandardOpenOption.CREATE_NEW)), StandardCharsets.UTF_8));
    }

    private static void append(BufferedWriter writer, JsonObject row) throws IOException {
        writer.write(SnapshotWriter.JSON.toJson(row));
        writer.newLine();
    }
}
