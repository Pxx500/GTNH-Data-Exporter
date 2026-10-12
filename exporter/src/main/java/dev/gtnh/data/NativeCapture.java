package dev.gtnh.data;

import static dev.gtnh.data.Jsons.object;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import cpw.mods.fml.common.Loader;
import cpw.mods.fml.common.ModContainer;
import gregtech.api.enums.Materials;
import gregtech.api.recipe.RecipeMap;
import gregtech.api.recipe.RecipeMetadataKey;
import gregtech.api.util.GTOreDictUnificator;
import gregtech.api.util.GTRecipe;
import gregtech.api.util.recipe.Sievert;
import java.io.IOException;
import java.lang.reflect.Array;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import net.minecraft.item.ItemStack;
import net.minecraft.item.Item;
import net.minecraft.item.crafting.FurnaceRecipes;
import net.minecraft.util.StatCollector;
import net.minecraftforge.fluids.FluidStack;
import net.minecraftforge.oredict.OreDictionary;

/**
 * Independent canonical capture. The native crafting dispatch and GT registry enumeration
 * were adapted from MIT GtnhCalcOracleExporter, Copyright (c) 2026 Samiracle64:
 * https://github.com/Samiracle64/gtnh-factory-flow (tools/dataset-pipeline/gtnh-calc-oracle).
 * See exporter/THIRD_PARTY_NOTICES.md for the retained MIT notice.
 * Source algorithms from LGPL GT are called through public APIs, not copied.
 */
final class NativeCapture {
    private final SnapshotWriter writer;
    private final Map<String, String> resourceIds = new HashMap<>();
    private final Map<String, String> oreGroups = new HashMap<>();
    private final Map<String, String> unifiedGroups = new HashMap<>();
    private int processNumber;
    private int unknownMetadata;

    NativeCapture(SnapshotWriter writer) { this.writer = writer; }

    void capture() throws IOException {
        oreDictionary();
        gregTech();
        assemblyLine();
        new CraftingCapture(this).capture();
        smelting();
        new EnderIoCapture(this).capture();
        new ForestryCapture(this).capture();
        new WorldgenCapture(this, writer).capture();
        coverage("resources", "partial", writer.count("resources"),
            "Resources referenced by captured recipes, ore groups and acquisition definitions. Not an exhaustive NEI item catalog");
        coverage("recipe-semantics", "partial", writer.count("processes"),
            "Dynamic native matching, machine-specific metadata and custom crafting remain unresolved. Uninterpreted metadata: " + unknownMetadata);
        coverage("other-mod-recipes", "unsupported", 0,
            "Other non-GT machine recipes beyond bounded EnderIO and Forestry Centrifuge adapters remain unsupported");
        coverage("other-acquisition", "unsupported", 0,
            "Mob drops, trades, other-mod worldgen, mining drop distributions and saved deposits are not captured");
    }

    JsonObject manifest(Path gameDirectory, String worldName, long worldSeed) throws IOException {
        JsonArray mods = new JsonArray();
        Map<Path, String> hashes = new HashMap<>();
        for (ModContainer mod : Loader.instance().getModList()) {
            Path source = mod.getSource() == null ? null : mod.getSource().toPath();
            String digest = null;
            if (source != null && Files.isRegularFile(source)) {
                digest = hashes.get(source);
                if (digest == null) { digest = SnapshotWriter.sha256(source); hashes.put(source, digest); }
            }
            mods.add(object("id", mod.getModId(), "version", mod.getVersion(),
                "source", source == null ? null : source.getFileName().toString(), "sha256", digest));
        }
        JsonArray configs = new JsonArray();
        for (String folder : new String[]{"config", "scripts"}) {
            Path root = gameDirectory.resolve(folder);
            if (!Files.isDirectory(root)) continue;
            try (java.util.stream.Stream<Path> paths = Files.walk(root)) {
                java.util.Iterator<Path> files = paths.filter(Files::isRegularFile).sorted().iterator();
                while (files.hasNext()) {
                    Path file = files.next();
                    configs.add(object("path", gameDirectory.relativize(file).toString().replace('\\', '/'),
                        "sha256", SnapshotWriter.sha256(file)));
                }
            }
        }
        return object("schema_version", 1, "snapshot_id", UUID.randomUUID().toString(),
            "created_at", Instant.now().toString(),
            "capture", object("exporter_version", Tags.VERSION, "lifecycle", "integrated-world-server-tick-end",
                "load_complete", true, "server_started", true, "gt_first_world_tick_complete", true,
                "client_world_attached", true, "isolated_world", worldName,
                "world_seed", Long.toString(worldSeed), "images", false),
            "pack", object("mods", mods, "config_script_digests", configs,
                "context", "configured native registries, no observed deposit scan"));
    }

    String item(ItemStack stack) throws IOException {
        if (stack == null) return null;
        String name = Item.itemRegistry.getNameForObject(stack.getItem());
        if (name == null) throw new IllegalArgumentException("Unregistered native item: " + stack.getItem().getClass().getName());
        JsonElement nbt = TypedNbt.encode(stack.getTagCompound());
        return resource("item", name, stack.getItemDamage(), nbt, displayName(stack, name));
    }

    String fluid(FluidStack stack) throws IOException {
        if (stack == null) return null;
        return resource("fluid", stack.getFluid().getName(), null, TypedNbt.encode(stack.tag), stack.getLocalizedName());
    }

    private String resource(String kind, String registry, Integer damage, JsonElement nbt, String label) throws IOException {
        String key = kind + "|" + registry + "|" + damage + "|" + nbt;
        String id = resourceIds.get(key);
        if (id == null) {
            id = "r" + resourceIds.size();
            resourceIds.put(key, id);
            writer.append("resources", object("id", id, "kind", kind, "registry_name", registry,
                "metadata", damage, "nbt", nbt, "display_name", label,
                "provenance", object("owner", "native_registry")));
        }
        return id;
    }

    private String displayName(ItemStack stack, String registry) {
        try { return stack.getDisplayName(); }
        catch (RuntimeException error) { return registry; }
    }

    private void oreDictionary() throws IOException {
        List<String> names = new ArrayList<>();
        Collections.addAll(names, OreDictionary.getOreNames());
        Collections.sort(names);
        for (String name : names) {
            JsonArray members = new JsonArray();
            Set<String> seen = new HashSet<>();
            for (ItemStack stack : OreDictionary.getOres(name)) {
                String resource = item(stack);
                if (resource != null && seen.add(resource)) members.add(new com.google.gson.JsonPrimitive(resource));
            }
            String id = "ore:" + name;
            oreGroups.put(name, id);
            writer.append("groups", object("id", id, "kind", "ore_dict", "name", name, "members", members,
                "provenance", object("owner", "Forge OreDictionary")));
        }
        coverage("forge.ore_dictionary", "complete", names.size(), "Enumerated the live ore dictionary after world readiness");
    }

    private void gregTech() throws IOException {
        List<RecipeMap<?>> maps = new ArrayList<>(RecipeMap.ALL_RECIPE_MAPS.values());
        maps.sort(java.util.Comparator.comparing(map -> map.unlocalizedName));
        for (RecipeMap<?> map : maps) {
            long count = 0;
            for (GTRecipe recipe : new ArrayList<>(map.getAllRecipes())) {
                JsonArray inputs = new JsonArray();
                ItemStack[][] alternatives = recipe instanceof GTRecipe.GTRecipe_WithAlt
                    ? ((GTRecipe.GTRecipe_WithAlt) recipe).mOreDictAlt : null;
                int[] oreIds = recipe instanceof GTRecipe.GTRecipe_WithAlt
                    ? ((GTRecipe.GTRecipe_WithAlt) recipe).mOreDictIds : null;
                for (int index = 0; index < recipe.mInputs.length; index++) {
                    ItemStack base = recipe.mInputs[index];
                    if (base == null) continue;
                    ItemStack[] choices = alternatives != null && index < alternatives.length && alternatives[index] != null
                        ? alternatives[index] : new ItemStack[]{base};
                    int oreId = oreIds != null && index < oreIds.length ? oreIds[index] : -1;
                    boolean nativeNbtMatching = recipe.isNBTSensitive;
                    for (GTRecipe.RecipeItemInput nativeInput : recipe.getCachedCombinedItemInputs()) {
                        ItemStack representative = nativeInput.unifiedStack;
                        if (representative != null && representative.getItem() == base.getItem()
                            && representative.getItemDamage() == base.getItemDamage() && nativeInput.usesNbtMatching)
                            nativeNbtMatching = true;
                    }
                    JsonObject slot = itemSlot(choices, oreId, nativeNbtMatching, true);
                    slot.addProperty("native_slot", index);
                    slot.add("consumption_chance", chance(recipe.getInputChance(index)));
                    inputs.add(slot);
                }
                for (int index = 0; index < recipe.mFluidInputs.length; index++) {
                    FluidStack base = recipe.mFluidInputs[index];
                    if (base == null) continue;
                    FluidStack[] choices = recipe.mAltFluidInputs != null && index < recipe.mAltFluidInputs.length
                        && recipe.mAltFluidInputs[index] != null ? recipe.mAltFluidInputs[index] : new FluidStack[]{base};
                    JsonObject slot = fluidSlot(choices);
                    slot.add("consumption_chance", chance(recipe.getFluidInputChance(index)));
                    inputs.add(slot);
                }
                JsonArray outputs = new JsonArray();
                for (int index = 0; index < recipe.mOutputs.length; index++) {
                    if (recipe.mOutputs[index] != null) outputs.add(object("resource_id", item(recipe.mOutputs[index]),
                        "amount", recipe.mOutputs[index].stackSize, "chance", chance(recipe.getOutputChance(index))));
                }
                for (int index = 0; index < recipe.mFluidOutputs.length; index++) {
                    if (recipe.mFluidOutputs[index] != null) outputs.add(object("resource_id", fluid(recipe.mFluidOutputs[index]),
                        "amount", recipe.mFluidOutputs[index].amount, "chance", chance(recipe.getFluidOutputChance(index))));
                }
                JsonObject metadata = new JsonObject();
                for (Map.Entry<RecipeMetadataKey<?>, Object> entry : recipe.getMetadataStorage().getEntries()) {
                    metadata.add(entry.getKey().toString(), nativeValue(entry.getValue()));
                }
                JsonObject conditions = object("native_special_value", recipe.mSpecialValue, "native_metadata", metadata,
                    "nbt_sensitive", recipe.isNBTSensitive, "enabled", recipe.mEnabled, "hidden", recipe.mHidden,
                    "fake", recipe.mFakeRecipe, "requires_empty_outputs", recipe.mNeedsEmptyOutput,
                    "special_items", nativeValue(recipe.mSpecialItems), "native_description", recipe.getNeiDesc(),
                    "machine_behavior", "native_machine_conditions_not_fully_interpreted");
                emitProcess("gregtech:" + map.unlocalizedName, StatCollector.translateToLocal(map.unlocalizedName),
                    inputs, outputs, recipe.mDuration, recipe.mEUt, map.getAmperage(),
                    recipe.mEnabled && !recipe.mFakeRecipe, conditions,
                    object("owner", "GTRecipe", "map", map.unlocalizedName,
                        "map_class", map.getClass().getName(), "recipe_class", recipe.getClass().getName(), "index", count));
                count++;
            }
            coverage("gregtech.map:" + map.unlocalizedName, "partial", count,
                "All registered entries captured, including fake/disabled. Dynamic backend and machine-specific conditions remain native metadata");
        }
        coverage("gregtech.map_catalog", "complete", maps.size(), "Enumerated RecipeMap.ALL_RECIPE_MAPS");
    }

    private void assemblyLine() throws IOException {
        long count = 0;
        for (GTRecipe.RecipeAssemblyLine recipe : new ArrayList<>(GTRecipe.RecipeAssemblyLine.sAssemblylineRecipes)) {
            JsonArray inputs = new JsonArray();
            for (int index = 0; index < recipe.mInputs.length; index++) {
                if (recipe.mInputs[index] == null) continue;
                ItemStack[] choices = recipe.mOreDictAlt != null && index < recipe.mOreDictAlt.length
                    && recipe.mOreDictAlt[index] != null ? recipe.mOreDictAlt[index] : new ItemStack[]{recipe.mInputs[index]};
                JsonObject slot = itemSlot(choices, -1, false, false);
                slot.addProperty("native_slot", index);
                inputs.add(slot);
            }
            for (FluidStack stack : recipe.mFluidInputs) if (stack != null) inputs.add(fluidSlot(new FluidStack[]{stack}));
            JsonArray outputs = new JsonArray();
            if (recipe.mOutput != null) outputs.add(object("resource_id", item(recipe.mOutput), "amount", recipe.mOutput.stackSize,
                "chance", object("numerator", 1, "denominator", 1)));
            JsonObject conditions = object("research", object("resource_id", item(recipe.mResearchItem),
                "time_ticks", recipe.mResearchTime, "voltage", recipe.mResearchVoltage),
                "native_persistent_hash", recipe.getPersistentHash());
            emitProcess("gregtech:assembly_line", "Assembly Line", inputs, outputs, recipe.mDuration,
                recipe.mEUt, 1, true, conditions, object("owner", "RecipeAssemblyLine.sAssemblylineRecipes", "index", count));
            count++;
        }
        coverage("gregtech.assembly_line", "partial", count,
            "Real production registry and research captured. Machine progression and data-stick interpretation remain native");
    }

    JsonObject itemSlot(ItemStack[] stacks, int oreId, boolean sensitive, boolean unify) throws IOException {
        JsonArray choices = new JsonArray();
        boolean presence = stacks.length > 0;
        for (ItemStack stack : stacks) if (stack != null && stack.stackSize != 0) presence = false;
        for (ItemStack stack : stacks) {
            if (stack == null) continue;
            if (Item.itemRegistry.getNameForObject(stack.getItem()) == null) {
                choices.add(object("resource_id", null, "amount", presence ? 1 : stack.stackSize,
                    "native_amount", stack.stackSize, "match", object("mode", "native_unknown"),
                    "native_item", nativeValue(stack)));
                continue;
            }
            String resource = item(stack);
            boolean needsNbt = sensitive;
            String group = null;
            String mode = stack.getItemDamage() == OreDictionary.WILDCARD_VALUE ? "wildcard" : "exact";
            if (oreId >= 0) { group = oreGroups.get(OreDictionary.getOreName(oreId)); mode = "ore_dict"; }
            else if (unify && !needsNbt) { group = unifiedGroup(stack); mode = "unified"; }
            JsonObject match = object("mode", mode, "nbt_sensitive", needsNbt);
            if (group != null) match.addProperty("group_id", group);
            choices.add(object("resource_id", resource, "amount", presence ? 1 : stack.stackSize,
                "native_amount", stack.stackSize,
                "match", match));
        }
        return object("role", presence ? "presence" : "consume", "choices", choices);
    }

    private String unifiedGroup(ItemStack original) throws IOException {
        ItemStack unified = GTOreDictUnificator.get(original.copy());
        String key = item(unified == null ? original : unified);
        String existing = unifiedGroups.get(key);
        if (existing != null) return existing;
        List<ItemStack> aliases = GTOreDictUnificator.getNonUnifiedStacks(unified == null ? original.copy() : unified);
        JsonArray members = new JsonArray();
        Set<String> seen = new HashSet<>();
        seen.add(item(original));
        for (ItemStack alias : aliases) if (alias != null) seen.add(item(alias));
        for (String id : seen) members.add(new com.google.gson.JsonPrimitive(id));
        String id = "unified:" + key;
        unifiedGroups.put(key, id);
        writer.append("groups", object("id", id, "kind", "unified", "name", key, "members", members,
            "provenance", object("owner", "GTOreDictUnificator.getNonUnifiedStacks")));
        return id;
    }

    private JsonObject fluidSlot(FluidStack[] stacks) throws IOException {
        JsonArray choices = new JsonArray();
        boolean presence = stacks.length > 0;
        for (FluidStack stack : stacks) if (stack != null && stack.amount != 0) presence = false;
        for (FluidStack stack : stacks) if (stack != null) choices.add(object("resource_id", fluid(stack),
            "amount", presence ? 1 : stack.amount, "native_amount", stack.amount,
            "match", object("mode", "exact", "nbt_sensitive", true)));
        return object("role", presence ? "presence" : "consume", "choices", choices);
    }

    private void smelting() throws IOException {
        @SuppressWarnings("unchecked") Map<ItemStack, ItemStack> recipes = FurnaceRecipes.smelting().getSmeltingList();
        long count = 0;
        for (Map.Entry<ItemStack, ItemStack> entry : recipes.entrySet()) {
            ItemStack input = entry.getKey().copy(); input.stackSize = 1;
            ItemStack output = entry.getValue();
            emitProcess("minecraft:smelting", "Furnace", Jsons.array(itemSlot(new ItemStack[]{input}, -1, false, false)),
                Jsons.array(object("resource_id", item(output), "amount", output.stackSize,
                    "chance", object("numerator", 1, "denominator", 1))),
                null, null, null, true, object("fuel_and_duration", "machine_owned_unknown"),
                object("owner", "FurnaceRecipes", "index", count++));
        }
        coverage("minecraft.smelting", "partial", count, "Live smelting registry. Fuel/time owned by furnace implementations");
    }

    private JsonElement nativeValue(Object value) throws IOException {
        if (value != null && value.getClass() == Sievert.class) {
            Sievert sievert = (Sievert) value;
            return object("type", value.getClass().getName(), "sievert", sievert.sievert, "isExact", sievert.isExact);
        }
        if (value != null && value.getClass() == Materials.class)
            return object("type", value.getClass().getName(), "material_name", ((Materials) value).getName());
        if (value instanceof ItemStack) {
            ItemStack stack = (ItemStack) value;
            if (Item.itemRegistry.getNameForObject(stack.getItem()) == null)
                return object("type", "item_stack", "resource_id", null, "amount", stack.stackSize,
                    "status", "unregistered", "item_class", stack.getItem().getClass().getName(),
                    "metadata", stack.getItemDamage(), "nbt", TypedNbt.encode(stack.getTagCompound()),
                    "display_name", displayName(stack, stack.getItem().getClass().getName()));
            return object("type", "item_stack", "resource_id", item(stack), "amount", stack.stackSize);
        }
        if (value instanceof FluidStack) return object("type", "fluid_stack", "resource_id", fluid((FluidStack) value), "amount", ((FluidStack) value).amount);
        if (value == null || value instanceof String || value instanceof Number || value instanceof Boolean)
            return SnapshotWriter.JSON.toJsonTree(value);
        if (value instanceof Enum) return object("type", value.getClass().getName(), "value", ((Enum<?>) value).name());
        JsonArray result = new JsonArray();
        if (value.getClass().isArray()) {
            for (int index = 0; index < Array.getLength(value); index++) result.add(nativeValue(Array.get(value, index)));
            return result;
        }
        if (value instanceof Iterable) { for (Object entry : (Iterable<?>) value) result.add(nativeValue(entry)); return result; }
        unknownMetadata++;
        return object("type", value.getClass().getName(), "status", "uninterpreted", "native_text", value.toString());
    }

    private JsonObject chance(int nativeChance) { return object("numerator", nativeChance, "denominator", 10000); }

    /** Counts accepted outcomes on the uniform 24-bit java.util.Random.nextFloat lattice. */
    static JsonObject floatRollChance(float threshold, boolean inclusive) {
        if (Float.isNaN(threshold) || Float.isInfinite(threshold)) return null;
        if (threshold < 0) return object("numerator", 0, "denominator", 1);
        if (threshold >= 1) return object("numerator", 1, "denominator", 1);
        int outcomes = 1 << 24;
        double scaled = (double) threshold * outcomes;
        long numerator = inclusive ? (long) Math.floor(scaled) + 1L : (long) Math.ceil(scaled);
        return object("numerator", numerator, "denominator", outcomes);
    }

    void emitProcess(String family, String label, JsonArray inputs, JsonArray outputs, Integer duration,
        Integer energy, Integer amperage, Boolean executable, JsonObject conditions, JsonObject provenance) throws IOException {
        writer.append("processes", object("id", "p" + processNumber++, "family", family, "display_name", label,
            "inputs", inputs, "outputs", outputs, "duration_ticks", duration, "eu_per_tick", energy,
            "amperage", amperage, "executable", executable, "conditions", conditions, "provenance", provenance));
    }

    void coverage(String domain, String status, long records, String reason) throws IOException {
        coverage(domain, status, records, reason, null);
    }

    void coverage(String domain, String status, long records, String reason, JsonObject details) throws IOException {
        JsonObject record = object("id", domain, "domain", domain, "status", status, "records", records,
            "reason", reason, "provenance", object("exporter", Tags.VERSION));
        if (details != null) record.add("details", details);
        writer.append("coverage", record);
    }
}
